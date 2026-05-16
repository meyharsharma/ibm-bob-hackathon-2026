"""Unit tests for city generator."""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from src.time_machine.city.city_generator import (
    CityGenerator,
    Building,
    CityState,
    LayoutConfig
)
from src.time_machine.ingestion.commit_parser import (
    CommitInfo,
    FileChange,
    ChangeType
)
from src.time_machine.ingestion.file_grouper import Neighborhood


class TestCityGenerator(unittest.TestCase):
    """Test cases for CityGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = CityGenerator()
        
        # Create sample commits
        self.commits = [
            CommitInfo(
                sha='abc123',
                author='Test Author',
                author_email='test@example.com',
                timestamp=datetime(2024, 1, 1),
                message='Initial commit',
                files_changed=[
                    FileChange(
                        path='src/main.py',
                        change_type=ChangeType.ADDED,
                        lines_added=100
                    ),
                    FileChange(
                        path='src/utils.py',
                        change_type=ChangeType.ADDED,
                        lines_added=50
                    )
                ]
            ),
            CommitInfo(
                sha='def456',
                author='Test Author',
                author_email='test@example.com',
                timestamp=datetime(2024, 1, 2),
                message='Update main',
                files_changed=[
                    FileChange(
                        path='src/main.py',
                        change_type=ChangeType.MODIFIED,
                        lines_added=20,
                        lines_deleted=10
                    )
                ]
            )
        ]
        
        # Create sample neighborhoods
        self.neighborhoods = {
            'src': Neighborhood(
                name='src',
                path='src',
                files={'src/main.py', 'src/utils.py'}
            )
        }
    
    def test_initialization(self):
        """Test CityGenerator initialization."""
        self.assertIsNotNone(self.generator)
        self.assertIsInstance(self.generator.layout_config, LayoutConfig)
        self.assertEqual(self.generator.buildings, {})
    
    def test_generate_city(self):
        """Test basic city generation."""
        city_state = self.generator.generate_city(self.commits, self.neighborhoods)
        
        self.assertIsInstance(city_state, CityState)
        self.assertEqual(city_state.commit_sha, 'def456')
        self.assertEqual(len(city_state.buildings), 2)
        self.assertIn('src/main.py', city_state.buildings)
        self.assertIn('src/utils.py', city_state.buildings)
    
    def test_building_properties(self):
        """Test building property calculation."""
        city_state = self.generator.generate_city(self.commits, self.neighborhoods)
        
        main_building = city_state.buildings['src/main.py']
        self.assertEqual(main_building.file_path, 'src/main.py')
        self.assertEqual(main_building.neighborhood, 'src')
        self.assertEqual(main_building.created_at, 'abc123')
        self.assertEqual(main_building.last_modified, 'def456')
        self.assertEqual(main_building.modification_count, 1)
        self.assertEqual(main_building.lines_of_code, 110)  # 100 + 20 - 10
        
        utils_building = city_state.buildings['src/utils.py']
        self.assertEqual(utils_building.modification_count, 0)
        self.assertEqual(utils_building.lines_of_code, 50)
    
    def test_generate_city_at_commit(self):
        """Test city generation at specific commit."""
        city_state = self.generator.generate_city_at_commit(
            self.commits,
            self.neighborhoods,
            'abc123'
        )
        
        self.assertEqual(city_state.commit_sha, 'abc123')
        self.assertEqual(len(city_state.buildings), 2)
        
        # At first commit, main.py should have 100 lines
        main_building = city_state.buildings['src/main.py']
        self.assertEqual(main_building.lines_of_code, 100)
        self.assertEqual(main_building.modification_count, 0)
    
    def test_empty_commits_raises_error(self):
        """Test that empty commits list raises ValueError."""
        with self.assertRaises(ValueError):
            self.generator.generate_city([], self.neighborhoods)
    
    def test_invalid_commit_sha_raises_error(self):
        """Test that invalid commit SHA raises ValueError."""
        with self.assertRaises(ValueError):
            self.generator.generate_city_at_commit(
                self.commits,
                self.neighborhoods,
                'invalid_sha'
            )
    
    def test_city_state_serialization(self):
        """Test CityState to_dict and from_dict."""
        city_state = self.generator.generate_city(self.commits, self.neighborhoods)
        
        # Convert to dict
        state_dict = city_state.to_dict()
        self.assertIsInstance(state_dict, dict)
        self.assertIn('commit_sha', state_dict)
        self.assertIn('buildings', state_dict)
        
        # Convert back from dict
        restored_state = CityState.from_dict(state_dict)
        self.assertEqual(restored_state.commit_sha, city_state.commit_sha)
        self.assertEqual(len(restored_state.buildings), len(city_state.buildings))
    
    def test_building_serialization(self):
        """Test Building to_dict and from_dict."""
        building = Building(
            file_path='test.py',
            position=(1.0, 2.0, 3.0),
            height=10.0,
            base_size=(1.5, 1.5),
            color=(255, 0, 0),
            neighborhood='src',
            created_at='abc123',
            last_modified='def456',
            modification_count=5,
            lines_of_code=100
        )
        
        # Convert to dict
        building_dict = building.to_dict()
        self.assertIsInstance(building_dict, dict)
        
        # Convert back from dict
        restored_building = Building.from_dict(building_dict)
        self.assertEqual(restored_building.file_path, building.file_path)
        self.assertEqual(restored_building.position, building.position)
        self.assertEqual(restored_building.height, building.height)
    
    def test_layout_config_serialization(self):
        """Test LayoutConfig to_dict and from_dict."""
        config = LayoutConfig(
            grid_size=15.0,
            building_spacing=3.0,
            layout_algorithm='grid'
        )
        
        # Convert to dict
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        
        # Convert back from dict
        restored_config = LayoutConfig.from_dict(config_dict)
        self.assertEqual(restored_config.grid_size, config.grid_size)
        self.assertEqual(restored_config.building_spacing, config.building_spacing)
    
    def test_save_and_load_city_state(self):
        """Test saving and loading city state to/from JSON."""
        city_state = self.generator.generate_city(self.commits, self.neighborhoods)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.generator.save_city_state(city_state, temp_path)
            
            # Verify file exists and is valid JSON
            self.assertTrue(Path(temp_path).exists())
            with open(temp_path, 'r') as f:
                data = json.load(f)
                self.assertIn('commit_sha', data)
            
            # Load back
            loaded_state = self.generator.load_city_state(temp_path)
            self.assertEqual(loaded_state.commit_sha, city_state.commit_sha)
            self.assertEqual(len(loaded_state.buildings), len(city_state.buildings))
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
    
    def test_building_height_calculation(self):
        """Test building height calculation."""
        # Test with different line counts
        height_0 = self.generator._calculate_building_height(0)
        height_10 = self.generator._calculate_building_height(10)
        height_100 = self.generator._calculate_building_height(100)
        height_1000 = self.generator._calculate_building_height(1000)
        
        # Heights should increase with lines
        self.assertLess(height_0, height_10)
        self.assertLess(height_10, height_100)
        self.assertLess(height_100, height_1000)
        
        # Heights should be within bounds
        self.assertGreaterEqual(height_0, self.generator.layout_config.min_building_height)
        self.assertLessEqual(height_1000, self.generator.layout_config.max_building_height)
    
    def test_building_color_calculation(self):
        """Test building color calculation."""
        # Test with different modification counts
        color_0 = self.generator._calculate_building_color(0)
        color_5 = self.generator._calculate_building_color(5)
        color_20 = self.generator._calculate_building_color(20)
        
        # All colors should be valid RGB tuples
        for color in [color_0, color_5, color_20]:
            self.assertEqual(len(color), 3)
            for component in color:
                self.assertGreaterEqual(component, 0)
                self.assertLessEqual(component, 255)
        
        # More modifications should result in more red
        self.assertLess(color_0[0], color_20[0])  # Red component increases


if __name__ == '__main__':
    unittest.main()

# Made with Bob
