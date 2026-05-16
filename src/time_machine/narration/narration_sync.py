"""Narration synchronization - syncs narration with visual playback."""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .epoch_generator import EpochNarration, Epoch
from ..rendering.timeline_controller import TimelineController
from ..rendering.playback_controller import PlaybackController, PlaybackState
from ..utils.logger import setup_logger
from ..utils.config import Config


class NarrationState(Enum):
    """States of narration playback."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class NarrationSegment:
    """
    A segment of narration tied to a specific time range.
    
    Attributes:
        start_time: Start time in seconds
        end_time: End time in seconds
        text: Narration text
        epoch: Associated epoch (if any)
        metadata: Additional metadata
    """
    start_time: float
    end_time: float
    text: str
    epoch: Optional[Epoch] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get duration of segment in seconds."""
        return self.end_time - self.start_time
    
    def contains_time(self, time: float) -> bool:
        """Check if time falls within this segment."""
        return self.start_time <= time < self.end_time


class NarrationSync:
    """
    Synchronizes narration with visual playback.
    
    This class manages the timing and delivery of narration segments
    to match the visual timeline. It ensures narration describes events
    at/around the current moment and handles pause/resume correctly.
    
    Features:
    - Time-based narration segment management
    - Automatic segment switching based on playback time
    - Pause/resume synchronization
    - Callbacks for narration events
    - Smooth transitions between segments
    
    Architecture:
    - Integrates with TimelineController for time tracking
    - Integrates with PlaybackController for state management
    - Maintains narration timeline parallel to visual timeline
    - Triggers callbacks for UI updates
    
    Example:
        ```python
        sync = NarrationSync(timeline_controller, playback_controller)
        
        # Add narration segments
        sync.add_narrations(epoch_narrations)
        
        # Update each frame
        sync.update()
        
        # Listen for narration changes
        sync.on_narration_change(lambda segment: print(segment.text))
        ```
    """
    
    def __init__(
        self,
        timeline_controller: TimelineController,
        playback_controller: Optional[PlaybackController] = None
    ):
        """
        Initialize narration sync.
        
        Args:
            timeline_controller: TimelineController for time tracking
            playback_controller: PlaybackController for state management (optional)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.timeline = timeline_controller
        self.playback = playback_controller
        
        # Narration segments
        self._segments: List[NarrationSegment] = []
        self._current_segment: Optional[NarrationSegment] = None
        self._current_segment_index: int = -1
        
        # State
        self._state = NarrationState.IDLE
        self._last_update_time: Optional[float] = None
        
        # Callbacks
        self._on_narration_change_callbacks: List[Callable[[NarrationSegment], None]] = []
        self._on_narration_complete_callbacks: List[Callable[[NarrationSegment], None]] = []
        
        # Register with playback controller if provided
        if self.playback:
            self.playback.on_state_change(self._handle_playback_state_change)
        
        self.logger.info("Initialized NarrationSync")
    
    def add_narrations(self, narrations: List[EpochNarration]) -> None:
        """
        Add epoch narrations to the timeline.
        
        Automatically distributes narrations across the timeline based on
        epoch timing.
        
        Args:
            narrations: List of EpochNarration objects
        """
        self.logger.info(f"Adding {len(narrations)} narrations to timeline")
        
        # Clear existing segments
        self._segments.clear()
        
        # Get total duration
        total_duration = self.timeline.state.total_duration
        
        # Sort narrations by epoch start time
        sorted_narrations = sorted(narrations, key=lambda n: n.epoch.start_time)
        
        # Calculate time mapping
        if not sorted_narrations:
            return
        
        first_epoch = sorted_narrations[0].epoch
        last_epoch = sorted_narrations[-1].epoch
        
        # Map epoch times to playback times
        for narration in sorted_narrations:
            # Calculate start and end times in playback timeline
            start_time = self._map_epoch_to_playback_time(
                narration.epoch.start_time,
                first_epoch.start_time,
                last_epoch.end_time,
                total_duration
            )
            
            end_time = self._map_epoch_to_playback_time(
                narration.epoch.end_time,
                first_epoch.start_time,
                last_epoch.end_time,
                total_duration
            )
            
            # Create segment
            segment = NarrationSegment(
                start_time=start_time,
                end_time=end_time,
                text=narration.narration,
                epoch=narration.epoch,
                metadata={
                    'highlights': narration.highlights,
                    'significance': narration.epoch.significance_score
                }
            )
            
            self._segments.append(segment)
        
        self.logger.info(f"Created {len(self._segments)} narration segments")
    
    def add_segment(self, segment: NarrationSegment) -> None:
        """
        Add a single narration segment.
        
        Args:
            segment: NarrationSegment to add
        """
        self._segments.append(segment)
        # Re-sort segments by start time
        self._segments.sort(key=lambda s: s.start_time)
    
    def update(self) -> None:
        """
        Update narration sync.
        
        This method should be called every frame to check for narration
        segment transitions.
        """
        # Get current playback time
        current_time = self.timeline.state.current_time
        
        # Check if we need to switch segments
        if not self._current_segment or not self._current_segment.contains_time(current_time):
            self._update_current_segment(current_time)
        
        # Update state based on playback
        if self.playback:
            if self.playback.is_playing():
                self._state = NarrationState.PLAYING
            elif self.playback.is_paused():
                self._state = NarrationState.PAUSED
            elif self.playback.is_stopped():
                self._state = NarrationState.IDLE
        
        self._last_update_time = current_time
    
    def get_current_narration(self) -> Optional[str]:
        """
        Get current narration text.
        
        Returns:
            Current narration text or None if no narration active
        """
        if self._current_segment:
            return self._current_segment.text
        return None
    
    def get_current_segment(self) -> Optional[NarrationSegment]:
        """
        Get current narration segment.
        
        Returns:
            Current NarrationSegment or None
        """
        return self._current_segment
    
    def get_segment_at_time(self, time: float) -> Optional[NarrationSegment]:
        """
        Get narration segment at specific time.
        
        Args:
            time: Time in seconds
            
        Returns:
            NarrationSegment at that time or None
        """
        for segment in self._segments:
            if segment.contains_time(time):
                return segment
        return None
    
    def get_all_segments(self) -> List[NarrationSegment]:
        """Get all narration segments."""
        return self._segments.copy()
    
    def get_state(self) -> NarrationState:
        """Get current narration state."""
        return self._state
    
    def is_playing(self) -> bool:
        """Check if narration is playing."""
        return self._state == NarrationState.PLAYING
    
    def is_paused(self) -> bool:
        """Check if narration is paused."""
        return self._state == NarrationState.PAUSED
    
    def clear(self) -> None:
        """Clear all narration segments."""
        self._segments.clear()
        self._current_segment = None
        self._current_segment_index = -1
        self._state = NarrationState.IDLE
        self.logger.info("Cleared all narration segments")
    
    def on_narration_change(self, callback: Callable[[NarrationSegment], None]) -> None:
        """
        Register callback for narration changes.
        
        Args:
            callback: Function to call when narration segment changes
        """
        self._on_narration_change_callbacks.append(callback)
    
    def on_narration_complete(self, callback: Callable[[NarrationSegment], None]) -> None:
        """
        Register callback for narration completion.
        
        Args:
            callback: Function to call when narration segment completes
        """
        self._on_narration_complete_callbacks.append(callback)
    
    def get_sync_info(self) -> Dict[str, Any]:
        """
        Get information about narration sync state.
        
        Returns:
            Dictionary with sync information
        """
        return {
            'state': self._state.value,
            'total_segments': len(self._segments),
            'current_segment_index': self._current_segment_index,
            'current_narration': self.get_current_narration(),
            'current_time': self.timeline.state.current_time,
            'has_current_segment': self._current_segment is not None
        }
    
    def _update_current_segment(self, current_time: float) -> None:
        """
        Update current segment based on time.
        
        Args:
            current_time: Current playback time
        """
        # Find segment for current time
        new_segment = None
        new_index = -1
        
        for i, segment in enumerate(self._segments):
            if segment.contains_time(current_time):
                new_segment = segment
                new_index = i
                break
        
        # Check if segment changed
        if new_segment != self._current_segment:
            # Complete previous segment
            if self._current_segment:
                self._notify_narration_complete(self._current_segment)
            
            # Update current segment
            self._current_segment = new_segment
            self._current_segment_index = new_index
            
            # Notify change
            if new_segment:
                self._notify_narration_change(new_segment)
                self.logger.debug(
                    f"Switched to narration segment {new_index}: "
                    f"{new_segment.text[:50]}..."
                )
    
    def _map_epoch_to_playback_time(
        self,
        epoch_time: Any,  # datetime
        first_epoch_time: Any,  # datetime
        last_epoch_time: Any,  # datetime
        total_duration: float
    ) -> float:
        """
        Map epoch timestamp to playback time.
        
        Args:
            epoch_time: Epoch timestamp
            first_epoch_time: First epoch timestamp
            last_epoch_time: Last epoch timestamp
            total_duration: Total playback duration
            
        Returns:
            Playback time in seconds
        """
        # Calculate progress through epoch timeline
        total_epoch_duration = (last_epoch_time - first_epoch_time).total_seconds()
        
        if total_epoch_duration <= 0:
            return 0.0
        
        elapsed = (epoch_time - first_epoch_time).total_seconds()
        progress = elapsed / total_epoch_duration
        
        # Map to playback time
        return progress * total_duration
    
    def _handle_playback_state_change(self, state: PlaybackState) -> None:
        """
        Handle playback state changes.
        
        Args:
            state: New playback state
        """
        if state == PlaybackState.PLAYING:
            self._state = NarrationState.PLAYING
        elif state == PlaybackState.PAUSED:
            self._state = NarrationState.PAUSED
        elif state == PlaybackState.STOPPED:
            self._state = NarrationState.IDLE
            self._current_segment = None
            self._current_segment_index = -1
    
    def _notify_narration_change(self, segment: NarrationSegment) -> None:
        """Notify all narration change callbacks."""
        for callback in self._on_narration_change_callbacks:
            try:
                callback(segment)
            except Exception as e:
                self.logger.error(f"Error in narration change callback: {e}")
    
    def _notify_narration_complete(self, segment: NarrationSegment) -> None:
        """Notify all narration complete callbacks."""
        for callback in self._on_narration_complete_callbacks:
            try:
                callback(segment)
            except Exception as e:
                self.logger.error(f"Error in narration complete callback: {e}")


# Made with Bob