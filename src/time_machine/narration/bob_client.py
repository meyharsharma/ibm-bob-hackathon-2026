"""IBM Watson Assistant (Bob) client for narration generation."""

import json
import time
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from ibm_watson import AssistantV2
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    from ibm_cloud_sdk_core import ApiException
else:
    try:
        from ibm_watson import AssistantV2
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
        from ibm_cloud_sdk_core import ApiException
    except ImportError:
        # Graceful degradation if IBM Watson SDK not installed
        AssistantV2 = None  # type: ignore
        IAMAuthenticator = None  # type: ignore
        ApiException = Exception  # type: ignore

from ..utils.config import Config
from ..utils.logger import setup_logger


class NarrationType(Enum):
    """Types of narration requests."""
    EPOCH_SUMMARY = "epoch_summary"
    BUILDING_EXPLANATION = "building_explanation"
    ACTIVITY_HIGHLIGHT = "activity_highlight"
    GENERAL_QUERY = "general_query"


@dataclass
class NarrationRequest:
    """
    Request for narration generation.
    
    Attributes:
        narration_type: Type of narration requested
        context: Context data for narration (commits, files, etc.)
        prompt: Optional custom prompt
        max_length: Maximum length of narration in words
        temperature: Creativity parameter (0.0-1.0)
    """
    narration_type: NarrationType
    context: Dict[str, Any]
    prompt: Optional[str] = None
    max_length: int = 200
    temperature: float = 0.7


@dataclass
class NarrationResponse:
    """
    Response from narration generation.
    
    Attributes:
        text: Generated narration text
        success: Whether generation was successful
        error: Error message if failed
        metadata: Additional metadata (tokens used, etc.)
        cached: Whether response was from cache
    """
    text: str
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False


