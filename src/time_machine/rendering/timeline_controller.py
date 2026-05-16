"""Timeline controller - manages time progression through repository history."""

import time
from typing import List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..city.city_generator import CityState, CityGenerator
from ..ingestion.commit_parser import CommitInfo
from ..ingestion.file_grouper import Neighborhood
from ..utils.logger import setup_logger
from ..utils.config import Config


@dataclass
class TimelineState:
    """
    Represents the current state of the timeline.
    
    Attributes:
        current_commit_index: Index of current commit in history
        current_time: Current playback time in seconds
        total_duration: Total playback duration in seconds
        is_playing: Whether timeline is currently playing
        playback_speed: Current playback speed multiplier
        progress: Progress through timeline (0.0 to 1.0)
    """
    current_commit_index: int = 0
    current_time: float = 0.0
    total_duration: float = 90.0
    is_playing: bool = False
    playback_speed: float = 1.0
    
    @property
    def progress(self) -> float:
        """Get progress through timeline (0.0 to 1.0)."""
        if self.total_duration <= 0:
            return 0.0
        return min(1.0, self.current_time / self.total_duration)


class TimelineController:
    """
    Controls time progression through repository history.
    
    This class manages the playback of repository history, animating the city
    through time from earliest to latest commit. It provides smooth time
    progression with configurable duration and supports callbacks for state
    updates.
    
    Features:
    - Smooth time progression through commit history
    - Configurable playback duration (default 90 seconds)
    - Real-time interpolation between commits
    - State change callbacks for UI updates
    - Timeline scrubbing support
    
    Architecture:
    - Uses delta time for frame-independent animation
    - Interpolates between discrete commit states
    - Maintains timeline state for external queries
    - Generates city states on-demand for current time
    
    Example:
        ```python
        controller = TimelineController(commits, neighborhoods, generator)
        controller.set_duration(90.0)
        controller.play()
        
        while controller.is_playing():
            city_state = controller.update(delta_time)
            renderer.render(city_state)
        ```
    """
    
    def __init__(
        self,
        commits: List[CommitInfo],
        neighborhoods: dict[str, Neighborhood],
        city_generator: CityGenerator,
        duration: Optional[float] = None
    ):
        """
        Initialize the timeline controller.
        
        Args:
            commits: List of CommitInfo objects (chronological order)
            neighborhoods: Dictionary of Neighborhood objects
            city_generator: CityGenerator instance for generating states
            duration: Total playback duration in seconds (uses config default if None)
            
        Raises:
            ValueError: If commits list is empty
        """
        if not commits:
            raise ValueError("Cannot create timeline from empty commit history")
        
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.commits = commits
        self.neighborhoods = neighborhoods
        self.city_generator = city_generator
        
        # Timeline state
        self.state = TimelineState(
            total_duration=duration or Config.DEFAULT_PLAYBACK_DURATION
        )
        
        # Cached city states for performance
        self._city_state_cache: dict[int, CityState] = {}
        
        # Callbacks for state changes
        self._on_commit_change_callbacks: List[Callable[[int, CityState], None]] = []
        self._on_time_update_callbacks: List[Callable[[float], None]] = []
        
        # Timing
        self._last_update_time: Optional[float] = None
        
        self.logger.info(
            f"Initialized TimelineController: {len(commits)} commits, "
            f"{duration or Config.DEFAULT_PLAYBACK_DURATION}s duration"
        )
    
    def play(self) -> None:
        """Start timeline playback."""
        if not self.state.is_playing:
            self.state.is_playing = True
            self._last_update_time = time.time()
            self.logger.info("Timeline playback started")
    
    def pause(self) -> None:
        """Pause timeline playback."""
        if self.state.is_playing:
            self.state.is_playing = False
            self._last_update_time = None
            self.logger.info("Timeline playback paused")
    
    def stop(self) -> None:
        """Stop timeline playback and reset to beginning."""
        self.state.is_playing = False
        self.state.current_time = 0.0
        self.state.current_commit_index = 0
        self._last_update_time = None
        self.logger.info("Timeline playback stopped")
    
    def is_playing(self) -> bool:
        """Check if timeline is currently playing."""
        return self.state.is_playing
    
    def set_duration(self, duration: float) -> None:
        """
        Set total playback duration.
        
        Args:
            duration: Duration in seconds (must be positive)
            
        Raises:
            ValueError: If duration is not positive
        """
        if duration <= 0:
            raise ValueError("Duration must be positive")
        
        self.state.total_duration = duration
        self.logger.info(f"Timeline duration set to {duration}s")
    
    def set_speed(self, speed: float) -> None:
        """
        Set playback speed multiplier.
        
        Args:
            speed: Speed multiplier (0.5 = half speed, 2.0 = double speed)
            
        Raises:
            ValueError: If speed is not positive
        """
        if speed <= 0:
            raise ValueError("Speed must be positive")
        
        self.state.playback_speed = speed
        self.logger.info(f"Playback speed set to {speed}x")
    
    def scrub_to_time(self, time_seconds: float) -> CityState:
        """
        Scrub timeline to specific time.
        
        Args:
            time_seconds: Target time in seconds
            
        Returns:
            CityState at the target time
        """
        # Clamp time to valid range
        time_seconds = max(0.0, min(self.state.total_duration, time_seconds))
        
        self.state.current_time = time_seconds
        
        # Calculate corresponding commit index
        progress = time_seconds / self.state.total_duration
        commit_index = int(progress * (len(self.commits) - 1))
        commit_index = max(0, min(len(self.commits) - 1, commit_index))
        
        # Update commit index if changed
        if commit_index != self.state.current_commit_index:
            self.state.current_commit_index = commit_index
            self._notify_commit_change()
        
        self.logger.debug(f"Scrubbed to time {time_seconds:.2f}s (commit {commit_index})")
        
        return self.get_current_city_state()
    
    def scrub_to_commit(self, commit_index: int) -> CityState:
        """
        Scrub timeline to specific commit.
        
        Args:
            commit_index: Index of target commit
            
        Returns:
            CityState at the target commit
            
        Raises:
            ValueError: If commit_index is out of range
        """
        if commit_index < 0 or commit_index >= len(self.commits):
            raise ValueError(f"Commit index {commit_index} out of range")
        
        self.state.current_commit_index = commit_index
        
        # Calculate corresponding time
        progress = commit_index / (len(self.commits) - 1)
        self.state.current_time = progress * self.state.total_duration
        
        self._notify_commit_change()
        
        self.logger.debug(f"Scrubbed to commit {commit_index}")
        
        return self.get_current_city_state()
    
    def update(self, delta_time: Optional[float] = None) -> CityState:
        """
        Update timeline state.
        
        This method should be called every frame to advance the timeline.
        It handles time progression, commit transitions, and state updates.
        
        Args:
            delta_time: Time elapsed since last update in seconds
                       (auto-calculated if None)
            
        Returns:
            Current CityState for rendering
        """
        if not self.state.is_playing:
            return self.get_current_city_state()
        
        # Calculate delta time if not provided
        if delta_time is None:
            current_time = time.time()
            if self._last_update_time is not None:
                delta_time = current_time - self._last_update_time
            else:
                delta_time = 0.0
            self._last_update_time = current_time
        
        # Apply playback speed
        delta_time *= self.state.playback_speed
        
        # Update current time
        self.state.current_time += delta_time
        
        # Check if we've reached the end
        if self.state.current_time >= self.state.total_duration:
            self.state.current_time = self.state.total_duration
            self.state.is_playing = False
            self.logger.info("Timeline playback completed")
        
        # Calculate current commit index based on time
        progress = self.state.current_time / self.state.total_duration
        new_commit_index = int(progress * (len(self.commits) - 1))
        new_commit_index = max(0, min(len(self.commits) - 1, new_commit_index))
        
        # Check if we've transitioned to a new commit
        if new_commit_index != self.state.current_commit_index:
            self.state.current_commit_index = new_commit_index
            self._notify_commit_change()
        
        # Notify time update
        self._notify_time_update()
        
        return self.get_current_city_state()
    
    def get_current_city_state(self) -> CityState:
        """
        Get city state for current timeline position.
        
        Returns:
            CityState at current commit
        """
        commit_index = self.state.current_commit_index
        
        # Check cache first
        if commit_index in self._city_state_cache:
            return self._city_state_cache[commit_index]
        
        # Generate city state for current commit
        commit = self.commits[commit_index]
        city_state = self.city_generator.generate_city_at_commit(
            self.commits,
            self.neighborhoods,
            commit.sha
        )
        
        # Cache the state
        self._city_state_cache[commit_index] = city_state
        
        return city_state
    
    def get_current_commit(self) -> CommitInfo:
        """Get current commit info."""
        return self.commits[self.state.current_commit_index]
    
    def get_timeline_info(self) -> dict:
        """
        Get information about the timeline.
        
        Returns:
            Dictionary with timeline information
        """
        current_commit = self.get_current_commit()
        
        return {
            'total_commits': len(self.commits),
            'current_commit_index': self.state.current_commit_index,
            'current_commit_sha': current_commit.sha[:8],
            'current_commit_message': current_commit.message,
            'current_commit_timestamp': current_commit.timestamp.isoformat(),
            'current_time': self.state.current_time,
            'total_duration': self.state.total_duration,
            'progress': self.state.progress,
            'is_playing': self.state.is_playing,
            'playback_speed': self.state.playback_speed,
            'first_commit_date': self.commits[0].timestamp.isoformat(),
            'last_commit_date': self.commits[-1].timestamp.isoformat()
        }
    
    def on_commit_change(self, callback: Callable[[int, CityState], None]) -> None:
        """
        Register callback for commit changes.
        
        Args:
            callback: Function to call when commit changes (commit_index, city_state)
        """
        self._on_commit_change_callbacks.append(callback)
    
    def on_time_update(self, callback: Callable[[float], None]) -> None:
        """
        Register callback for time updates.
        
        Args:
            callback: Function to call on time update (current_time)
        """
        self._on_time_update_callbacks.append(callback)
    
    def _notify_commit_change(self) -> None:
        """Notify all commit change callbacks."""
        city_state = self.get_current_city_state()
        for callback in self._on_commit_change_callbacks:
            try:
                callback(self.state.current_commit_index, city_state)
            except Exception as e:
                self.logger.error(f"Error in commit change callback: {e}")
    
    def _notify_time_update(self) -> None:
        """Notify all time update callbacks."""
        for callback in self._on_time_update_callbacks:
            try:
                callback(self.state.current_time)
            except Exception as e:
                self.logger.error(f"Error in time update callback: {e}")
    
    def clear_cache(self) -> None:
        """Clear cached city states to free memory."""
        self._city_state_cache.clear()
        self.logger.info("City state cache cleared")


# Made with Bob