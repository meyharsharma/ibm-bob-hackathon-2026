"""City renderer - 3D visualization of code city using ModernGL."""

import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

try:
    import moderngl
    import moderngl_window as mglw
    from moderngl_window import geometry
    from pyrr import Matrix44, Vector3
except ImportError as e:
    raise ImportError(
        "ModernGL dependencies not installed. "
        "Install with: pip install moderngl moderngl-window pyrr"
    ) from e

from ..city.city_generator import CityState, Building
from ..utils.logger import setup_logger
from ..utils.config import Config


@dataclass
class Camera:
    """
    Camera for viewing the 3D city.
    
    Attributes:
        position: Camera position in 3D space (x, y, z)
        target: Point the camera is looking at (x, y, z)
        up: Up vector for camera orientation
        fov: Field of view in degrees
        near: Near clipping plane
        far: Far clipping plane
    """
    position: Vector3
    target: Vector3
    up: Optional[Vector3] = None
    fov: float = 60.0
    near: float = 0.1
    far: float = 1000.0
    
    def __post_init__(self):
        """Initialize default up vector if not provided."""
        if self.up is None:
            self.up = Vector3([0.0, 0.0, 1.0])
    
    def get_view_matrix(self) -> Matrix44:
        """Get view matrix for camera."""
        return Matrix44.look_at(
            self.position,
            self.target,
            self.up
        )
    
    def get_projection_matrix(self, aspect_ratio: float) -> Matrix44:
        """Get projection matrix for camera."""
        return Matrix44.perspective_projection(
            self.fov,
            aspect_ratio,
            self.near,
            self.far
        )
    
    def orbit(self, delta_azimuth: float, delta_elevation: float) -> None:
        """
        Orbit camera around target.
        
        Args:
            delta_azimuth: Change in azimuth angle (degrees)
            delta_elevation: Change in elevation angle (degrees)
        """
        # Calculate current spherical coordinates
        direction = self.position - self.target
        radius = direction.length
        
        # Convert to spherical coordinates
        azimuth = math.atan2(direction.y, direction.x)
        elevation = math.asin(direction.z / radius)
        
        # Apply deltas
        azimuth += math.radians(delta_azimuth)
        elevation += math.radians(delta_elevation)
        
        # Clamp elevation to avoid gimbal lock
        elevation = max(-math.pi/2 + 0.1, min(math.pi/2 - 0.1, elevation))
        
        # Convert back to cartesian
        self.position = Vector3([
            self.target.x + radius * math.cos(elevation) * math.cos(azimuth),
            self.target.y + radius * math.cos(elevation) * math.sin(azimuth),
            self.target.z + radius * math.sin(elevation)
        ])
    
    def zoom(self, delta: float) -> None:
        """
        Zoom camera in/out.
        
        Args:
            delta: Zoom amount (positive = zoom in, negative = zoom out)
        """
        direction = self.target - self.position
        distance = direction.length
        
        # Calculate new distance
        new_distance = max(1.0, distance - delta)
        
        # Update position
        direction = direction.normalised
        self.position = self.target - direction * new_distance
    
    def pan(self, delta_x: float, delta_y: float) -> None:
        """
        Pan camera (move target and position together).
        
        Args:
            delta_x: Pan amount in x direction
            delta_y: Pan amount in y direction
        """
        # Calculate right and up vectors
        forward = (self.target - self.position).normalised
        right = forward.cross(self.up).normalised
        up = right.cross(forward).normalised
        
        # Apply pan
        offset = right * delta_x + up * delta_y
        self.position += offset
        self.target += offset


