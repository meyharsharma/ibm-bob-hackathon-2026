"""Unit tests for city renderer."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from src.time_machine.city.city_generator import CityState, Building, LayoutConfig
from src.time_machine.rendering.city_renderer import (
    CityRenderer,
    Camera,
    VisualEncoding,
    BuildingMesh
)

try:
    from pyrr import Vector3, Matrix44
    PYRR_AVAILABLE = True
except ImportError:
    PYRR_AVAILABLE = False


class TestCamera:
    """Test Camera class."""
    
    @pytest.mark.skipif(not PYRR_AVAILABLE, reason="pyrr not installed")
    def test_camera_initialization(self):
        """Test camera initialization."""
        camera = Camera(
            position=Vector3([10.0, 10.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )
        
        assert camera.position[0] == 10.0
        assert camera.target[0] == 0.0
        assert camera.fov == 60.0
    
    @pytest.mark.skipif(not PYRR_AVAILABLE, reason="pyrr not installed")
    def test_camera_get_view_matrix(self):
        """Test view matrix generation."""
        camera = Camera(
            position=Vector3([10.0, 10.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )
        
        view_matrix = camera.get_view_matrix()
        assert view_matrix is not None
        assert view_matrix.shape == (4, 4)
    
    @pytest.mark.skipif(not PYRR_AVAILABLE, reason="pyrr not installed")
    def test_camera_get_projection_matrix(self):
        """Test projection matrix generation."""
        camera = Camera(
            position=Vector3([10.0, 10.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )
        
        projection_matrix = camera.get_projection_matrix(16/9)
        assert projection_matrix is not None
        assert projection_matrix.shape == (4, 4)
    
    @pytest.mark.skipif(not PYRR_AVAILABLE, reason="pyrr not installed")
    def test_camera_zoom(self):
        """Test camera zoom."""
        camera = Camera(
            position=Vector3([10.0, 10.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )
        
        initial_distance = (camera.position - camera.target).length
        camera.zoom(5.0)
        new_distance = (camera.position - camera.target).length
        
        assert new_distance < initial_distance


class TestVisualEncoding:
    """Test VisualEncoding class."""
    
    def test_visual_encoding_initialization(self):
        """Test visual encoding initialization."""
        encoding = VisualEncoding()
        
        assert encoding.min_height == 1.0
        assert encoding.max_height == 50.0
        assert encoding.cold_color == (0.2, 0.4, 0.8)
        assert encoding.hot_color == (0.9, 0.2, 0.1)
    
    def test_encode_height(self):
        """Test height encoding."""
        encoding = VisualEncoding()
        
        # Test zero lines
        height = encoding.encode_height(0)
        assert height == encoding.min_height
        
        # Test small file
        height = encoding.encode_height(10)
        assert encoding.min_height <= height <= encoding.max_height
        
        # Test large file
        height = encoding.encode_height(10000)
        assert encoding.min_height <= height <= encoding.max_height
    
    def test_encode_color(self):
        """Test color encoding."""
        encoding = VisualEncoding()
        
        # Test low activity (should be blue-ish)
        color = encoding.encode_color(0)
        assert len(color) == 3
        assert all(0.0 <= c <= 1.0 for c in color)
        assert color[2] > color[0]  # More blue than red
        
        # Test high activity (should be red-ish)
        color = encoding.encode_color(100)
        assert len(color) == 3
        assert all(0.0 <= c <= 1.0 for c in color)
        assert color[0] > color[2]  # More red than blue
    
    def test_encode_weathering(self):
        """Test weathering encoding."""
        encoding = VisualEncoding()
        
        # Test fresh file
        brightness = encoding.encode_weathering(0.0)
        assert brightness == encoding.fresh_brightness
        
        # Test old file
        brightness = encoding.encode_weathering(1.0)
        assert brightness == encoding.aged_brightness
        
        # Test middle age
        brightness = encoding.encode_weathering(0.5)
        assert encoding.aged_brightness < brightness < encoding.fresh_brightness
    
    def test_get_legend(self):
        """Test legend generation."""
        encoding = VisualEncoding()
        legend = encoding.get_legend()
        
        assert 'height' in legend
        assert 'color' in legend
        assert 'brightness' in legend
        assert 'property' in legend['height']
        assert 'encoding' in legend['height']


class TestBuildingMesh:
    """Test BuildingMesh class."""
    
    def test_create_cube_vertices(self):
        """Test cube vertex generation."""
        vertices = BuildingMesh.create_cube_vertices(
            position=(0.0, 0.0, 0.0),
            size=(2.0, 2.0, 2.0)
        )
        
        # Should have 36 vertices (6 faces * 2 triangles * 3 vertices)
        assert vertices.shape == (36, 3)
        assert vertices.dtype == np.float32
    
    def test_create_cube_normals(self):
        """Test cube normal generation."""
        normals = BuildingMesh.create_cube_normals()
        
        # Should have 36 normals
        assert normals.shape == (36, 3)
        assert normals.dtype == np.float32
        
        # All normals should be unit vectors (or close to it)
        for normal in normals:
            length = np.linalg.norm(normal)
            assert abs(length - 1.0) < 0.01 or length == 0.0
    
    def test_create_cube_colors(self):
        """Test cube color generation."""
        colors = BuildingMesh.create_cube_colors(
            color=(1.0, 0.5, 0.0),
            brightness=0.8
        )
        
        # Should have 36 colors
        assert colors.shape == (36, 3)
        assert colors.dtype == np.float32
        
        # All colors should be within valid range
        assert np.all(colors >= 0.0)
        assert np.all(colors <= 1.0)
    
    def test_cube_vertices_centered(self):
        """Test that cube vertices are centered at position."""
        position = (5.0, 10.0, 15.0)
        size = (2.0, 2.0, 2.0)
        vertices = BuildingMesh.create_cube_vertices(position, size)
        
        # Calculate centroid
        centroid = np.mean(vertices, axis=0)
        
        # Centroid should be close to position (z is at base, not center)
        assert abs(centroid[0] - position[0]) < 0.01
        assert abs(centroid[1] - position[1]) < 0.01


class TestCityRenderer:
    """Test CityRenderer class."""
    
    def test_renderer_initialization(self):
        """Test renderer initialization."""
        renderer = CityRenderer(width=1920, height=1080)
        
        assert renderer.width == 1920
        assert renderer.height == 1080
        assert renderer.visual_encoding is not None
        assert renderer.camera is not None
        assert renderer.ctx is None  # Not initialized yet
    
    def test_renderer_with_custom_encoding(self):
        """Test renderer with custom visual encoding."""
        encoding = VisualEncoding(
            min_height=2.0,
            max_height=100.0
        )
        renderer = CityRenderer(visual_encoding=encoding)
        
        assert renderer.visual_encoding.min_height == 2.0
        assert renderer.visual_encoding.max_height == 100.0
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_initialize_context(self, mock_moderngl):
        """Test context initialization."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        assert renderer.ctx is not None
        mock_ctx.enable.assert_called_once()
        mock_ctx.program.assert_called_once()
    
    def test_load_city_state_without_context(self):
        """Test that loading city state without context raises error."""
        renderer = CityRenderer()
        city_state = self._create_test_city_state()
        
        with pytest.raises(RuntimeError, match="Context not initialized"):
            renderer.load_city_state(city_state)
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_load_city_state(self, mock_moderngl):
        """Test loading city state."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        city_state = self._create_test_city_state()
        renderer.load_city_state(city_state)
        
        assert renderer.city_state is not None
        assert len(renderer.building_vaos) > 0
    
    def test_get_visual_legend(self):
        """Test getting visual legend."""
        renderer = CityRenderer()
        legend = renderer.get_visual_legend()
        
        assert 'height' in legend
        assert 'color' in legend
        assert 'brightness' in legend
    
    def test_get_city_statistics_without_state(self):
        """Test getting statistics without loaded state."""
        renderer = CityRenderer()
        stats = renderer.get_city_statistics()
        
        assert stats == {}
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_get_city_statistics(self, mock_moderngl):
        """Test getting city statistics."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        city_state = self._create_test_city_state()
        renderer.load_city_state(city_state)
        
        stats = renderer.get_city_statistics()
        
        assert 'total_buildings' in stats
        assert 'total_neighborhoods' in stats
        assert 'commit_sha' in stats
        assert stats['total_buildings'] == 2
    
    def test_render_without_context(self):
        """Test that rendering without context raises error."""
        renderer = CityRenderer()
        
        with pytest.raises(RuntimeError, match="Context not initialized"):
            renderer.render()
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_render_without_state(self, mock_moderngl):
        """Test that rendering without state raises error."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        with pytest.raises(RuntimeError, match="City state not loaded"):
            renderer.render()
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_calculate_age_factors(self, mock_moderngl):
        """Test age factor calculation."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        city_state = self._create_test_city_state()
        renderer.load_city_state(city_state)
        
        age_factors = renderer._calculate_age_factors()
        
        assert len(age_factors) == 2
        assert all(0.0 <= factor <= 1.0 for factor in age_factors.values())
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_auto_position_camera(self, mock_moderngl):
        """Test automatic camera positioning."""
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        renderer = CityRenderer()
        renderer.initialize_context()
        
        city_state = self._create_test_city_state()
        renderer.load_city_state(city_state)
        
        # Camera should be positioned to view the city
        assert renderer.camera.position is not None
        assert renderer.camera.target is not None
    
    def _create_test_city_state(self) -> CityState:
        """Create a test city state."""
        buildings = {
            'src/main.py': Building(
                file_path='src/main.py',
                position=(0.0, 0.0, 0.0),
                height=10.0,
                base_size=(1.5, 1.5),
                color=(255, 128, 0),
                neighborhood='src',
                created_at='abc123',
                last_modified='def456',
                modification_count=5,
                lines_of_code=100
            ),
            'src/utils.py': Building(
                file_path='src/utils.py',
                position=(3.0, 0.0, 0.0),
                height=5.0,
                base_size=(1.5, 1.5),
                color=(128, 128, 255),
                neighborhood='src',
                created_at='abc123',
                last_modified='ghi789',
                modification_count=2,
                lines_of_code=50
            )
        }
        
        neighborhoods = {
            'src': {
                'name': 'src',
                'position': (0, 0),
                'building_count': 2,
                'total_lines': 150
            }
        }
        
        return CityState(
            commit_sha='test123',
            timestamp=datetime.now(),
            buildings=buildings,
            neighborhoods=neighborhoods,
            layout_config=LayoutConfig(),
            statistics={
                'total_buildings': 2,
                'total_neighborhoods': 1,
                'total_lines_of_code': 150
            }
        )


