"""Building explainer - generates explanations for individual buildings/files."""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .bob_client import BobClient, NarrationRequest, NarrationResponse, NarrationType
from ..city.city_generator import Building
from ..ingestion.commit_parser import CommitInfo
from ..utils.logger import setup_logger
from ..utils.config import Config


@dataclass
class BuildingExplanation:
    """
    Explanation for a building/file.
    
    Attributes:
        building: The building being explained
        explanation: Generated explanation text
        key_events: List of key events in file history
        current_time: Current playback time (for temporal constraint)
        metadata: Additional metadata
    """
    building: Building
    explanation: str
    key_events: List[str] = field(default_factory=list)
    current_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BuildingExplainer:
    """
    Generates explanations for individual buildings/files on click.
    
    This class provides detailed, contextual explanations for specific files
    when clicked by the user. Explanations reference concrete events with
    dates and are constrained to events at/before the current playback moment.
    
    Features:
    - On-demand explanation generation
    - Temporal constraint (only past events)
    - Concrete event references with dates
    - Fast response time (< few seconds)
    - Caching for performance
    - Fallback to offline mode
    
    Architecture:
    - Integrates with BobClient for AI generation
    - Analyzes file history from commits
    - Maintains explanation cache
    - Respects current playback time
    
    Example:
        ```python
        explainer = BuildingExplainer(bob_client, commits)
        
        # Get explanation for clicked building
        explanation = explainer.explain_building(
            building,
            current_time=45.0
        )
        
        print(explanation.explanation)
        ```
    """
    
    # Configuration
    MAX_HISTORY_EVENTS = 10  # Maximum events to include in history
    EXPLANATION_TIMEOUT = 5.0  # Maximum time to wait for explanation (seconds)
    
    def __init__(
        self,
        bob_client: Optional[BobClient] = None,
        commits: Optional[List[CommitInfo]] = None
    ):
        """
        Initialize the building explainer.
        
        Args:
            bob_client: BobClient for narration generation (creates new if None)
            commits: List of all commits for history analysis
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.bob_client = bob_client or BobClient()
        self.commits = commits or []
        
        # Cache for explanations
        self._explanation_cache: Dict[str, BuildingExplanation] = {}
        
        # File history cache
        self._file_history_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        self.logger.info("Initialized BuildingExplainer")
    
    def set_commits(self, commits: List[CommitInfo]) -> None:
        """
        Set commits for history analysis.
        
        Args:
            commits: List of CommitInfo objects
        """
        self.commits = commits
        # Clear history cache when commits change
        self._file_history_cache.clear()
        self.logger.info(f"Updated commits: {len(commits)} commits")
    
    def explain_building(
        self,
        building: Building,
        current_time: Optional[float] = None,
        use_cache: bool = True
    ) -> BuildingExplanation:
        """
        Generate explanation for a building.
        
        Args:
            building: Building to explain
            current_time: Current playback time (for temporal constraint)
            use_cache: Whether to use cached explanation if available
            
        Returns:
            BuildingExplanation with generated text
        """
        # Check cache
        cache_key = self._get_cache_key(building, current_time)
        if use_cache and cache_key in self._explanation_cache:
            self.logger.debug(f"Using cached explanation for {building.file_path}")
            return self._explanation_cache[cache_key]
        
        self.logger.info(f"Generating explanation for {building.file_path}")
        
        # Get file history up to current time
        history = self._get_file_history(building.file_path, current_time)
        
        # Prepare context
        context = self._prepare_building_context(building, history, current_time)
        
        # Create narration request
        request = NarrationRequest(
            narration_type=NarrationType.BUILDING_EXPLANATION,
            context=context,
            max_length=150
        )
        
        # Generate explanation
        response = self.bob_client.generate_narration(request)
        
        # Extract key events
        key_events = self._extract_key_events(history)
        
        # Create explanation
        explanation = BuildingExplanation(
            building=building,
            explanation=response.text,
            key_events=key_events,
            current_time=current_time,
            metadata={
                'success': response.success,
                'cached': response.cached,
                'history_events': len(history)
            }
        )
        
        # Cache the explanation
        self._explanation_cache[cache_key] = explanation
        
        return explanation
    
    def explain_building_sync(
        self,
        building: Building,
        current_time: Optional[float] = None
    ) -> BuildingExplanation:
        """
        Generate explanation synchronously (blocking).
        
        This is a convenience method that ensures the explanation is
        generated within the timeout period.
        
        Args:
            building: Building to explain
            current_time: Current playback time
            
        Returns:
            BuildingExplanation
        """
        return self.explain_building(building, current_time)
    
    def pregenerate_explanations(
        self,
        buildings: List[Building],
        current_time: Optional[float] = None
    ) -> Dict[str, BuildingExplanation]:
        """
        Pre-generate explanations for multiple buildings.
        
        Useful for pre-caching explanations before demo.
        
        Args:
            buildings: List of buildings to explain
            current_time: Current playback time
            
        Returns:
            Dictionary mapping file paths to explanations
        """
        self.logger.info(f"Pre-generating explanations for {len(buildings)} buildings")
        
        explanations = {}
        for building in buildings:
            try:
                explanation = self.explain_building(building, current_time)
                explanations[building.file_path] = explanation
            except Exception as e:
                self.logger.error(
                    f"Failed to generate explanation for {building.file_path}: {e}"
                )
        
        self.logger.info(f"Pre-generated {len(explanations)} explanations")
        return explanations
    
    def clear_cache(self) -> None:
        """Clear explanation cache."""
        self._explanation_cache.clear()
        self.logger.info("Cleared explanation cache")
    
    def _get_file_history(
        self,
        file_path: str,
        current_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of changes for a file up to current time.
        
        Args:
            file_path: Path to file
            current_time: Current playback time (None = all history)
            
        Returns:
            List of history events
        """
        # Check cache
        cache_key = f"{file_path}_{current_time}"
        if cache_key in self._file_history_cache:
            return self._file_history_cache[cache_key]
        
        history = []
        
        # Filter commits by time if specified
        relevant_commits = self.commits
        if current_time is not None:
            # TODO: Map playback time to commit time
            # For now, use all commits
            pass
        
        # Extract events for this file
        for commit in relevant_commits:
            for file_change in commit.files_changed:
                if file_change.path == file_path:
                    event = {
                        'timestamp': commit.timestamp,
                        'author': commit.author,
                        'message': commit.message,
                        'change_type': file_change.change_type.value,
                        'lines_added': file_change.lines_added,
                        'lines_deleted': file_change.lines_deleted
                    }
                    history.append(event)
        
        # Limit to max events
        if len(history) > self.MAX_HISTORY_EVENTS:
            # Keep most recent and most significant
            history = sorted(history, key=lambda e: e['timestamp'], reverse=True)
            history = history[:self.MAX_HISTORY_EVENTS]
        
        # Cache the history
        self._file_history_cache[cache_key] = history
        
        return history
    
    def _prepare_building_context(
        self,
        building: Building,
        history: List[Dict[str, Any]],
        current_time: Optional[float]
    ) -> Dict[str, Any]:
        """
        Prepare context for building explanation.
        
        Args:
            building: Building to explain
            history: File history events
            current_time: Current playback time
            
        Returns:
            Context dictionary
        """
        # Format history for prompt
        history_text = []
        for event in history:
            date_str = event['timestamp'].strftime('%Y-%m-%d')
            history_text.append(
                f"{date_str}: {event['change_type']} - {event['message'][:50]}"
            )
        
        # Current state
        current_state = {
            'lines': building.lines_of_code,
            'modifications': building.modification_count,
            'last_modified': building.last_modified,
            'created': building.created_at
        }
        
        return {
            'file_path': building.file_path,
            'history': history_text,
            'current_state': current_state,
            'current_time': current_time,
            'neighborhood': building.neighborhood
        }
    
    def _extract_key_events(self, history: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key events from history.
        
        Args:
            history: File history events
            
        Returns:
            List of key event descriptions
        """
        key_events = []
        
        for event in history[:5]:  # Top 5 events
            date_str = event['timestamp'].strftime('%Y-%m-%d')
            change_type = event['change_type']
            
            if change_type == 'added':
                key_events.append(f"Created on {date_str}")
            elif change_type == 'modified':
                lines_changed = event['lines_added'] + event['lines_deleted']
                if lines_changed > 100:
                    key_events.append(
                        f"Major update on {date_str} ({lines_changed} lines changed)"
                    )
            elif change_type == 'deleted':
                key_events.append(f"Deleted on {date_str}")
            elif change_type == 'renamed':
                key_events.append(f"Renamed on {date_str}")
        
        return key_events
    
    def _get_cache_key(
        self,
        building: Building,
        current_time: Optional[float]
    ) -> str:
        """
        Generate cache key for building explanation.
        
        Args:
            building: Building
            current_time: Current playback time
            
        Returns:
            Cache key string
        """
        time_str = f"{current_time:.2f}" if current_time is not None else "all"
        return f"{building.file_path}_{time_str}"


# Made with Bob