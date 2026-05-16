"""Demo orchestrator - coordinates all components for demo mode."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

from ..narration.narration_storage import NarrationStorage
from ..rendering.playback_controller import PlaybackController
from ..rendering.timeline_controller import TimelineController
from ..rendering.animation_system import AnimationSystem
from ..city.city_generator import CityGenerator, CityState
from ..ingestion.repository_ingester import RepositoryIngester
from ..ingestion.commit_parser import CommitParser
from ..ingestion.file_grouper import FileGrouper
from ..utils.config import Config
from ..utils.logger import setup_logger


class DemoMode(Enum):
    """Demo mode types."""
    OFFLINE = "offline"  # Use pre-rendered narrations only
    ONLINE = "online"    # Generate narrations on-the-fly
    HYBRID = "hybrid"    # Try online, fallback to offline


@dataclass
class DemoConfig:
    """
    Configuration for demo mode.
    
    Attributes:
        mode: Demo mode (offline, online, or hybrid)
        repository_path: Path to repository to demo
        repository_id: Unique repository identifier (auto-generated if None)
        playback_duration: Duration of demo in seconds
        auto_start: Whether to start playback automatically
        show_legend: Whether to show visual legend on start
        legend_duration: Duration to show legend in seconds
        enable_narration: Whether to enable narration
        enable_animations: Whether to enable animations
        graceful_degradation: Whether to continue on errors
    """
    mode: DemoMode = DemoMode.HYBRID
    repository_path: Optional[str] = None
    repository_id: Optional[str] = None
    playback_duration: int = 90
    auto_start: bool = True
    show_legend: bool = True
    legend_duration: float = 15.0
    enable_narration: bool = True
    enable_animations: bool = True
    graceful_degradation: bool = True


class DemoOrchestrator:
    """
    Orchestrates all components for demo mode.
    
    This class provides a high-level interface for running demos of
    repository evolution. It coordinates narration loading, playback
    control, animation, and graceful degradation.
    
    Features:
    - Offline demo mode with pre-rendered narrations
    - Online mode with live narration generation
    - Hybrid mode with automatic fallback
    - Visual legend/onboarding experience
    - Graceful degradation on errors
    - Simple API for running demos
    
    Architecture:
    - Coordinates NarrationStorage for loading narrations
    - Manages PlaybackController for timeline control
    - Integrates AnimationSystem for visual effects
    - Handles errors with graceful degradation
    - Provides callbacks for UI updates
    
    Example:
        ```python
        # Offline demo with pre-rendered narrations
        config = DemoConfig(
            mode=DemoMode.OFFLINE,
            repository_path="/path/to/repo"
        )
        orchestrator = DemoOrchestrator(config)
        
        # Initialize and start demo
        if orchestrator.initialize():
            orchestrator.start_demo()
            
            # Update loop
            while orchestrator.is_running():
                city_state = orchestrator.update()
                # Render city_state
        ```
    """
    
    def __init__(self, config: Optional[DemoConfig] = None):
        """
        Initialize the demo orchestrator.
        
        Args:
            config: DemoConfig (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.config = config or DemoConfig()
        
        # Components
        self.storage: Optional[NarrationStorage] = None
        self.ingester: Optional[RepositoryIngester] = None
        self.commit_parser: Optional[CommitParser] = None
        self.file_grouper: Optional[FileGrouper] = None
        self.city_generator: Optional[CityGenerator] = None
        self.timeline: Optional[TimelineController] = None
        self.animation_system: Optional[AnimationSystem] = None
        self.playback: Optional[PlaybackController] = None
        
        # Cached data
        self._commits: Optional[List] = None
        self._neighborhoods: Optional[Dict] = None
        
        # State
        self._initialized = False
        self._running = False
        self._error_count = 0
        self._max_errors = 5
        
        # Narration data
        self._epoch_narrations: Optional[List[Dict[str, Any]]] = None
        self._building_explanations: Optional[Dict[str, Dict[str, Any]]] = None
        
        self.logger.info(f"Initialized DemoOrchestrator in {self.config.mode.value} mode")
    
    def initialize(self) -> bool:
        """
        Initialize all components for demo.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing demo components...")
            
            # Validate configuration
            if not self._validate_config():
                return False
            
            # Initialize storage
            self.storage = NarrationStorage()
            
            # Generate repository ID if not provided
            if not self.config.repository_id and self.config.repository_path:
                self.config.repository_id = NarrationStorage.generate_repository_id(
                    self.config.repository_path
                )
            
            # Load or generate narrations based on mode
            if not self._load_narrations():
                if not self.config.graceful_degradation:
                    return False
                self.logger.warning("Continuing without narrations (graceful degradation)")
            
            # Initialize city generator
            if not self._initialize_city():
                if not self.config.graceful_degradation:
                    return False
                self.logger.warning("Continuing without city (graceful degradation)")
            
            # Initialize playback components
            if not self._initialize_playback():
                if not self.config.graceful_degradation:
                    return False
                self.logger.warning("Continuing without playback (graceful degradation)")
            
            self._initialized = True
            self.logger.info("Demo initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize demo: {e}")
            if self.config.graceful_degradation:
                self._initialized = True
                return True
            return False
    
    def start_demo(self) -> bool:
        """
        Start the demo playback.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self._initialized:
            self.logger.error("Cannot start demo: not initialized")
            return False
        
        try:
            self.logger.info("Starting demo...")
            
            # Start playback if auto-start enabled
            if self.config.auto_start and self.playback:
                self.playback.play()
            
            self._running = True
            self.logger.info("Demo started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start demo: {e}")
            return self._handle_error("start_demo")
    
    def stop_demo(self) -> None:
        """Stop the demo playback."""
        try:
            self.logger.info("Stopping demo...")
            
            if self.playback:
                self.playback.stop()
            
            self._running = False
            self.logger.info("Demo stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping demo: {e}")
    
    def pause_demo(self) -> None:
        """Pause the demo playback."""
        try:
            if self.playback:
                self.playback.pause()
            self.logger.info("Demo paused")
        except Exception as e:
            self.logger.error(f"Error pausing demo: {e}")
    
    def resume_demo(self) -> None:
        """Resume the demo playback."""
        try:
            if self.playback:
                self.playback.resume()
            self.logger.info("Demo resumed")
        except Exception as e:
            self.logger.error(f"Error resuming demo: {e}")
    
    def update(self, delta_time: Optional[float] = None) -> Optional[CityState]:
        """
        Update demo state.
        
        This should be called every frame.
        
        Args:
            delta_time: Time elapsed since last update in seconds
            
        Returns:
            Current CityState for rendering, or None on error
        """
        if not self._running:
            return None
        
        try:
            # Update playback
            if self.playback:
                return self.playback.update(delta_time)
            
            # Fallback: update timeline directly
            if self.timeline:
                return self.timeline.update(delta_time)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error updating demo: {e}")
            if self._handle_error("update"):
                return None
            self._running = False
            return None
    
    def is_running(self) -> bool:
        """Check if demo is currently running."""
        return self._running
    
    def is_initialized(self) -> bool:
        """Check if demo is initialized."""
        return self._initialized
    
    def get_narration_at_time(self, time_seconds: float) -> Optional[str]:
        """
        Get narration text for specific time.
        
        Args:
            time_seconds: Time in seconds
            
        Returns:
            Narration text or None
        """
        if not self._epoch_narrations:
            return None
        
        try:
            # Find epoch containing this time
            for narration in self._epoch_narrations:
                epoch = narration.get('epoch', {})
                # Simple time-based lookup (could be improved)
                if 'start_time' in epoch:
                    return narration.get('narration')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting narration: {e}")
            return None
    
    def get_building_explanation(self, file_path: str) -> Optional[str]:
        """
        Get explanation for specific building/file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Explanation text or None
        """
        if not self._building_explanations:
            return None
        
        try:
            explanation = self._building_explanations.get(file_path)
            if explanation:
                return explanation.get('explanation')
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting building explanation: {e}")
            return None
    
    def get_demo_info(self) -> Dict[str, Any]:
        """
        Get comprehensive demo information.
        
        Returns:
            Dictionary with demo state and configuration
        """
        info = {
            'initialized': self._initialized,
            'running': self._running,
            'mode': self.config.mode.value,
            'repository_id': self.config.repository_id,
            'has_narrations': self._epoch_narrations is not None,
            'has_explanations': self._building_explanations is not None,
            'error_count': self._error_count,
        }
        
        # Add playback info if available
        if self.playback:
            try:
                info['playback'] = self.playback.get_playback_info()
            except:
                pass
        
        return info
    
    def _validate_config(self) -> bool:
        """Validate configuration."""
        if self.config.mode == DemoMode.OFFLINE:
            if not self.config.repository_id and not self.config.repository_path:
                self.logger.error("Offline mode requires repository_id or repository_path")
                return False
        
        return True
    
    def _load_narrations(self) -> bool:
        """Load narrations based on mode."""
        try:
            if self.config.mode == DemoMode.OFFLINE:
                return self._load_offline_narrations()
            elif self.config.mode == DemoMode.ONLINE:
                return self._generate_online_narrations()
            else:  # HYBRID
                return self._load_hybrid_narrations()
                
        except Exception as e:
            self.logger.error(f"Failed to load narrations: {e}")
            return False
    
    def _load_offline_narrations(self) -> bool:
        """Load pre-rendered narrations from storage."""
        if not self.storage or not self.config.repository_id:
            return False
        
        self.logger.info(f"Loading offline narrations for {self.config.repository_id}")
        
        # Load epoch narrations
        self._epoch_narrations = self.storage.load_epoch_narrations(
            self.config.repository_id
        )
        
        # Load building explanations
        self._building_explanations = self.storage.load_building_explanations(
            self.config.repository_id
        )
        
        has_narrations = (
            self._epoch_narrations is not None or
            self._building_explanations is not None
        )
        
        if has_narrations:
            self.logger.info("Successfully loaded offline narrations")
        else:
            self.logger.warning("No offline narrations found")
        
        return has_narrations
    
    def _generate_online_narrations(self) -> bool:
        """Generate narrations on-the-fly."""
        self.logger.info("Online narration generation not yet implemented")
        # TODO: Implement online narration generation
        # This would involve calling the narration sync system
        return False
    
    def _load_hybrid_narrations(self) -> bool:
        """Try online, fallback to offline."""
        self.logger.info("Attempting hybrid narration loading...")
        
        # Try online first
        if self._generate_online_narrations():
            return True
        
        # Fallback to offline
        self.logger.info("Online generation failed, falling back to offline")
        return self._load_offline_narrations()
    
    def _initialize_city(self) -> bool:
        """Initialize city generator."""
        try:
            if not self.config.repository_path:
                self.logger.warning("No repository path provided, skipping city generation")
                return False
            
            # Initialize ingester and ingest repository
            self.ingester = RepositoryIngester()
            result = self.ingester.ingest(self.config.repository_path)
            
            if not result:
                self.logger.warning("Failed to ingest repository")
                return False
            
            # Parse commits
            self.commit_parser = CommitParser(result['path'])
            self._commits = self.commit_parser.parse_history()
            
            if not self._commits:
                self.logger.warning("No commits found in repository")
                return False
            
            # Group files into neighborhoods
            self.file_grouper = FileGrouper()
            self._neighborhoods = self.file_grouper.group_files(self._commits)
            
            # Initialize city generator
            self.city_generator = CityGenerator()
            
            self.logger.info(f"Initialized city with {len(self._commits)} commits")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize city: {e}")
            return False
    
    def _initialize_playback(self) -> bool:
        """Initialize playback components."""
        try:
            if not self._commits or not self._neighborhoods or not self.city_generator:
                self.logger.warning("No commits, neighborhoods, or city generator available")
                return False
            
            # Initialize timeline
            self.timeline = TimelineController(
                commits=self._commits,
                neighborhoods=self._neighborhoods,
                city_generator=self.city_generator,
                duration=self.config.playback_duration
            )
            
            # Initialize animation system if enabled
            if self.config.enable_animations:
                self.animation_system = AnimationSystem()
            
            # Initialize playback controller
            self.playback = PlaybackController(
                timeline_controller=self.timeline,
                animation_system=self.animation_system
            )
            
            self.logger.info("Initialized playback components")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize playback: {e}")
            return False
    
    def _handle_error(self, context: str) -> bool:
        """
        Handle error with graceful degradation.
        
        Args:
            context: Context where error occurred
            
        Returns:
            True if should continue, False if should stop
        """
        self._error_count += 1
        
        if not self.config.graceful_degradation:
            return False
        
        if self._error_count >= self._max_errors:
            self.logger.error(f"Too many errors ({self._error_count}), stopping demo")
            self._running = False
            return False
        
        self.logger.warning(
            f"Error in {context} (count: {self._error_count}), continuing with degradation"
        )
        return True


# Made with Bob