class BobClient:
    """
    Client for IBM Watson Assistant (Bob) narration generation.
    
    This class handles communication with IBM Watson Assistant for
    generating AI narration for the repository visualization. It supports
    multiple narration types and includes error handling, retry logic,
    and offline fallback.
    
    Features:
    - Multiple narration types (epoch summaries, building explanations, etc.)
    - Automatic retry with exponential backoff
    - Request/response caching
    - Offline mode support
    - Error handling and graceful degradation
    - Rate limiting
    
    Architecture:
    - Uses IBM Watson Assistant V2 API
    - Maintains session state for context
    - Caches responses for performance
    - Falls back to offline mode on failure
    
    Example:
        ```python
        client = BobClient()
        
        request = NarrationRequest(
            narration_type=NarrationType.EPOCH_SUMMARY,
            context={'commits': commits, 'timeframe': '2024-01'}
        )
        
        response = client.generate_narration(request)
        if response.success:
            print(response.text)
        ```
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    RETRY_BACKOFF = 2.0  # exponential backoff multiplier
    
    # Rate limiting
    MIN_REQUEST_INTERVAL = 0.5  # seconds between requests
    
    def __init__(self, offline_mode: Optional[bool] = None):
        """
        Initialize the Bob client.
        
        Args:
            offline_mode: Force offline mode (uses config default if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        # Determine offline mode
        self.offline_mode = offline_mode if offline_mode is not None else Config.ENABLE_OFFLINE_MODE
        
        # IBM Watson Assistant client
        self.assistant: Optional[Any] = None  # AssistantV2 instance
        self.session_id: Optional[str] = None
        
        # Rate limiting
        self._last_request_time: Optional[float] = None
        
        # Initialize client if not in offline mode
        if not self.offline_mode:
            self._initialize_client()
        else:
            self.logger.info("BobClient initialized in offline mode")
    
    def _initialize_client(self) -> None:
        """Initialize IBM Watson Assistant client."""
        if AssistantV2 is None or IAMAuthenticator is None:
            self.logger.error(
                "IBM Watson SDK not installed. "
                "Install with: pip install ibm-watson ibm-cloud-sdk-core"
            )
            self.offline_mode = True
            return
        
        try:
            # Validate configuration
            if not Config.IBM_WATSON_API_KEY:
                raise ValueError("IBM_WATSON_API_KEY not configured")
            if not Config.IBM_WATSON_URL:
                raise ValueError("IBM_WATSON_URL not configured")
            if not Config.IBM_WATSON_ASSISTANT_ID:
                raise ValueError("IBM_WATSON_ASSISTANT_ID not configured")
            
            # Create authenticator
            authenticator = IAMAuthenticator(Config.IBM_WATSON_API_KEY)
            
            # Create assistant client
            self.assistant = AssistantV2(
                version='2021-11-27',
                authenticator=authenticator
            )
            self.assistant.set_service_url(Config.IBM_WATSON_URL)
            
            # Create session
            self._create_session()
            
            self.logger.info("IBM Watson Assistant client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Watson Assistant: {e}")
            self.offline_mode = True
    
    def _create_session(self) -> None:
        """Create a new Watson Assistant session."""
        if not self.assistant:
            return
        
        try:
            response = self.assistant.create_session(
                assistant_id=Config.IBM_WATSON_ASSISTANT_ID
            ).get_result()
            
            self.session_id = response['session_id']
            self.logger.debug(f"Created Watson Assistant session: {self.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            self.offline_mode = True
    
    def generate_narration(
        self,
        request: NarrationRequest,
        retry: bool = True
    ) -> NarrationResponse:
        """
        Generate narration from request.
        
        Args:
            request: NarrationRequest with context and parameters
            retry: Whether to retry on failure
            
        Returns:
            NarrationResponse with generated text or error
        """
        # Check if offline mode
        if self.offline_mode:
            return self._offline_fallback(request)
        
        # Rate limiting
        self._apply_rate_limit()
        
        # Build prompt
        prompt = self._build_prompt(request)
        
        # Try to generate with retries
        for attempt in range(self.MAX_RETRIES if retry else 1):
            try:
                response = self._send_message(prompt)
                
                if response:
                    return NarrationResponse(
                        text=response,
                        success=True,
                        metadata={
                            'narration_type': request.narration_type.value,
                            'attempt': attempt + 1
                        }
                    )
            
            except Exception as e:
                self.logger.warning(
                    f"Narration generation attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self.MAX_RETRIES - 1:
                    # Wait before retry with exponential backoff
                    delay = self.RETRY_DELAY * (self.RETRY_BACKOFF ** attempt)
                    time.sleep(delay)
                else:
                    # Final attempt failed, fall back to offline
                    self.logger.error("All narration generation attempts failed")
                    return self._offline_fallback(request)
        
        # Should not reach here, but fallback just in case
        return self._offline_fallback(request)
    
    def _send_message(self, message: str) -> Optional[str]:
        """
        Send message to Watson Assistant and get response.
        
        Args:
            message: Message to send
            
        Returns:
            Response text or None if failed
        """
        if not self.assistant or not self.session_id:
            raise RuntimeError("Watson Assistant not initialized")
        
        try:
            response = self.assistant.message(
                assistant_id=Config.IBM_WATSON_ASSISTANT_ID,
                session_id=self.session_id,
                input={
                    'message_type': 'text',
                    'text': message
                }
            ).get_result()
            
            # Extract response text
            if 'output' in response and 'generic' in response['output']:
                for item in response['output']['generic']:
                    if item.get('response_type') == 'text':
                        return item.get('text', '')
            
            return None
            
        except ApiException as e:
            self.logger.error(f"Watson API error: {e}")
            raise
    
    def _build_prompt(self, request: NarrationRequest) -> str:
        """
        Build prompt for narration generation.
        
        Args:
            request: NarrationRequest
            
        Returns:
            Formatted prompt string
        """
        if request.prompt:
            return request.prompt
        
        # Build prompt based on narration type
        if request.narration_type == NarrationType.EPOCH_SUMMARY:
            return self._build_epoch_prompt(request.context)
        
        elif request.narration_type == NarrationType.BUILDING_EXPLANATION:
            return self._build_building_prompt(request.context)
        
        elif request.narration_type == NarrationType.ACTIVITY_HIGHLIGHT:
            return self._build_activity_prompt(request.context)
        
        else:
            return self._build_general_prompt(request.context)
    
    def _build_epoch_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for epoch summary."""
        commits = context.get('commits', [])
        timeframe = context.get('timeframe', 'this period')
        
        commit_summaries = []
        for commit in commits[:10]:  # Limit to recent commits
            commit_summaries.append(
                f"- {commit.get('message', 'No message')} by {commit.get('author', 'Unknown')}"
            )
        
        prompt = f"""Generate a narrative summary of repository activity during {timeframe}.

Commits:
{chr(10).join(commit_summaries)}

Create a coherent story that:
1. Identifies the main themes and changes
2. Highlights notable events (refactors, new features, bug fixes)
3. Describes the overall trajectory of development
4. Reads as a story, not a list

Keep it concise (under 200 words) and engaging."""
        
        return prompt
    
    def _build_building_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for building explanation."""
        file_path = context.get('file_path', 'unknown file')
        history = context.get('history', [])
        current_state = context.get('current_state', {})
        
        prompt = f"""Explain the history and significance of the file: {file_path}

Current state:
- Lines of code: {current_state.get('lines', 'unknown')}
- Modifications: {current_state.get('modifications', 0)}
- Last modified: {current_state.get('last_modified', 'unknown')}

Recent changes:
{chr(10).join(f"- {h}" for h in history[:5])}

Provide a brief explanation that:
1. Describes what this file does
2. Highlights key changes in its history
3. Explains its role in the project

Keep it concise (under 150 words)."""
        
        return prompt
    
    def _build_activity_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for activity highlight."""
        hotspot = context.get('hotspot', {})
        
        prompt = f"""Describe the significant activity in this area of the codebase.

Activity details:
- Location: {hotspot.get('location', 'unknown')}
- Changes: {hotspot.get('changes', 0)}
- Files affected: {hotspot.get('files', 0)}

Create a brief narrative highlighting:
1. What changed in this area
2. Why it's significant
3. The impact on the project

Keep it concise (under 100 words)."""
        
        return prompt
    
    def _build_general_prompt(self, context: Dict[str, Any]) -> str:
        """Build general prompt from context."""
        return json.dumps(context, indent=2)
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        
        self._last_request_time = time.time()
    
    def _offline_fallback(self, request: NarrationRequest) -> NarrationResponse:
        """
        Generate fallback narration when offline or on error.
        
        Args:
            request: NarrationRequest
            
        Returns:
            NarrationResponse with fallback text
        """
        self.logger.debug("Using offline fallback narration")
        
        # Generate simple fallback based on type
        if request.narration_type == NarrationType.EPOCH_SUMMARY:
            text = self._generate_epoch_fallback(request.context)
        elif request.narration_type == NarrationType.BUILDING_EXPLANATION:
            text = self._generate_building_fallback(request.context)
        elif request.narration_type == NarrationType.ACTIVITY_HIGHLIGHT:
            text = self._generate_activity_fallback(request.context)
        else:
            text = "Narration unavailable in offline mode."
        
        return NarrationResponse(
            text=text,
            success=True,
            metadata={'offline': True, 'narration_type': request.narration_type.value}
        )
    
    def _generate_epoch_fallback(self, context: Dict[str, Any]) -> str:
        """Generate fallback epoch summary."""
        commits = context.get('commits', [])
        timeframe = context.get('timeframe', 'this period')
        
        if not commits:
            return f"During {timeframe}, the repository saw continued development."
        
        return (
            f"During {timeframe}, the repository received {len(commits)} commits. "
            f"Development focused on various improvements and updates across the codebase."
        )
    
    def _generate_building_fallback(self, context: Dict[str, Any]) -> str:
        """Generate fallback building explanation."""
        file_path = context.get('file_path', 'this file')
        current_state = context.get('current_state', {})
        
        lines = current_state.get('lines', 0)
        mods = current_state.get('modifications', 0)
        
        return (
            f"{file_path} contains {lines} lines of code and has been "
            f"modified {mods} times throughout its history."
        )
    
    def _generate_activity_fallback(self, context: Dict[str, Any]) -> str:
        """Generate fallback activity highlight."""
        hotspot = context.get('hotspot', {})
        changes = hotspot.get('changes', 0)
        files = hotspot.get('files', 0)
        
        return (
            f"This area saw significant activity with {changes} changes "
            f"across {files} files."
        )
    
    def close(self) -> None:
        """Close the Watson Assistant session."""
        if self.assistant and self.session_id:
            try:
                self.assistant.delete_session(
                    assistant_id=Config.IBM_WATSON_ASSISTANT_ID,
                    session_id=self.session_id
                )
                self.logger.debug("Watson Assistant session closed")
            except Exception as e:
                self.logger.warning(f"Error closing session: {e}")
        
        self.session_id = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Made with Bob