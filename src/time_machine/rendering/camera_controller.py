"""Camera controller - user input handling for camera movement."""

import time
from typing import Optional, Tuple, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    from pyrr import Vector3
except ImportError:
    raise ImportError("pyrr not installed. Install with: pip install pyrr")

from .city_renderer import Camera
from ..utils.logger import setup_logger
from ..utils.config import Config


class InputType(Enum):
    """Types of camera input."""
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    TOUCH = "touch"


@dataclass
class CameraInputState:
    """
    Tracks the state of camera input.
    
    Attributes:
        mouse_x: Current mouse X position
        mouse_y: Current mouse Y position
        mouse_left_down: Left mouse button state
        mouse_right_down: Right mouse button state
        mouse_middle_down: Middle mouse button state
        keys_pressed: Set of currently pressed keys
        last_update_time: Last input update time
    """
    mouse_x: float = 0.0
    mouse_y: float = 0.0
    mouse_left_down: bool = False
    mouse_right_down: bool = False
    mouse_middle_down: bool = False
    keys_pressed: Set[str] = field(default_factory=set)
    last_update_time: float = 0.0


@dataclass
class CameraControlConfig:
    """
    Configuration for camera controls.
    
    Attributes:
        orbit_sensitivity: Mouse sensitivity for orbit (degrees per pixel)
        pan_sensitivity: Mouse sensitivity for pan (units per pixel)
        zoom_sensitivity: Mouse wheel sensitivity (units per tick)
        keyboard_move_speed: Keyboard movement speed (units per second)
        keyboard_rotate_speed: Keyboard rotation speed (degrees per second)
        smooth_factor: Smoothing factor for camera movement (0.0 = instant, 1.0 = very smooth)
        min_distance: Minimum camera distance from target
        max_distance: Maximum camera distance from target
        invert_y: Invert Y-axis for orbit
    """
    orbit_sensitivity: float = 0.3
    pan_sensitivity: float = 0.05
    zoom_sensitivity: float = 2.0
    keyboard_move_speed: float = 10.0
    keyboard_rotate_speed: float = 45.0
    smooth_factor: float = 0.15
    min_distance: float = 5.0
    max_distance: float = 500.0
    invert_y: bool = False