@dataclass
class VisualEncoding:
    """
    Visual encoding system for mapping file properties to visual attributes.
    
    This class defines how file properties are encoded visually:
    - Height: File complexity (lines of code)
    - Color: File activity (modification count)
    - Weathering: Time since last modification
    """
    
    # Height encoding
    min_height: float = 1.0
    max_height: float = 50.0
    height_scale: float = 5.0  # Logarithmic scale factor
    
    # Color encoding (activity-based)
    cold_color: Tuple[float, float, float] = (0.2, 0.4, 0.8)  # Blue (low activity)
    hot_color: Tuple[float, float, float] = (0.9, 0.2, 0.1)   # Red (high activity)
    
    # Weathering encoding (age-based)
    fresh_brightness: float = 1.0
    aged_brightness: float = 0.5
    
    def encode_height(self, lines_of_code: int) -> float:
        """
        Encode lines of code as building height.
        
        Uses logarithmic scaling to prevent extreme heights.
        
        Args:
            lines_of_code: Number of lines in file
            
        Returns:
            Building height
        """
        if lines_of_code <= 0:
            return self.min_height
        
        height = math.log(lines_of_code + 1) * self.height_scale
        return max(self.min_height, min(self.max_height, height))
    
    def encode_color(self, modification_count: int) -> Tuple[float, float, float]:
        """
        Encode modification count as color.
        
        More modifications = warmer colors (red/orange)
        Fewer modifications = cooler colors (blue)
        
        Args:
            modification_count: Number of times file was modified
            
        Returns:
            RGB color tuple (0.0-1.0)
        """
        # Normalize using logarithmic scale
        normalized = min(1.0, math.log(modification_count + 1) / 5.0)
        
        # Interpolate between cold and hot colors
        r = self.cold_color[0] + (self.hot_color[0] - self.cold_color[0]) * normalized
        g = self.cold_color[1] + (self.hot_color[1] - self.cold_color[1]) * normalized
        b = self.cold_color[2] + (self.hot_color[2] - self.cold_color[2]) * normalized
        
        return (r, g, b)
    
    def encode_weathering(self, age_factor: float) -> float:
        """
        Encode file age as brightness/weathering.
        
        Newer files are brighter, older files are darker/weathered.
        
        Args:
            age_factor: Age factor (0.0 = newest, 1.0 = oldest)
            
        Returns:
            Brightness multiplier (0.0-1.0)
        """
        return self.fresh_brightness - (self.fresh_brightness - self.aged_brightness) * age_factor
    
    def get_legend(self) -> Dict[str, Any]:
        """
        Get visual encoding legend for display.
        
        Returns:
            Dictionary describing the encoding system
        """
        return {
            'height': {
                'property': 'Lines of Code',
                'encoding': 'Logarithmic scale',
                'range': f'{self.min_height:.1f} - {self.max_height:.1f} units',
                'description': 'Taller buildings = more complex files'
            },
            'color': {
                'property': 'Modification Count',
                'encoding': 'Temperature scale',
                'cold': f'RGB{tuple(int(c*255) for c in self.cold_color)} (low activity)',
                'hot': f'RGB{tuple(int(c*255) for c in self.hot_color)} (high activity)',
                'description': 'Warmer colors = more frequently modified'
            },
            'brightness': {
                'property': 'Time Since Last Modification',
                'encoding': 'Brightness/weathering',
                'range': f'{self.aged_brightness:.1f} - {self.fresh_brightness:.1f}',
                'description': 'Darker buildings = older/less recently modified'
            }
        }


