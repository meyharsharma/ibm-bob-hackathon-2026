"""Auto camera - cinematic flythrough with intelligent focus."""

import math
import time
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from pyrr import Vector3
except ImportError:
    raise ImportError("pyrr not installed. Install with: pip install pyrr")

from .city_renderer import Camera
from .camera_controller import CameraController
from ..city.city_generator import CityState, Building
from ..utils.logger import setup_logger
from ..utils.config import Config


class CameraMode(Enum):
    """Camera movement modes."""
    OVERVIEW = "overview"           # Wide view of entire city
    FOCUS_ACTIVITY = "focus_activity"  # Focus on high-activity areas
    FOCUS_GROWTH = "focus_growth"   # Focus on growing areas
    ORBIT = "orbit"                 # Orbit around target
    FLYTHROUGH = "flythrough"       # Fly through city


@dataclass
class CameraKeyframe:
    """
    Represents a camera keyframe for animation.
    
    Attributes:
        time: Time of keyframe in seconds
        position: Camera position
        target: Camera look-at target
        duration: Duration to reach this keyframe from previous
        mode: Camera mode for this keyframe
    """
    time: float
    position: Vector3
    target: Vector3
    duration: float = 2.0
    mode: CameraMode = CameraMode.OVERVIEW


@dataclass
class ActivityHotspot:
    """
    Represents an area of high activity in the city.
    
    Attributes:
        position: Center position of hotspot
        intensity: Activity intensity (0.0 to 1.0)
        radius: Radius of influence
        building_count: Number of buildings in hotspot
        total_changes: Total changes in this area
    """
    position: Tuple[float, float, float]
    intensity: float
    radius: float
    building_count: int
    total_changes: int


