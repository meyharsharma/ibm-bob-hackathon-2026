"""Unit tests for TimelineController."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.time_machine.rendering.timeline_controller import (
    TimelineController,
    TimelineState
)
from src.time_machine.ingestion.commit_parser import CommitInfo, FileChange, ChangeType
from src.time_machine.city.city_generator import CityGenerator


class TestTimelineState(unittest.TestCase):
    """Test TimelineState dataclass."""
    
    def test_progress_calculation(self):
        """Test progress property calculation."""
        state = TimelineState(
            current_time=45.0,
            total_duration=90.0
        )
        self.assertAlmostEqual(state.progress, 0.5)
    
    def test_progress_at_start(self):
        """Test progress at start."""
        state = TimelineState(current_time=0.0, total_duration=90.0)
        self.assertEqual(state.progress, 0.0)
    
    def test_progress_at_end(self):
        """Test progress at end."""
        state = TimelineState(current_time=90.0, total_duration=90.0)
        self.assertEqual(state.progress, 1.0)
    
    def test_progress_beyond_end(self):
        """Test progress clamped at 1.0."""
        state = TimelineState(current_time=100.0, total_duration=90.0)
        self.assertEqual(state.progress, 1.0)


class TestTimelineController(unittest.TestCase):
    """Test TimelineController class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock commits
        self.commits = [
            CommitInfo(
                sha=f"commit{i}",
                message=f"Commit {i}",
                author="Test Author",
                author_email="test@example.com",
                timestamp=datetime(2024, 1, i+1),
                files_changed=[]
            )
            for i in range(10)
        ]
        
        self.neighborhoods = {}
        self.city_generator = Mock(spec=CityGenerator)
        
        # Mock city state
        mock_city_state = Mock()
        mock_city_state.commit_sha = "commit0"
        mock_city_state.timestamp = datetime(2024, 1, 1)
        self.city_generator.generate_city_at_commit.return_value = mock_city_state
    
    def test_initialization(self):
        """Test controller initialization."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator,
            duration=90.0
        )
        
        self.assertEqual(len(controller.commits), 10)
        self.assertEqual(controller.state.total_duration, 90.0)
        self.assertFalse(controller.state.is_playing)
    
    def test_initialization_empty_commits_raises_error(self):
        """Test initialization with empty commits raises ValueError."""
        with self.assertRaises(ValueError):
            TimelineController([], self.neighborhoods, self.city_generator)
    
    def test_play(self):
        """Test play functionality."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.play()
        self.assertTrue(controller.state.is_playing)
        self.assertTrue(controller.is_playing())
    
    def test_pause(self):
        """Test pause functionality."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.play()
        controller.pause()
        self.assertFalse(controller.state.is_playing)
        self.assertFalse(controller.is_playing())
    
    def test_stop(self):
        """Test stop functionality."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.play()
        controller.state.current_time = 45.0
        controller.stop()
        
        self.assertFalse(controller.state.is_playing)
        self.assertEqual(controller.state.current_time, 0.0)
        self.assertEqual(controller.state.current_commit_index, 0)
    
    def test_set_duration(self):
        """Test setting duration."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.set_duration(120.0)
        self.assertEqual(controller.state.total_duration, 120.0)
    
    def test_set_duration_invalid_raises_error(self):
        """Test setting invalid duration raises ValueError."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        with self.assertRaises(ValueError):
            controller.set_duration(0.0)
        
        with self.assertRaises(ValueError):
            controller.set_duration(-10.0)
    
    def test_set_speed(self):
        """Test setting playback speed."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.set_speed(2.0)
        self.assertEqual(controller.state.playback_speed, 2.0)
    
    def test_scrub_to_time(self):
        """Test scrubbing to specific time."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator,
            duration=90.0
        )
        
        city_state = controller.scrub_to_time(45.0)
        
        self.assertEqual(controller.state.current_time, 45.0)
        self.assertIsNotNone(city_state)
        # Should be at middle commit (index 4 or 5)
        self.assertIn(controller.state.current_commit_index, [4, 5])
    
    def test_scrub_to_commit(self):
        """Test scrubbing to specific commit."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator,
            duration=90.0
        )
        
        city_state = controller.scrub_to_commit(5)
        
        self.assertEqual(controller.state.current_commit_index, 5)
        self.assertIsNotNone(city_state)
    
    def test_scrub_to_commit_invalid_raises_error(self):
        """Test scrubbing to invalid commit raises ValueError."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        with self.assertRaises(ValueError):
            controller.scrub_to_commit(-1)
        
        with self.assertRaises(ValueError):
            controller.scrub_to_commit(100)
    
    def test_update_advances_time(self):
        """Test update advances time when playing."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.play()
        city_state = controller.update(delta_time=1.0)
        
        self.assertEqual(controller.state.current_time, 1.0)
        self.assertIsNotNone(city_state)
    
    def test_update_respects_speed(self):
        """Test update respects playback speed."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        controller.set_speed(2.0)
        controller.play()
        controller.update(delta_time=1.0)
        
        self.assertEqual(controller.state.current_time, 2.0)
    
    def test_update_stops_at_end(self):
        """Test update stops at end of timeline."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator,
            duration=10.0
        )
        
        controller.play()
        controller.update(delta_time=15.0)
        
        self.assertEqual(controller.state.current_time, 10.0)
        self.assertFalse(controller.state.is_playing)
    
    def test_callbacks_on_commit_change(self):
        """Test commit change callbacks are called."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator,
            duration=10.0
        )
        
        callback = Mock()
        controller.on_commit_change(callback)
        
        controller.scrub_to_commit(5)
        
        callback.assert_called_once()
    
    def test_get_timeline_info(self):
        """Test getting timeline information."""
        controller = TimelineController(
            self.commits,
            self.neighborhoods,
            self.city_generator
        )
        
        info = controller.get_timeline_info()
        
        self.assertEqual(info['total_commits'], 10)
        self.assertEqual(info['current_commit_index'], 0)
        self.assertIn('current_commit_sha', info)
        self.assertIn('progress', info)


if __name__ == '__main__':
    unittest.main()

# Made with Bob