class BuildingMesh:
    """
    Generates and manages 3D mesh data for buildings.
    
    Creates cube/box meshes with proper vertices, normals, and colors.
    """
    
    @staticmethod
    def create_cube_vertices(
        position: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ) -> np.ndarray:
        """
        Create vertices for a cube mesh.
        
        Args:
            position: Center position (x, y, z)
            size: Size (width, depth, height)
            
        Returns:
            Numpy array of vertices (36 vertices for 6 faces, 2 triangles each)
        """
        x, y, z = position
        w, d, h = size
        
        # Half dimensions
        hw, hd, hh = w/2, d/2, h/2
        
        # Define 8 corners of the cube
        corners = np.array([
            [x - hw, y - hd, z],      # 0: bottom-left-front
            [x + hw, y - hd, z],      # 1: bottom-right-front
            [x + hw, y + hd, z],      # 2: bottom-right-back
            [x - hw, y + hd, z],      # 3: bottom-left-back
            [x - hw, y - hd, z + h],  # 4: top-left-front
            [x + hw, y - hd, z + h],  # 5: top-right-front
            [x + hw, y + hd, z + h],  # 6: top-right-back
            [x - hw, y + hd, z + h],  # 7: top-left-back
        ])
        
        # Define faces (2 triangles per face)
        faces = np.array([
            # Front face
            [0, 1, 5], [0, 5, 4],
            # Back face
            [2, 3, 7], [2, 7, 6],
            # Left face
            [3, 0, 4], [3, 4, 7],
            # Right face
            [1, 2, 6], [1, 6, 5],
            # Top face
            [4, 5, 6], [4, 6, 7],
            # Bottom face
            [3, 2, 1], [3, 1, 0],
        ])
        
        # Create vertex array from faces
        vertices = corners[faces.flatten()]
        
        return vertices.astype('f4')
    
    @staticmethod
    def create_cube_normals() -> np.ndarray:
        """
        Create normal vectors for cube faces.
        
        Returns:
            Numpy array of normals (36 normals, one per vertex)
        """
        # Define normals for each face (2 triangles per face)
        normals = np.array([
            # Front face (facing -Y)
            [0, -1, 0], [0, -1, 0], [0, -1, 0],
            [0, -1, 0], [0, -1, 0], [0, -1, 0],
            # Back face (facing +Y)
            [0, 1, 0], [0, 1, 0], [0, 1, 0],
            [0, 1, 0], [0, 1, 0], [0, 1, 0],
            # Left face (facing -X)
            [-1, 0, 0], [-1, 0, 0], [-1, 0, 0],
            [-1, 0, 0], [-1, 0, 0], [-1, 0, 0],
            # Right face (facing +X)
            [1, 0, 0], [1, 0, 0], [1, 0, 0],
            [1, 0, 0], [1, 0, 0], [1, 0, 0],
            # Top face (facing +Z)
            [0, 0, 1], [0, 0, 1], [0, 0, 1],
            [0, 0, 1], [0, 0, 1], [0, 0, 1],
            # Bottom face (facing -Z)
            [0, 0, -1], [0, 0, -1], [0, 0, -1],
            [0, 0, -1], [0, 0, -1], [0, 0, -1],
        ])
        
        return normals.astype('f4')
    
    @staticmethod
    def create_cube_colors(
        color: Tuple[float, float, float],
        brightness: float = 1.0
    ) -> np.ndarray:
        """
        Create color data for cube vertices.
        
        Args:
            color: Base RGB color (0.0-1.0)
            brightness: Brightness multiplier (0.0-1.0)
            
        Returns:
            Numpy array of colors (36 colors, one per vertex)
        """
        # Apply brightness to color
        r, g, b = color
        r, g, b = r * brightness, g * brightness, b * brightness
        
        # Repeat color for all 36 vertices
        colors = np.tile([r, g, b], (36, 1))
        
        return colors.astype('f4')