class CameraController:
    """
    Handles user input for camera control.
    
    This class extends the Camera functionality with user input handling,
    providing responsive and smooth camera controls for exploring the 3D city.
    
    Features:
    - Mouse controls (orbit, pan, zoom)
    - Keyboard controls (WASD movement, arrow keys rotation)
    - Smooth camera transitions with interpolation
    - Configurable sensitivity and constraints
    - Multiple input modes (mouse, keyboard, touch)
    - Sub-second response time for all inputs
    
    Mouse Controls:
    - Left drag: Orbit around target
    - Right drag: Pan camera
    - Middle drag: Pan camera (alternative)
    - Scroll wheel: Zoom in/out
    
    Keyboard Controls:
    - W/S: Move forward/backward
    - A/D: Move left/right
    - Q/E: Move up/down
    - Arrow keys: Rotate camera
    - +/-: Zoom in/out
    
    Architecture:
    - Wraps Camera class with input handling
    - Maintains input state for smooth transitions
    - Applies constraints (min/max distance, etc.)
    - Uses delta time for frame-independent movement
    - Provides smooth interpolation for natural feel
    
    Example:
        ```python
        camera = Camera(position=Vector3([50, 50, 50]), target=Vector3([0, 0, 0]))
        controller = CameraController(camera)
        
        # Handle mouse input
        controller.on_mouse_move(x, y)
        controller.on_mouse_button(button='left', pressed=True)
        
        # Handle keyboard input
        controller.on_key_press('w')
        
        # Update camera each frame
        controller.update(delta_time)
        ```
    """
    
    def __init__(
        self,
        camera: Camera,
        config: Optional[CameraControlConfig] = None
    ):
        """
        Initialize the camera controller.
        
        Args:
            camera: Camera instance to control
            config: CameraControlConfig (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.camera = camera
        self.config = config or CameraControlConfig()
        
        # Input state
        self.input_state = CameraInputState()
        
        # Target values for smooth interpolation
        self._target_position: Optional[Vector3] = None
        self._target_target: Optional[Vector3] = None
        
        # Manual control flag (for auto-camera override)
        self._manual_control_active = False
        self._manual_control_time: Optional[float] = None
        
        self.logger.info("Initialized CameraController")
    
    def on_mouse_move(self, x: float, y: float) -> None:
        """
        Handle mouse movement.
        
        Args:
            x: Mouse X position
            y: Mouse Y position
        """
        # Calculate delta from last position
        delta_x = x - self.input_state.mouse_x
        delta_y = y - self.input_state.mouse_y
        
        # Update position
        self.input_state.mouse_x = x
        self.input_state.mouse_y = y
        
        # Apply camera movement based on button state
        if self.input_state.mouse_left_down:
            # Orbit camera
            self._orbit_camera(delta_x, delta_y)
            self._activate_manual_control()
        
        elif self.input_state.mouse_right_down or self.input_state.mouse_middle_down:
            # Pan camera
            self._pan_camera(delta_x, delta_y)
            self._activate_manual_control()
    
    def on_mouse_button(self, button: str, pressed: bool) -> None:
        """
        Handle mouse button press/release.
        
        Args:
            button: Button name ('left', 'right', 'middle')
            pressed: True if pressed, False if released
        """
        if button == 'left':
            self.input_state.mouse_left_down = pressed
        elif button == 'right':
            self.input_state.mouse_right_down = pressed
        elif button == 'middle':
            self.input_state.mouse_middle_down = pressed
    
    def on_mouse_scroll(self, delta: float) -> None:
        """
        Handle mouse scroll (zoom).
        
        Args:
            delta: Scroll delta (positive = zoom in, negative = zoom out)
        """
        zoom_amount = delta * self.config.zoom_sensitivity
        self._zoom_camera(zoom_amount)
        self._activate_manual_control()
    
    def on_key_press(self, key: str) -> None:
        """
        Handle key press.
        
        Args:
            key: Key name (e.g., 'w', 'a', 's', 'd', 'up', 'down')
        """
        self.input_state.keys_pressed.add(key.lower())
    
    def on_key_release(self, key: str) -> None:
        """
        Handle key release.
        
        Args:
            key: Key name
        """
        self.input_state.keys_pressed.discard(key.lower())
    
    def update(self, delta_time: float) -> None:
        """
        Update camera based on input state.
        
        This method should be called every frame.
        
        Args:
            delta_time: Time elapsed since last update in seconds
        """
        # Process keyboard input
        self._process_keyboard_input(delta_time)
        
        # Apply smooth interpolation if target values are set
        if self._target_position is not None:
            self._smooth_to_target(delta_time)
        
        # Update input state time
        self.input_state.last_update_time = time.time()
    
    def set_target_position(
        self,
        position: Vector3,
        target: Optional[Vector3] = None
    ) -> None:
        """
        Set target camera position for smooth transition.
        
        Args:
            position: Target camera position
            target: Target look-at point (keeps current if None)
        """
        self._target_position = position
        if target is not None:
            self._target_target = target
    
    def reset_to_default(self, position: Vector3, target: Vector3) -> None:
        """
        Reset camera to default position.
        
        Args:
            position: Default camera position
            target: Default look-at target
        """
        self.camera.position = position
        self.camera.target = target
        self._target_position = None
        self._target_target = None
        self._manual_control_active = False
        
        self.logger.info("Camera reset to default position")
    
    def is_manual_control_active(self) -> bool:
        """
        Check if user has taken manual control.
        
        Returns:
            True if user is actively controlling camera
        """
        return self._manual_control_active
    
    def clear_manual_control(self) -> None:
        """Clear manual control flag (for auto-camera takeover)."""
        self._manual_control_active = False
        self._manual_control_time = None
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Get information about camera state.
        
        Returns:
            Dictionary with camera information
        """
        direction = self.camera.target - self.camera.position
        distance = direction.length
        
        return {
            'position': list(self.camera.position),
            'target': list(self.camera.target),
            'distance': distance,
            'fov': self.camera.fov,
            'manual_control_active': self._manual_control_active,
            'input_active': (
                self.input_state.mouse_left_down or
                self.input_state.mouse_right_down or
                len(self.input_state.keys_pressed) > 0
            )
        }
    
    def _orbit_camera(self, delta_x: float, delta_y: float) -> None:
        """
        Orbit camera around target.
        
        Args:
            delta_x: Mouse X delta
            delta_y: Mouse Y delta
        """
        # Convert pixel delta to angle delta
        azimuth_delta = -delta_x * self.config.orbit_sensitivity
        elevation_delta = delta_y * self.config.orbit_sensitivity
        
        # Invert Y if configured
        if self.config.invert_y:
            elevation_delta = -elevation_delta
        
        # Apply orbit
        self.camera.orbit(azimuth_delta, elevation_delta)
    
    def _pan_camera(self, delta_x: float, delta_y: float) -> None:
        """
        Pan camera.
        
        Args:
            delta_x: Mouse X delta
            delta_y: Mouse Y delta
        """
        # Convert pixel delta to world units
        pan_x = -delta_x * self.config.pan_sensitivity
        pan_y = delta_y * self.config.pan_sensitivity
        
        # Apply pan
        self.camera.pan(pan_x, pan_y)
    
    def _zoom_camera(self, amount: float) -> None:
        """
        Zoom camera.
        
        Args:
            amount: Zoom amount (positive = zoom in)
        """
        # Apply zoom with distance constraints
        direction = self.camera.target - self.camera.position
        current_distance = direction.length
        
        # Calculate new distance
        new_distance = current_distance - amount
        new_distance = max(self.config.min_distance, min(self.config.max_distance, new_distance))
        
        # Apply zoom
        zoom_delta = current_distance - new_distance
        self.camera.zoom(zoom_delta)
    
    def _process_keyboard_input(self, delta_time: float) -> None:
        """
        Process keyboard input for camera movement.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if not self.input_state.keys_pressed:
            return
        
        move_speed = self.config.keyboard_move_speed * delta_time
        rotate_speed = self.config.keyboard_rotate_speed * delta_time
        
        # Calculate camera vectors
        forward = (self.camera.target - self.camera.position).normalised
        right = forward.cross(self.camera.up).normalised
        up = self.camera.up if self.camera.up is not None else Vector3([0.0, 0.0, 1.0])
        
        # Movement (WASD + QE)
        movement = Vector3([0.0, 0.0, 0.0])
        
        if 'w' in self.input_state.keys_pressed:
            movement += forward * move_speed
        if 's' in self.input_state.keys_pressed:
            movement -= forward * move_speed
        if 'a' in self.input_state.keys_pressed:
            movement -= right * move_speed
        if 'd' in self.input_state.keys_pressed:
            movement += right * move_speed
        if 'q' in self.input_state.keys_pressed:
            movement -= up * move_speed
        if 'e' in self.input_state.keys_pressed:
            movement += up * move_speed
        
        # Apply movement
        if movement.length > 0:
            self.camera.position += movement
            self.camera.target += movement
            self._activate_manual_control()
        
        # Rotation (Arrow keys)
        if 'left' in self.input_state.keys_pressed:
            self.camera.orbit(rotate_speed, 0)
            self._activate_manual_control()
        if 'right' in self.input_state.keys_pressed:
            self.camera.orbit(-rotate_speed, 0)
            self._activate_manual_control()
        if 'up' in self.input_state.keys_pressed:
            self.camera.orbit(0, rotate_speed)
            self._activate_manual_control()
        if 'down' in self.input_state.keys_pressed:
            self.camera.orbit(0, -rotate_speed)
            self._activate_manual_control()
        
        # Zoom (+/-)
        if '+' in self.input_state.keys_pressed or '=' in self.input_state.keys_pressed:
            self._zoom_camera(move_speed * 2)
            self._activate_manual_control()
        if '-' in self.input_state.keys_pressed or '_' in self.input_state.keys_pressed:
            self._zoom_camera(-move_speed * 2)
            self._activate_manual_control()
    
    def _smooth_to_target(self, delta_time: float) -> None:
        """
        Smoothly interpolate camera to target position.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if self._target_position is None:
            return
        
        # Calculate interpolation factor
        t = min(1.0, self.config.smooth_factor * delta_time * 60.0)  # Normalize to 60 FPS
        
        # Interpolate position
        self.camera.position = self.camera.position + (self._target_position - self.camera.position) * t
        
        # Interpolate target if set
        if self._target_target is not None:
            self.camera.target = self.camera.target + (self._target_target - self.camera.target) * t
        
        # Check if we've reached the target
        position_diff = (self._target_position - self.camera.position).length
        if position_diff < 0.1:
            self.camera.position = self._target_position
            self._target_position = None
            
            if self._target_target is not None:
                self.camera.target = self._target_target
                self._target_target = None
    
    def _activate_manual_control(self) -> None:
        """Mark that user has taken manual control."""
        if not self._manual_control_active:
            self._manual_control_active = True
            self._manual_control_time = time.time()
            self.logger.debug("Manual camera control activated")


# Made with Bob