class TestIntegration:
    """Integration tests for rendering system."""
    
    @patch('src.time_machine.rendering.city_renderer.moderngl')
    def test_full_rendering_pipeline(self, mock_moderngl):
        """Test complete rendering pipeline."""
        # Setup mock context
        mock_ctx = MagicMock()
        mock_moderngl.create_standalone_context.return_value = mock_ctx
        
        # Create renderer
        renderer = CityRenderer(width=800, height=600)
        
        # Initialize context
        renderer.initialize_context()
        assert renderer.ctx is not None
        
        # Create test city state
        city_state = self._create_complex_city_state()
        
        # Load city state
        renderer.load_city_state(city_state)
        assert len(renderer.building_vaos) == 3
        assert len(renderer.neighborhood_boundaries) == 2
        
        # Get statistics
        stats = renderer.get_city_statistics()
        assert stats['total_buildings'] == 3
        assert stats['total_neighborhoods'] == 2
        
        # Get legend
        legend = renderer.get_visual_legend()
        assert 'height' in legend
        assert 'color' in legend
        assert 'brightness' in legend
    
    def _create_complex_city_state(self) -> CityState:
        """Create a more complex test city state."""
        buildings = {
            'src/main.py': Building(
                file_path='src/main.py',
                position=(0.0, 0.0, 0.0),
                height=15.0,
                base_size=(1.5, 1.5),
                color=(255, 100, 50),
                neighborhood='src',
                created_at='abc123',
                last_modified='def456',
                modification_count=10,
                lines_of_code=200
            ),
            'src/utils.py': Building(
                file_path='src/utils.py',
                position=(3.0, 0.0, 0.0),
                height=8.0,
                base_size=(1.5, 1.5),
                color=(150, 150, 200),
                neighborhood='src',
                created_at='abc123',
                last_modified='ghi789',
                modification_count=3,
                lines_of_code=80
            ),
            'tests/test_main.py': Building(
                file_path='tests/test_main.py',
                position=(10.0, 0.0, 0.0),
                height=12.0,
                base_size=(1.5, 1.5),
                color=(200, 120, 100),
                neighborhood='tests',
                created_at='jkl012',
                last_modified='mno345',
                modification_count=7,
                lines_of_code=150
            )
        }
        
        neighborhoods = {
            'src': {
                'name': 'src',
                'position': (0, 0),
                'building_count': 2,
                'total_lines': 280
            },
            'tests': {
                'name': 'tests',
                'position': (10, 0),
                'building_count': 1,
                'total_lines': 150
            }
        }
        
        return CityState(
            commit_sha='test456',
            timestamp=datetime.now(),
            buildings=buildings,
            neighborhoods=neighborhoods,
            layout_config=LayoutConfig(),
            statistics={
                'total_buildings': 3,
                'total_neighborhoods': 2,
                'total_lines_of_code': 430
            }
        )


# Made with Bob