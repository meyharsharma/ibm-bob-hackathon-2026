"""Animation system - manages building lifecycle animations."""

import math
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..city.city_generator import Building, CityState
from ..utils.logger import setup_logger
from ..utils.config import Config


class AnimationType(Enum):
    """Types of animations for buildings."""
    GROW = "grow"           # Building rising from ground
    SHRINK = "shrink"       # Building shrinking
    CRUMBLE = "crumble"     # Building crumbling/falling
    FADE_OUT = "fade_out"   # Building fading away
    PULSE = "pulse"         # Building pulsing (for large changes)
    NONE = "none"           # No animation


class EasingFunction(Enum):
    """Easing functions for smooth animations."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


@dataclass
class Animation:
    """
    Represents a single animation instance.
    
    Attributes:
        file_path: Path to file being animated
        animation_type: Type of animation
        start_time: Animation start time
        duration: Animation duration in seconds
        easing: Easing function to use
        start_value: Starting value for interpolation
        end_value: Ending value for interpolation
        current_value: Current interpolated value
        is_complete: Whether animation has completed
        metadata: Additional animation-specific data
    """
    file_path: str
    animation_type: AnimationType
    start_time: float
    duration: float
    easing: EasingFunction = EasingFunction.EASE_OUT
    start_value: float = 0.0
    end_value: float = 1.0
    current_value: float = 0.0
    is_complete: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def update(self, current_time: float) -> float:
        """
        Update animation and return current value.
        
        Args:
            current_time: Current time in seconds
            
        Returns:
            Current interpolated value (0.0 to 1.0)
        """
        if self.is_complete:
            return self.end_value
        
        # Calculate progress (0.0 to 1.0)
        elapsed = current_time - self.start_time
        if elapsed >= self.duration:
            self.is_complete = True
            self.current_value = self.end_value
            return self.end_value
        
        progress = elapsed / self.duration if self.duration > 0 else 1.0
        
        # Apply easing function
        eased_progress = self._apply_easing(progress)
        
        # Interpolate between start and end values
        self.current_value = self.start_value + (self.end_value - self.start_value) * eased_progress
        
        return self.current_value
    
    def _apply_easing(self, t: float) -> float:
        """
        Apply easing function to progress value.
        
        Args:
            t: Progress value (0.0 to 1.0)
            
        Returns:
            Eased progress value
        """
        if self.easing == EasingFunction.LINEAR:
            return t
        
        elif self.easing == EasingFunction.EASE_IN:
            return t * t
        
        elif self.easing == EasingFunction.EASE_OUT:
            return 1 - (1 - t) * (1 - t)
        
        elif self.easing == EasingFunction.EASE_IN_OUT:
            if t < 0.5:
                return 2 * t * t
            else:
                return 1 - 2 * (1 - t) * (1 - t)
        
        elif self.easing == EasingFunction.BOUNCE:
            # Bounce effect at the end
            if t < 0.5:
                return 2 * t * t
            else:
                t = (t - 0.5) * 2
                return 0.5 + 0.5 * (1 - abs(math.sin(t * math.pi * 3)))
        
        elif self.easing == EasingFunction.ELASTIC:
            # Elastic overshoot effect
            if t == 0 or t == 1:
                return t
            return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1
        
        return t


@dataclass
class BuildingAnimationState:
    """
    Tracks the animation state of a building.
    
    Attributes:
        building: The building being animated
        active_animations: List of currently active animations
        scale: Current scale factor (for grow/shrink)
        opacity: Current opacity (for fade effects)
        offset: Current position offset (for crumble effects)
        pulse_intensity: Current pulse intensity
    """
    building: Building
    active_animations: List[Animation] = field(default_factory=list)
    scale: float = 1.0
    opacity: float = 1.0
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    pulse_intensity: float = 0.0
    
    def has_active_animations(self) -> bool:
        """Check if building has any active animations."""
        return len(self.active_animations) > 0
    
    def get_transform_matrix(self) -> Tuple[float, float, float]:
        """
        Get transformation parameters for rendering.
        
        Returns:
            Tuple of (scale, opacity, z_offset)
        """
        z_offset = self.offset[2]
        return (self.scale, self.opacity, z_offset)


class AnimationSystem:
    """
    Manages building lifecycle animations.
    
    This class handles all animations for buildings in the city, including:
    - New files appearing (grow animation)
    - Deleted files disappearing (crumble/fade-out)
    - Large changes (pulse animation)
    - Smooth interpolation between states
    
    Features:
    - Multiple simultaneous animations per building
    - Configurable animation durations and easing
    - Automatic animation lifecycle management
    - Visual distinction for different change magnitudes
    - Smooth interpolation with various easing functions
    
    Architecture:
    - Maintains animation state for each building
    - Updates all animations each frame
    - Provides rendering parameters for animated buildings
    - Automatically cleans up completed animations
    
    Example:
        ```python
        anim_system = AnimationSystem()
        
        # Animate new file
        anim_system.animate_file_added("src/app.py", building, current_time)
        
        # Update animations each frame
        anim_system.update(current_time)
        
        # Get rendering state
        state = anim_system.get_building_state("src/app.py")
        scale, opacity, z_offset = state.get_transform_matrix()
        ```
    """
    
    # Default animation durations (seconds)
    DEFAULT_GROW_DURATION = 1.0
    DEFAULT_SHRINK_DURATION = 0.8
    DEFAULT_CRUMBLE_DURATION = 1.2
    DEFAULT_FADE_DURATION = 0.5
    DEFAULT_PULSE_DURATION = 0.6
    
    # Change magnitude thresholds
    SMALL_CHANGE_THRESHOLD = 10    # lines
    MEDIUM_CHANGE_THRESHOLD = 50   # lines
    LARGE_CHANGE_THRESHOLD = 200   # lines
    
    def __init__(self):
        """Initialize the animation system."""
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        # Building animation states: file_path -> BuildingAnimationState
        self._animation_states: Dict[str, BuildingAnimationState] = {}
        
        # Animation completion callbacks
        self._on_animation_complete_callbacks: List[Callable[[str, AnimationType], None]] = []
        
        self.logger.info("Initialized AnimationSystem")
    
    def animate_file_added(
        self,
        file_path: str,
        building: Building,
        current_time: float,
        duration: Optional[float] = None
    ) -> None:
        """
        Animate a new file appearing (building rising from ground).
        
        Args:
            file_path: Path to the file
            building: Building object
            current_time: Current time in seconds
            duration: Animation duration (uses default if None)
        """
        duration = duration or self.DEFAULT_GROW_DURATION
        
        # Create or get animation state
        state = self._get_or_create_state(file_path, building)
        
        # Start with scale 0 (invisible)
        state.scale = 0.0
        
        # Create grow animation
        animation = Animation(
            file_path=file_path,
            animation_type=AnimationType.GROW,
            start_time=current_time,
            duration=duration,
            easing=EasingFunction.EASE_OUT,
            start_value=0.0,
            end_value=1.0,
            metadata={'building_height': building.height}
        )
        
        state.active_animations.append(animation)
        
        self.logger.debug(f"Started grow animation for {file_path}")
    
    def animate_file_deleted(
        self,
        file_path: str,
        building: Building,
        current_time: float,
        use_crumble: bool = True,
        duration: Optional[float] = None
    ) -> None:
        """
        Animate a file being deleted (building disappearing).
        
        Args:
            file_path: Path to the file
            building: Building object
            current_time: Current time in seconds
            use_crumble: If True, use crumble effect; otherwise fade out
            duration: Animation duration (uses default if None)
        """
        if use_crumble:
            duration = duration or self.DEFAULT_CRUMBLE_DURATION
            animation_type = AnimationType.CRUMBLE
            easing = EasingFunction.EASE_IN
        else:
            duration = duration or self.DEFAULT_FADE_DURATION
            animation_type = AnimationType.FADE_OUT
            easing = EasingFunction.LINEAR
        
        # Create or get animation state
        state = self._get_or_create_state(file_path, building)
        
        # Create disappear animation
        if use_crumble:
            # Crumble: shrink and fall
            shrink_anim = Animation(
                file_path=file_path,
                animation_type=animation_type,
                start_time=current_time,
                duration=duration,
                easing=easing,
                start_value=1.0,
                end_value=0.0,
                metadata={'effect': 'shrink'}
            )
            
            fall_anim = Animation(
                file_path=file_path,
                animation_type=animation_type,
                start_time=current_time,
                duration=duration,
                easing=EasingFunction.EASE_IN,
                start_value=0.0,
                end_value=-building.height,
                metadata={'effect': 'fall'}
            )
            
            state.active_animations.extend([shrink_anim, fall_anim])
        else:
            # Fade out
            fade_anim = Animation(
                file_path=file_path,
                animation_type=animation_type,
                start_time=current_time,
                duration=duration,
                easing=easing,
                start_value=1.0,
                end_value=0.0,
                metadata={'effect': 'fade'}
            )
            
            state.active_animations.append(fade_anim)
        
        self.logger.debug(
            f"Started {'crumble' if use_crumble else 'fade'} animation for {file_path}"
        )
    
    def animate_file_modified(
        self,
        file_path: str,
        building: Building,
        current_time: float,
        lines_changed: int,
        duration: Optional[float] = None
    ) -> None:
        """
        Animate a file modification (pulse for large changes).
        
        Args:
            file_path: Path to the file
            building: Building object
            current_time: Current time in seconds
            lines_changed: Number of lines changed
            duration: Animation duration (uses default if None)
        """
        # Only animate if change is significant
        if lines_changed < self.SMALL_CHANGE_THRESHOLD:
            return
        
        duration = duration or self.DEFAULT_PULSE_DURATION
        
        # Create or get animation state
        state = self._get_or_create_state(file_path, building)
        
        # Calculate pulse intensity based on change magnitude
        if lines_changed >= self.LARGE_CHANGE_THRESHOLD:
            intensity = 0.3  # Strong pulse
        elif lines_changed >= self.MEDIUM_CHANGE_THRESHOLD:
            intensity = 0.2  # Medium pulse
        else:
            intensity = 0.1  # Subtle pulse
        
        # Create pulse animation (scale up then back down)
        pulse_anim = Animation(
            file_path=file_path,
            animation_type=AnimationType.PULSE,
            start_time=current_time,
            duration=duration,
            easing=EasingFunction.EASE_IN_OUT,
            start_value=0.0,
            end_value=0.0,  # Returns to 0
            metadata={
                'intensity': intensity,
                'lines_changed': lines_changed
            }
        )
        
        state.active_animations.append(pulse_anim)
        
        self.logger.debug(
            f"Started pulse animation for {file_path} "
            f"(intensity={intensity}, lines={lines_changed})"
        )
    
    def update(self, current_time: float) -> None:
        """
        Update all active animations.
        
        This method should be called every frame to update animation states.
        
        Args:
            current_time: Current time in seconds
        """
        completed_animations = []
        
        for file_path, state in self._animation_states.items():
            if not state.has_active_animations():
                continue
            
            # Update each animation
            for animation in state.active_animations:
                value = animation.update(current_time)
                
                # Apply animation effect based on type
                if animation.animation_type == AnimationType.GROW:
                    state.scale = value
                
                elif animation.animation_type == AnimationType.CRUMBLE:
                    if animation.metadata.get('effect') == 'shrink':
                        state.scale = value
                    elif animation.metadata.get('effect') == 'fall':
                        state.offset = (0.0, 0.0, value)
                
                elif animation.animation_type == AnimationType.FADE_OUT:
                    state.opacity = value
                
                elif animation.animation_type == AnimationType.PULSE:
                    # Pulse: scale oscillates
                    intensity = animation.metadata.get('intensity', 0.1)
                    progress = (current_time - animation.start_time) / animation.duration
                    # Use sine wave for smooth pulse
                    pulse_value = math.sin(progress * math.pi) * intensity
                    state.scale = 1.0 + pulse_value
                    state.pulse_intensity = pulse_value
                
                # Track completed animations
                if animation.is_complete:
                    completed_animations.append((file_path, animation))
        
        # Remove completed animations and notify callbacks
        for file_path, animation in completed_animations:
            state = self._animation_states.get(file_path)
            if state:
                state.active_animations.remove(animation)
                self._notify_animation_complete(file_path, animation.animation_type)
        
        # Clean up states with no active animations
        self._cleanup_inactive_states()
    
    def get_building_state(self, file_path: str) -> Optional[BuildingAnimationState]:
        """
        Get animation state for a building.
        
        Args:
            file_path: Path to the file
            
        Returns:
            BuildingAnimationState or None if not animated
        """
        return self._animation_states.get(file_path)
    
    def is_animating(self, file_path: str) -> bool:
        """
        Check if a building is currently animating.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if building has active animations
        """
        state = self._animation_states.get(file_path)
        return state is not None and state.has_active_animations()
    
    def stop_animations(self, file_path: str) -> None:
        """
        Stop all animations for a building.
        
        Args:
            file_path: Path to the file
        """
        if file_path in self._animation_states:
            self._animation_states[file_path].active_animations.clear()
            self.logger.debug(f"Stopped all animations for {file_path}")
    
    def clear_all_animations(self) -> None:
        """Clear all active animations."""
        self._animation_states.clear()
        self.logger.info("Cleared all animations")
    
    def on_animation_complete(
        self,
        callback: Callable[[str, AnimationType], None]
    ) -> None:
        """
        Register callback for animation completion.
        
        Args:
            callback: Function to call when animation completes (file_path, animation_type)
        """
        self._on_animation_complete_callbacks.append(callback)
    
    def get_active_animation_count(self) -> int:
        """Get total number of active animations."""
        return sum(
            len(state.active_animations)
            for state in self._animation_states.values()
        )
    
    def _get_or_create_state(
        self,
        file_path: str,
        building: Building
    ) -> BuildingAnimationState:
        """Get or create animation state for a building."""
        if file_path not in self._animation_states:
            self._animation_states[file_path] = BuildingAnimationState(
                building=building
            )
        return self._animation_states[file_path]
    
    def _cleanup_inactive_states(self) -> None:
        """Remove animation states with no active animations."""
        inactive = [
            file_path for file_path, state in self._animation_states.items()
            if not state.has_active_animations()
        ]
        
        for file_path in inactive:
            del self._animation_states[file_path]
    
    def _notify_animation_complete(
        self,
        file_path: str,
        animation_type: AnimationType
    ) -> None:
        """Notify all animation complete callbacks."""
        for callback in self._on_animation_complete_callbacks:
            try:
                callback(file_path, animation_type)
            except Exception as e:
                self.logger.error(f"Error in animation complete callback: {e}")


# Made with Bob