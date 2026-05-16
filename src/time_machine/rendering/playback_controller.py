"""Playback controller - user controls for timeline playback."""

from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .timeline_controller import TimelineController, TimelineState
from .animation_system import AnimationSystem
from ..city.city_generator import CityState
from ..utils.logger import setup_logger
from ..utils.config import Config


class PlaybackState(Enum):
    """Playback states."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class PlaybackConfig:
    """
    Configuration for playback controls.
    
    Attributes:
        min_speed: Minimum playback speed multiplier
        max_speed: Maximum playback speed multiplier
        default_speed: Default playback speed
        speed_step: Speed adjustment step size
        scrub_sensitivity: Sensitivity for scrubbing (seconds per unit)
    """
    min_speed: float = 0.5
    max_speed: float = 4.0
    default_speed: float = 1.0
    speed_step: float = 0.25
    scrub_sensitivity: float = 1.0


class PlaybackController:
    """
    Controls playback of timeline with user interaction.
    
    This class provides a high-level interface for controlling timeline
    playback with user-friendly controls including play, pause, scrub,
    and speed adjustment. It integrates TimelineController and
    AnimationSystem to provide a complete playback experience.
    
    Features:
    - Play/pause/stop controls
    - Timeline scrubbing to arbitrary moments
    - Playback speed adjustment (0.5x - 4x)
    - Speed presets (slow, normal, fast)
    - State management and callbacks
    - Integration with animation system
    
    Architecture:
    - Wraps TimelineController for timeline management
    - Coordinates with AnimationSystem for visual effects
    - Maintains playback state and configuration
    - Provides callbacks for UI updates
    - Validates user input and enforces constraints
    
    Example:
        ```python
        controller = PlaybackController(timeline, animation_system)
        
        # Start playback
        controller.play()
        
        # Adjust speed
        controller.set_speed(2.0)  # 2x speed
        
        # Pause
        controller.pause()
        
        # Scrub to 50% through timeline
        controller.scrub_to_progress(0.5)
        
        # Resume
        controller.resume()
        ```
    """
    
    def __init__(
        self,
        timeline_controller: TimelineController,
        animation_system: Optional[AnimationSystem] = None,
        config: Optional[PlaybackConfig] = None
    ):
        """
        Initialize the playback controller.
        
        Args:
            timeline_controller: TimelineController instance
            animation_system: AnimationSystem instance (optional)
            config: PlaybackConfig (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.timeline = timeline_controller
        self.animation_system = animation_system
        self.config = config or PlaybackConfig()
        
        # Playback state
        self._state = PlaybackState.STOPPED
        self._previous_speed: Optional[float] = None
        
        # Callbacks
        self._on_state_change_callbacks: list[Callable[[PlaybackState], None]] = []
        self._on_speed_change_callbacks: list[Callable[[float], None]] = []
        
        self.logger.info("Initialized PlaybackController")
    
    def play(self) -> None:
        """
        Start playback from current position.
        
        If already playing, this has no effect.
        """
        if self._state == PlaybackState.PLAYING:
            self.logger.debug("Already playing")
            return
        
        # If at end, restart from beginning
        if self.timeline.state.progress >= 1.0:
            self.timeline.stop()
        
        self.timeline.play()
        self._state = PlaybackState.PLAYING
        self._notify_state_change()
        
        self.logger.info("Playback started")
    
    def pause(self) -> None:
        """
        Pause playback at current position.
        
        Playback can be resumed from this position.
        """
        if self._state != PlaybackState.PLAYING:
            self.logger.debug("Not playing, cannot pause")
            return
        
        self.timeline.pause()
        self._state = PlaybackState.PAUSED
        self._notify_state_change()
        
        self.logger.info("Playback paused")
    
    def resume(self) -> None:
        """
        Resume playback from paused state.
        
        If not paused, this is equivalent to play().
        """
        if self._state == PlaybackState.PAUSED:
            self.timeline.play()
            self._state = PlaybackState.PLAYING
            self._notify_state_change()
            self.logger.info("Playback resumed")
        else:
            self.play()
    
    def stop(self) -> None:
        """
        Stop playback and reset to beginning.
        """
        self.timeline.stop()
        self._state = PlaybackState.STOPPED
        self._notify_state_change()
        
        # Clear animations
        if self.animation_system:
            self.animation_system.clear_all_animations()
        
        self.logger.info("Playback stopped")
    
    def toggle_play_pause(self) -> None:
        """
        Toggle between play and pause states.
        
        Convenient for single-button play/pause control.
        """
        if self._state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.resume()
    
    def scrub_to_time(self, time_seconds: float) -> CityState:
        """
        Scrub timeline to specific time.
        
        Args:
            time_seconds: Target time in seconds
            
        Returns:
            CityState at the target time
        """
        was_playing = self._state == PlaybackState.PLAYING
        
        # Pause if playing
        if was_playing:
            self.timeline.pause()
        
        # Scrub to time
        city_state = self.timeline.scrub_to_time(time_seconds)
        
        # Update state
        if self.timeline.state.current_time > 0:
            self._state = PlaybackState.PAUSED
        else:
            self._state = PlaybackState.STOPPED
        
        self._notify_state_change()
        
        self.logger.debug(f"Scrubbed to time {time_seconds:.2f}s")
        
        return city_state
    
    def scrub_to_progress(self, progress: float) -> CityState:
        """
        Scrub timeline to specific progress (0.0 to 1.0).
        
        Args:
            progress: Target progress (0.0 = start, 1.0 = end)
            
        Returns:
            CityState at the target progress
            
        Raises:
            ValueError: If progress is out of range
        """
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")
        
        time_seconds = progress * self.timeline.state.total_duration
        return self.scrub_to_time(time_seconds)
    
    def scrub_to_commit(self, commit_index: int) -> CityState:
        """
        Scrub timeline to specific commit.
        
        Args:
            commit_index: Index of target commit
            
        Returns:
            CityState at the target commit
        """
        was_playing = self._state == PlaybackState.PLAYING
        
        # Pause if playing
        if was_playing:
            self.timeline.pause()
        
        # Scrub to commit
        city_state = self.timeline.scrub_to_commit(commit_index)
        
        # Update state
        self._state = PlaybackState.PAUSED if commit_index > 0 else PlaybackState.STOPPED
        self._notify_state_change()
        
        self.logger.debug(f"Scrubbed to commit {commit_index}")
        
        return city_state
    
    def step_forward(self) -> CityState:
        """
        Step forward one commit.
        
        Returns:
            CityState at next commit
        """
        current_index = self.timeline.state.current_commit_index
        next_index = min(current_index + 1, len(self.timeline.commits) - 1)
        return self.scrub_to_commit(next_index)
    
    def step_backward(self) -> CityState:
        """
        Step backward one commit.
        
        Returns:
            CityState at previous commit
        """
        current_index = self.timeline.state.current_commit_index
        prev_index = max(current_index - 1, 0)
        return self.scrub_to_commit(prev_index)
    
    def set_speed(self, speed: float) -> None:
        """
        Set playback speed.
        
        Args:
            speed: Speed multiplier (0.5 = half speed, 2.0 = double speed)
            
        Raises:
            ValueError: If speed is outside allowed range
        """
        if not self.config.min_speed <= speed <= self.config.max_speed:
            raise ValueError(
                f"Speed must be between {self.config.min_speed} and "
                f"{self.config.max_speed}, got {speed}"
            )
        
        self.timeline.set_speed(speed)
        self._notify_speed_change()
        
        self.logger.info(f"Playback speed set to {speed}x")
    
    def increase_speed(self) -> float:
        """
        Increase playback speed by one step.
        
        Returns:
            New speed value
        """
        current_speed = self.timeline.state.playback_speed
        new_speed = min(
            current_speed + self.config.speed_step,
            self.config.max_speed
        )
        self.set_speed(new_speed)
        return new_speed
    
    def decrease_speed(self) -> float:
        """
        Decrease playback speed by one step.
        
        Returns:
            New speed value
        """
        current_speed = self.timeline.state.playback_speed
        new_speed = max(
            current_speed - self.config.speed_step,
            self.config.min_speed
        )
        self.set_speed(new_speed)
        return new_speed
    
    def set_speed_preset(self, preset: str) -> None:
        """
        Set playback speed to a preset value.
        
        Args:
            preset: Preset name ('slow', 'normal', 'fast', 'very_fast')
            
        Raises:
            ValueError: If preset is unknown
        """
        presets = {
            'slow': 0.5,
            'normal': 1.0,
            'fast': 2.0,
            'very_fast': 4.0
        }
        
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}")
        
        self.set_speed(presets[preset])
    
    def reset_speed(self) -> None:
        """Reset playback speed to default."""
        self.set_speed(self.config.default_speed)
    
    def get_state(self) -> PlaybackState:
        """Get current playback state."""
        return self._state
    
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._state == PlaybackState.PLAYING
    
    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._state == PlaybackState.PAUSED
    
    def is_stopped(self) -> bool:
        """Check if currently stopped."""
        return self._state == PlaybackState.STOPPED
    
    def get_playback_info(self) -> Dict[str, Any]:
        """
        Get comprehensive playback information.
        
        Returns:
            Dictionary with playback state and timeline info
        """
        timeline_info = self.timeline.get_timeline_info()
        
        return {
            'state': self._state.value,
            'is_playing': self.is_playing(),
            'is_paused': self.is_paused(),
            'is_stopped': self.is_stopped(),
            'speed': self.timeline.state.playback_speed,
            'speed_range': {
                'min': self.config.min_speed,
                'max': self.config.max_speed,
                'default': self.config.default_speed
            },
            **timeline_info
        }
    
    def update(self, delta_time: Optional[float] = None) -> CityState:
        """
        Update playback state.
        
        This method should be called every frame.
        
        Args:
            delta_time: Time elapsed since last update in seconds
            
        Returns:
            Current CityState for rendering
        """
        # Update timeline
        city_state = self.timeline.update(delta_time)
        
        # Update animations if system is available
        if self.animation_system:
            self.animation_system.update(self.timeline.state.current_time)
        
        # Check if playback completed
        if self._state == PlaybackState.PLAYING and not self.timeline.is_playing():
            self._state = PlaybackState.STOPPED
            self._notify_state_change()
            self.logger.info("Playback completed")
        
        return city_state
    
    def on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        """
        Register callback for state changes.
        
        Args:
            callback: Function to call when state changes
        """
        self._on_state_change_callbacks.append(callback)
    
    def on_speed_change(self, callback: Callable[[float], None]) -> None:
        """
        Register callback for speed changes.
        
        Args:
            callback: Function to call when speed changes
        """
        self._on_speed_change_callbacks.append(callback)
    
    def _notify_state_change(self) -> None:
        """Notify all state change callbacks."""
        for callback in self._on_state_change_callbacks:
            try:
                callback(self._state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
    
    def _notify_speed_change(self) -> None:
        """Notify all speed change callbacks."""
        speed = self.timeline.state.playback_speed
        for callback in self._on_speed_change_callbacks:
            try:
                callback(speed)
            except Exception as e:
                self.logger.error(f"Error in speed change callback: {e}")


# Made with Bob