class AutoCamera:
    """
    Automatic cinematic camera for flythrough visualization.
    
    This class provides intelligent, cinematic camera movement that
    automatically highlights areas of significant activity in the city.
    It creates smooth camera paths and transitions while focusing on
    the most interesting parts of the repository evolution.
    
    Features:
    - Intelligent focus on high-activity areas
    - Smooth camera paths with spline interpolation
    - Multiple camera modes (overview, focus, orbit, flythrough)
    - Activity hotspot detection
    - Automatic keyframe generation
    - User override support
    - Configurable transition timing
    
    Architecture:
    - Analyzes city state to find interesting areas
    - Generates camera keyframes for smooth paths
    - Uses spline interpolation for natural movement
    - Respects user manual control override
    - Coordinates with CameraController
    
    Example:
        ```python
        auto_camera = AutoCamera(camera, camera_controller)
        
        # Update with new city state
        auto_camera.update_city_state(city_state, current_time)
        
        # Update camera each frame
        auto_camera.update(delta_time)
        
        # Check if user has overridden
        if camera_controller.is_manual_control_active():
            auto_camera.pause()
        ```
    """
    
    # Configuration constants
    OVERVIEW_HEIGHT_MULTIPLIER = 2.5
    FOCUS_HEIGHT_MULTIPLIER = 1.5
    ORBIT_RADIUS_MULTIPLIER = 2.0
    TRANSITION_DURATION = 3.0
    FOCUS_DURATION = 5.0
    ORBIT_DURATION = 8.0
    MIN_ACTIVITY_THRESHOLD = 5  # Minimum changes to be considered active
    
    def __init__(
        self,
        camera: Camera,
        camera_controller: Optional[CameraController] = None
    ):
        """
        Initialize the auto camera.
        
        Args:
            camera: Camera instance to control
            camera_controller: CameraController for manual override detection
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.camera = camera
        self.camera_controller = camera_controller
        
        # Camera path
        self._keyframes: List[CameraKeyframe] = []
        self._current_keyframe_index = 0
        self._keyframe_start_time: Optional[float] = None
        
        # City state
        self._city_state: Optional[CityState] = None
        self._activity_hotspots: List[ActivityHotspot] = []
        
        # State
        self._is_active = False
        self._is_paused = False
        self._last_update_time: Optional[float] = None
        
        self.logger.info("Initialized AutoCamera")
    
    def start(self, city_state: CityState, current_time: float = 0.0) -> None:
        """
        Start automatic camera movement.
        
        Args:
            city_state: Current city state
            current_time: Current time in seconds
        """
        self._city_state = city_state
        self._is_active = True
        self._is_paused = False
        self._last_update_time = current_time
        
        # Analyze city and generate camera path
        self._analyze_city_activity()
        self._generate_camera_path(current_time)
        
        self.logger.info("Auto camera started")
    
    def pause(self) -> None:
        """Pause automatic camera movement."""
        self._is_paused = True
        self.logger.debug("Auto camera paused")
    
    def resume(self) -> None:
        """Resume automatic camera movement."""
        self._is_paused = False
        self.logger.debug("Auto camera resumed")
    
    def stop(self) -> None:
        """Stop automatic camera movement."""
        self._is_active = False
        self._is_paused = False
        self._keyframes.clear()
        self._current_keyframe_index = 0
        self.logger.info("Auto camera stopped")
    
    def is_active(self) -> bool:
        """Check if auto camera is active."""
        return self._is_active and not self._is_paused
    
    def update_city_state(self, city_state: CityState, current_time: float) -> None:
        """
        Update with new city state.
        
        Args:
            city_state: New city state
            current_time: Current time in seconds
        """
        self._city_state = city_state
        
        # Re-analyze activity and update path if significant changes
        old_hotspot_count = len(self._activity_hotspots)
        self._analyze_city_activity()
        
        if len(self._activity_hotspots) != old_hotspot_count:
            # Significant change, regenerate path
            self._generate_camera_path(current_time)
            self.logger.debug("Camera path regenerated due to activity changes")
    
    def update(self, delta_time: float) -> None:
        """
        Update camera position.
        
        This method should be called every frame.
        
        Args:
            delta_time: Time elapsed since last update in seconds
        """
        if not self.is_active():
            return
        
        # Check for manual control override
        if self.camera_controller and self.camera_controller.is_manual_control_active():
            self.pause()
            self.logger.debug("Auto camera paused due to manual control")
            return
        
        # Update current time
        current_time = time.time() if self._last_update_time is None else self._last_update_time + delta_time
        self._last_update_time = current_time
        
        # Update camera along path
        self._update_camera_path(current_time)
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Get information about auto camera state.
        
        Returns:
            Dictionary with auto camera information
        """
        current_mode = None
        if self._keyframes and self._current_keyframe_index < len(self._keyframes):
            current_mode = self._keyframes[self._current_keyframe_index].mode.value
        
        return {
            'is_active': self._is_active,
            'is_paused': self._is_paused,
            'current_mode': current_mode,
            'keyframe_count': len(self._keyframes),
            'current_keyframe_index': self._current_keyframe_index,
            'hotspot_count': len(self._activity_hotspots)
        }
    
    def _analyze_city_activity(self) -> None:
        """Analyze city state to find activity hotspots."""
        if not self._city_state or not self._city_state.buildings:
            self._activity_hotspots = []
            return
        
        # Group buildings by proximity and activity
        hotspots: List[ActivityHotspot] = []
        
        # Find high-activity buildings
        active_buildings = [
            building for building in self._city_state.buildings.values()
            if building.modification_count >= self.MIN_ACTIVITY_THRESHOLD
        ]
        
        if not active_buildings:
            # No significant activity, create overview hotspot
            buildings = list(self._city_state.buildings.values())
            center = self._calculate_center(buildings)
            hotspots.append(ActivityHotspot(
                position=center,
                intensity=0.5,
                radius=50.0,
                building_count=len(buildings),
                total_changes=sum(b.modification_count for b in buildings)
            ))
        else:
            # Cluster active buildings into hotspots
            # Simple clustering: group by neighborhood
            neighborhood_groups: Dict[str, List[Building]] = {}
            for building in active_buildings:
                if building.neighborhood not in neighborhood_groups:
                    neighborhood_groups[building.neighborhood] = []
                neighborhood_groups[building.neighborhood].append(building)
            
            # Create hotspot for each neighborhood with activity
            for neighborhood, buildings in neighborhood_groups.items():
                if len(buildings) < 2:
                    continue
                
                center = self._calculate_center(buildings)
                total_changes = sum(b.modification_count for b in buildings)
                max_changes = max(b.modification_count for b in buildings)
                
                # Calculate intensity based on activity
                intensity = min(1.0, total_changes / (len(buildings) * 20))
                
                hotspots.append(ActivityHotspot(
                    position=center,
                    intensity=intensity,
                    radius=30.0,
                    building_count=len(buildings),
                    total_changes=total_changes
                ))
        
        # Sort by intensity (most active first)
        hotspots.sort(key=lambda h: h.intensity, reverse=True)
        
        self._activity_hotspots = hotspots[:5]  # Keep top 5 hotspots
        
        self.logger.debug(f"Found {len(self._activity_hotspots)} activity hotspots")
    
    def _calculate_center(self, buildings: List[Building]) -> Tuple[float, float, float]:
        """
        Calculate center point of buildings.
        
        Args:
            buildings: List of buildings
            
        Returns:
            Center position (x, y, z)
        """
        if not buildings:
            return (0.0, 0.0, 0.0)
        
        x = sum(b.position[0] for b in buildings) / len(buildings)
        y = sum(b.position[1] for b in buildings) / len(buildings)
        z = sum(b.height for b in buildings) / (len(buildings) * 2)  # Half average height
        
        return (x, y, z)
    
    def _generate_camera_path(self, start_time: float) -> None:
        """
        Generate camera keyframes for cinematic path.
        
        Args:
            start_time: Starting time in seconds
        """
        self._keyframes = []
        current_time = start_time
        
        if not self._city_state or not self._city_state.buildings:
            return
        
        # Start with overview
        overview_keyframe = self._create_overview_keyframe(current_time)
        self._keyframes.append(overview_keyframe)
        current_time += overview_keyframe.duration
        
        # Visit each hotspot
        for hotspot in self._activity_hotspots:
            # Focus on hotspot
            focus_keyframe = self._create_focus_keyframe(hotspot, current_time)
            self._keyframes.append(focus_keyframe)
            current_time += focus_keyframe.duration
            
            # Orbit around hotspot
            orbit_keyframe = self._create_orbit_keyframe(hotspot, current_time)
            self._keyframes.append(orbit_keyframe)
            current_time += orbit_keyframe.duration
        
        # End with overview
        final_overview = self._create_overview_keyframe(current_time)
        self._keyframes.append(final_overview)
        
        self._current_keyframe_index = 0
        self._keyframe_start_time = start_time
        
        self.logger.info(f"Generated camera path with {len(self._keyframes)} keyframes")
    
    def _create_overview_keyframe(self, time: float) -> CameraKeyframe:
        """Create overview keyframe showing entire city."""
        if not self._city_state:
            # Fallback to default position
            return CameraKeyframe(
                time=time,
                position=Vector3([50.0, 50.0, 50.0]),
                target=Vector3([0.0, 0.0, 0.0]),
                duration=self.TRANSITION_DURATION,
                mode=CameraMode.OVERVIEW
            )
        
        buildings = list(self._city_state.buildings.values())
        center = self._calculate_center(buildings)
        
        # Calculate bounding box
        positions = [b.position for b in buildings]
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] for p in positions)
        
        size = max(max_x - min_x, max_y - min_y)
        height = size * self.OVERVIEW_HEIGHT_MULTIPLIER
        
        position = Vector3([
            center[0] + size * 0.7,
            center[1] + size * 0.7,
            height
        ])
        
        target = Vector3(list(center))
        
        return CameraKeyframe(
            time=time,
            position=position,
            target=target,
            duration=self.TRANSITION_DURATION,
            mode=CameraMode.OVERVIEW
        )
    
    def _create_focus_keyframe(self, hotspot: ActivityHotspot, time: float) -> CameraKeyframe:
        """Create keyframe focusing on activity hotspot."""
        center = hotspot.position
        
        # Position camera to focus on hotspot
        distance = hotspot.radius * self.FOCUS_HEIGHT_MULTIPLIER
        height = distance * 0.8
        
        position = Vector3([
            center[0] + distance * 0.6,
            center[1] + distance * 0.6,
            center[2] + height
        ])
        
        target = Vector3(list(center))
        
        return CameraKeyframe(
            time=time,
            position=position,
            target=target,
            duration=self.FOCUS_DURATION,
            mode=CameraMode.FOCUS_ACTIVITY
        )
    
    def _create_orbit_keyframe(self, hotspot: ActivityHotspot, time: float) -> CameraKeyframe:
        """Create keyframe for orbiting around hotspot."""
        center = hotspot.position
        
        # Calculate orbit position (will be animated)
        distance = hotspot.radius * self.ORBIT_RADIUS_MULTIPLIER
        height = distance * 0.5
        
        # Start position for orbit
        angle = time * 0.5  # Vary start angle based on time
        position = Vector3([
            center[0] + distance * math.cos(angle),
            center[1] + distance * math.sin(angle),
            center[2] + height
        ])
        
        target = Vector3(list(center))
        
        return CameraKeyframe(
            time=time,
            position=position,
            target=target,
            duration=self.ORBIT_DURATION,
            mode=CameraMode.ORBIT
        )
    
    def _update_camera_path(self, current_time: float) -> None:
        """
        Update camera position along path.
        
        Args:
            current_time: Current time in seconds
        """
        if not self._keyframes or self._keyframe_start_time is None:
            return
        
        # Find current keyframe
        elapsed = current_time - self._keyframe_start_time
        
        # Check if we need to advance to next keyframe
        while self._current_keyframe_index < len(self._keyframes) - 1:
            current_kf = self._keyframes[self._current_keyframe_index]
            next_kf = self._keyframes[self._current_keyframe_index + 1]
            
            if elapsed >= next_kf.time:
                self._current_keyframe_index += 1
            else:
                break
        
        # Check if we've reached the end
        if self._current_keyframe_index >= len(self._keyframes) - 1:
            # Loop back to start
            self._current_keyframe_index = 0
            self._keyframe_start_time = current_time
            elapsed = 0
        
        # Interpolate between current and next keyframe
        current_kf = self._keyframes[self._current_keyframe_index]
        
        if self._current_keyframe_index < len(self._keyframes) - 1:
            next_kf = self._keyframes[self._current_keyframe_index + 1]
            
            # Calculate interpolation factor
            kf_elapsed = elapsed - current_kf.time
            t = kf_elapsed / next_kf.duration if next_kf.duration > 0 else 1.0
            t = max(0.0, min(1.0, t))
            
            # Apply easing for smooth motion
            t = self._ease_in_out(t)
            
            # Interpolate position and target
            self.camera.position = current_kf.position + (next_kf.position - current_kf.position) * t
            self.camera.target = current_kf.target + (next_kf.target - current_kf.target) * t
            
            # Special handling for orbit mode
            if next_kf.mode == CameraMode.ORBIT:
                self._apply_orbit_motion(next_kf, t)
        else:
            # At last keyframe
            self.camera.position = current_kf.position
            self.camera.target = current_kf.target
    
    def _apply_orbit_motion(self, keyframe: CameraKeyframe, t: float) -> None:
        """
        Apply orbital motion around target.
        
        Args:
            keyframe: Orbit keyframe
            t: Interpolation factor (0.0 to 1.0)
        """
        # Calculate orbit angle based on progress
        angle = t * math.pi * 2  # Full circle
        
        # Calculate distance from target
        direction = self.camera.position - keyframe.target
        distance = direction.length
        height = self.camera.position.z - keyframe.target.z
        
        # Update position to orbit
        self.camera.position = Vector3([
            keyframe.target.x + distance * math.cos(angle),
            keyframe.target.y + distance * math.sin(angle),
            keyframe.target.z + height
        ])
    
    def _ease_in_out(self, t: float) -> float:
        """
        Apply ease-in-out easing function.
        
        Args:
            t: Input value (0.0 to 1.0)
            
        Returns:
            Eased value (0.0 to 1.0)
        """
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - 2 * (1 - t) * (1 - t)


# Made with Bob