class CityRenderer:
    """
    Renders 3D city visualization using ModernGL.
    
    This class handles:
    - 3D rendering of buildings as cubes
    - Visual encoding of file properties (height, color, weathering)
    - Neighborhood clustering and visualization
    - Camera controls for viewing the city
    - Interactive rendering with ModernGL
    
    The renderer uses a scene graph approach where each building is a
    separate mesh with its own transformation and visual properties.
    
    Architecture:
    - Uses ModernGL for GPU-accelerated rendering
    - Implements Phong shading for realistic lighting
    - Supports camera controls (orbit, zoom, pan)
    - Renders neighborhood boundaries for visual separation
    - Provides visual encoding legend
    
    Example:
        ```python
        renderer = CityRenderer(width=1920, height=1080)
        renderer.load_city_state(city_state)
        renderer.render()
        ```
    """
    
    # Vertex shader for building rendering
    VERTEX_SHADER = """
    #version 330
    
    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;
    
    in vec3 in_position;
    in vec3 in_normal;
    in vec3 in_color;
    
    out vec3 v_position;
    out vec3 v_normal;
    out vec3 v_color;
    
    void main() {
        vec4 world_position = model * vec4(in_position, 1.0);
        v_position = world_position.xyz;
        v_normal = mat3(model) * in_normal;
        v_color = in_color;
        gl_Position = projection * view * world_position;
    }
    """
    
    # Fragment shader with Phong lighting
    FRAGMENT_SHADER = """
    #version 330
    
    uniform vec3 light_position;
    uniform vec3 light_color;
    uniform vec3 camera_position;
    
    in vec3 v_position;
    in vec3 v_normal;
    in vec3 v_color;
    
    out vec4 f_color;
    
    void main() {
        // Ambient lighting
        float ambient_strength = 0.3;
        vec3 ambient = ambient_strength * light_color;
        
        // Diffuse lighting
        vec3 norm = normalize(v_normal);
        vec3 light_dir = normalize(light_position - v_position);
        float diff = max(dot(norm, light_dir), 0.0);
        vec3 diffuse = diff * light_color;
        
        // Specular lighting
        float specular_strength = 0.5;
        vec3 view_dir = normalize(camera_position - v_position);
        vec3 reflect_dir = reflect(-light_dir, norm);
        float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 32);
        vec3 specular = specular_strength * spec * light_color;
        
        // Combine lighting
        vec3 result = (ambient + diffuse + specular) * v_color;
        f_color = vec4(result, 1.0);
    }
    """
    
    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        visual_encoding: Optional[VisualEncoding] = None
    ):
        """
        Initialize the city renderer.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels
            visual_encoding: Visual encoding system (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.width = width
        self.height = height
        self.visual_encoding = visual_encoding or VisualEncoding()
        
        # ModernGL context (will be initialized when needed)
        self.ctx: Optional[moderngl.Context] = None
        self.prog: Optional[moderngl.Program] = None
        
        # Camera setup
        self.camera = Camera(
            position=Vector3([50.0, 50.0, 50.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )
        
        # City state
        self.city_state: Optional[CityState] = None
        
        # Rendering data
        self.building_vaos: Dict[str, moderngl.VertexArray] = {}
        self.neighborhood_boundaries: Dict[str, moderngl.VertexArray] = {}
        
        # Light setup
        self.light_position = Vector3([100.0, 100.0, 100.0])
        self.light_color = Vector3([1.0, 1.0, 1.0])
        
        self.logger.info(
            f"Initialized CityRenderer ({width}x{height})"
        )
    
    def initialize_context(self, ctx: Optional[moderngl.Context] = None) -> None:
        """
        Initialize ModernGL context and shaders.
        
        Args:
            ctx: Existing ModernGL context (creates standalone if None)
        """
        if ctx is None:
            self.ctx = moderngl.create_standalone_context()
        else:
            self.ctx = ctx
        
        # Enable depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)
        
        # Compile shaders
        self.prog = self.ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER
        )
        
        self.logger.info("ModernGL context initialized")
    
    def load_city_state(self, city_state: CityState) -> None:
        """
        Load city state for rendering.
        
        This method processes the city state and creates GPU buffers
        for all buildings and neighborhood boundaries.
        
        Args:
            city_state: CityState object to render
            
        Raises:
            RuntimeError: If context not initialized
        """
        if self.ctx is None:
            raise RuntimeError("Context not initialized. Call initialize_context() first.")
        
        self.logger.info(
            f"Loading city state: {len(city_state.buildings)} buildings, "
            f"{len(city_state.neighborhoods)} neighborhoods"
        )
        
        self.city_state = city_state
        
        # Clear existing data
        self.building_vaos.clear()
        self.neighborhood_boundaries.clear()
        
        # Create building meshes
        self._create_building_meshes()
        
        # Create neighborhood boundaries
        self._create_neighborhood_boundaries()
        
        # Calculate camera position to view entire city
        self._auto_position_camera()
        
        self.logger.info("City state loaded successfully")
    
    def _create_building_meshes(self) -> None:
        """Create GPU buffers for all building meshes."""
        if not self.city_state:
            return
        
        # Calculate age factors for weathering
        age_factors = self._calculate_age_factors()
        
        for file_path, building in self.city_state.buildings.items():
            # Create mesh data
            vertices = BuildingMesh.create_cube_vertices(
                building.position,
                (building.base_size[0], building.base_size[1], building.height)
            )
            normals = BuildingMesh.create_cube_normals()
            
            # Apply visual encoding
            color = self.visual_encoding.encode_color(building.modification_count)
            age_factor = age_factors.get(file_path, 0.0)
            brightness = self.visual_encoding.encode_weathering(age_factor)
            colors = BuildingMesh.create_cube_colors(color, brightness)
            
            # Create vertex buffer
            vbo = self.ctx.buffer(
                np.concatenate([vertices, normals, colors], axis=1).tobytes()
            )
            
            # Create vertex array object
            vao = self.ctx.vertex_array(
                self.prog,
                [
                    (vbo, '3f 3f 3f', 'in_position', 'in_normal', 'in_color')
                ]
            )
            
            self.building_vaos[file_path] = vao
        
        self.logger.info(f"Created {len(self.building_vaos)} building meshes")
    
    def _calculate_age_factors(self) -> Dict[str, float]:
        """
        Calculate age factors for all buildings (0.0 = newest, 1.0 = oldest).
        
        Returns:
            Dictionary mapping file paths to age factors
        """
        if not self.city_state:
            return {}
        
        # Find oldest and newest modification times
        # For simplicity, use modification count as proxy for age
        # (more modifications = more recent activity)
        mod_counts = [
            b.modification_count for b in self.city_state.buildings.values()
        ]
        
        if not mod_counts:
            return {}
        
        max_mods = max(mod_counts)
        
        # Calculate age factors (inverse of modification activity)
        age_factors = {}
        for file_path, building in self.city_state.buildings.items():
            if max_mods > 0:
                # Invert: high modification count = low age factor (fresh)
                age_factors[file_path] = 1.0 - (building.modification_count / max_mods)
            else:
                age_factors[file_path] = 0.5  # Default middle age
        
        return age_factors
    
    def _create_neighborhood_boundaries(self) -> None:
        """Create visual boundaries for neighborhoods."""
        if not self.city_state:
            return
        
        for neighborhood_path, metadata in self.city_state.neighborhoods.items():
            position = metadata.get('position', (0, 0))
            
            # Create boundary box (ground plane rectangle)
            x, y = position
            size = self.city_state.layout_config.grid_size
            
            # Define boundary vertices (line loop)
            vertices = np.array([
                [x, y, 0],
                [x + size, y, 0],
                [x + size, y + size, 0],
                [x, y + size, 0],
                [x, y, 0],  # Close the loop
            ], dtype='f4')
            
            # Create vertex buffer
            vbo = self.ctx.buffer(vertices.tobytes())
            
            # Create simple program for lines (if not already created)
            if not hasattr(self, 'line_prog'):
                self.line_prog = self.ctx.program(
                    vertex_shader="""
                    #version 330
                    uniform mat4 mvp;
                    in vec3 in_position;
                    void main() {
                        gl_Position = mvp * vec4(in_position, 1.0);
                    }
                    """,
                    fragment_shader="""
                    #version 330
                    out vec4 f_color;
                    void main() {
                        f_color = vec4(0.5, 0.5, 0.5, 1.0);
                    }
                    """
                )
            
            # Create vertex array object
            vao = self.ctx.vertex_array(
                self.line_prog,
                [(vbo, '3f', 'in_position')]
            )
            
            self.neighborhood_boundaries[neighborhood_path] = vao
        
        self.logger.info(
            f"Created {len(self.neighborhood_boundaries)} neighborhood boundaries"
        )
    
    def _auto_position_camera(self) -> None:
        """Automatically position camera to view entire city."""
        if not self.city_state or not self.city_state.buildings:
            return
        
        # Calculate bounding box of all buildings
        positions = [b.position for b in self.city_state.buildings.values()]
        
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] for p in positions)
        max_z = max(b.height for b in self.city_state.buildings.values())
        
        # Calculate center and size
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = max_z / 2
        
        size_x = max_x - min_x
        size_y = max_y - min_y
        max_size = max(size_x, size_y, max_z)
        
        # Position camera to view entire city
        distance = max_size * 2.0
        self.camera.target = Vector3([center_x, center_y, center_z])
        self.camera.position = Vector3([
            center_x + distance * 0.7,
            center_y + distance * 0.7,
            center_z + distance * 0.5
        ])
        
        self.logger.info(
            f"Camera positioned at {self.camera.position}, "
            f"looking at {self.camera.target}"
        )
    
    def render(self, clear_color: Tuple[float, float, float, float] = (0.1, 0.1, 0.15, 1.0)) -> None:
        """
        Render the city.
        
        Args:
            clear_color: Background color (RGBA, 0.0-1.0)
            
        Raises:
            RuntimeError: If context not initialized or city state not loaded
        """
        if self.ctx is None:
            raise RuntimeError("Context not initialized")
        
        if self.city_state is None:
            raise RuntimeError("City state not loaded")
        
        # Clear buffers
        self.ctx.clear(*clear_color)
        
        # Calculate matrices
        view_matrix = self.camera.get_view_matrix()
        projection_matrix = self.camera.get_projection_matrix(
            self.width / self.height
        )
        
        # Set uniforms
        self.prog['view'].write(view_matrix.astype('f4').tobytes())
        self.prog['projection'].write(projection_matrix.astype('f4').tobytes())
        self.prog['light_position'].write(self.light_position.astype('f4').tobytes())
        self.prog['light_color'].write(self.light_color.astype('f4').tobytes())
        self.prog['camera_position'].write(self.camera.position.astype('f4').tobytes())
        
        # Render buildings
        identity = Matrix44.identity()
        self.prog['model'].write(identity.astype('f4').tobytes())
        
        for vao in self.building_vaos.values():
            vao.render(moderngl.TRIANGLES)
        
        # Render neighborhood boundaries
        if hasattr(self, 'line_prog'):
            mvp = projection_matrix * view_matrix
            self.line_prog['mvp'].write(mvp.astype('f4').tobytes())
            
            for vao in self.neighborhood_boundaries.values():
                vao.render(moderngl.LINE_STRIP)
    
    def get_visual_legend(self) -> Dict[str, Any]:
        """
        Get visual encoding legend.
        
        Returns:
            Dictionary describing the visual encoding system
        """
        return self.visual_encoding.get_legend()
    
    def get_city_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the rendered city.
        
        Returns:
            Dictionary with city statistics
        """
        if not self.city_state:
            return {}
        
        return {
            'total_buildings': len(self.city_state.buildings),
            'total_neighborhoods': len(self.city_state.neighborhoods),
            'commit_sha': self.city_state.commit_sha,
            'timestamp': self.city_state.timestamp.isoformat(),
            **self.city_state.statistics
        }
    
    def cleanup(self) -> None:
        """Release GPU resources."""
        for vao in self.building_vaos.values():
            vao.release()
        
        for vao in self.neighborhood_boundaries.values():
            vao.release()
        
        if self.prog:
            self.prog.release()
        
        if hasattr(self, 'line_prog'):
            self.line_prog.release()
        
        self.building_vaos.clear()
        self.neighborhood_boundaries.clear()
        
        self.logger.info("Renderer resources released")


# Made with Bob