"""Unit tests for PlaybackController."""

import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.time_machine.rendering.playback_controller import (
    PlaybackController,
    PlaybackState,
    PlaybackConfig
)
from src.time_machine.rendering.timeline_controller import TimelineController
from src.time_machine.rendering.animation_system import AnimationSystem
from src.time_machine.ingestion.commit_parser import CommitInfo
from src.time_machine.city.city_generator import CityGenerator


class TestPlaybackConfig(unittest.TestCase):
    """Test PlaybackConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = PlaybackConfig()
        
        self.assertEqual(config.min_speed, 0.5)
        self.assertEqual(config.max_speed, 4.0)
        self.assertEqual(config.default_speed, 1.0)


class TestPlaybackController(unittest.TestCase):
    """Test PlaybackController class."""
    
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
        
        # Create mocks
        self.city_generator = Mock(spec=CityGenerator)
        mock_city_state = Mock()
        self.city_generator.generate_city_at_commit.return_value = mock_city_state
        
        self.timeline = TimelineController(
            self.commits,
            {},
            self.city_generator,
            duration=90.0
        )
        
        self.animation_system = Mock(spec=AnimationSystem)
        
        self.controller = PlaybackController(
            self.timeline,
            self.animation_system
        )
    
    def test_initialization(self):
        """Test controller initialization."""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.get_state(), PlaybackState.STOPPED)
    
    def test_play(self):
        """Test play functionality."""
        self.controller.play()
        
        self.assertTrue(self.controller.is_playing())
        self.assertEqual(self.controller.get_state(), PlaybackState.PLAYING)
    
    def test_pause(self):
        """Test pause functionality."""
        self.controller.play()
        self.controller.pause()
        
        self.assertTrue(self.controller.is_paused())
        self.assertEqual(self.controller.get_state(), PlaybackState.PAUSED)
    
    def test_resume(self):
        """Test resume functionality."""
        self.controller.play()
        self.controller.pause()
        self.controller.resume()
        
        self.assertTrue(self.controller.is_playing())
    
    def test_stop(self):
        """Test stop functionality."""
        self.controller.play()
        self.controller.stop()
        
        self.assertTrue(self.controller.is_stopped())
        self.assertEqual(self.timeline.state.current_time, 0.0)
    
    def test_toggle_play_pause(self):
        """Test toggle play/pause."""
        # Start stopped, toggle to play
        self.controller.toggle_play_pause()
        self.assertTrue(self.controller.is_playing())
        
        # Toggle to pause
        self.controller.toggle_play_pause()
        self.assertTrue(self.controller.is_paused())
    
    def test_scrub_to_time(self):
        """Test scrubbing to specific time."""
        city_state = self.controller.scrub_to_time(45.0)
        
        self.assertEqual(self.timeline.state.current_time, 45.0)
        self.assertIsNotNone(city_state)
    
    def test_scrub_to_progress(self):
        """Test scrubbing to progress."""
        city_state = self.controller.scrub_to_progress(0.5)
        
        self.assertAlmostEqual(self.timeline.state.progress, 0.5, places=1)
        self.assertIsNotNone(city_state)
    
    def test_scrub_to_progress_invalid_raises_error(self):
        """Test invalid progress raises ValueError."""
        with self.assertRaises(ValueError):
            self.controller.scrub_to_progress(-0.1)
        
        with self.assertRaises(ValueError):
            self.controller.scrub_to_progress(1.5)
    
    def test_scrub_to_commit(self):
        """Test scrubbing to specific commit."""
        city_state = self.controller.scrub_to_commit(5)
        
        self.assertEqual(self.timeline.state.current_commit_index, 5)
        self.assertIsNotNone(city_state)
    
    def test_step_forward(self):
        """Test stepping forward one commit."""
        initial_index = self.timeline.state.current_commit_index
        self.controller.step_forward()
        
        self.assertEqual(
            self.timeline.state.current_commit_index,
            initial_index + 1
        )
    
    def test_step_backward(self):
        """Test stepping backward one commit."""
        self.controller.scrub_to_commit(5)
        self.controller.step_backward()
        
        self.assertEqual(self.timeline.state.current_commit_index, 4)
    
    def test_set_speed(self):
        """Test setting playback speed."""
        self.controller.set_speed(2.0)
        
        self.assertEqual(self.timeline.state.playback_speed, 2.0)
    
    def test_set_speed_invalid_raises_error(self):
        """Test invalid speed raises ValueError."""
        with self.assertRaises(ValueError):
            self.controller.set_speed(0.1)  # Below min
        
        with self.assertRaises(ValueError):
            self.controller.set_speed(5.0)  # Above max
    
    def test_increase_speed(self):
        """Test increasing speed."""
        initial_speed = self.timeline.state.playback_speed
        new_speed = self.controller.increase_speed()
        
        self.assertGreater(new_speed, initial_speed)
    
    def test_decrease_speed(self):
        """Test decreasing speed."""
        self.controller.set_speed(2.0)
        new_speed = self.controller.decrease_speed()
        
        self.assertLess(new_speed, 2.0)
    
    def test_set_speed_preset(self):
        """Test setting speed presets."""
        self.controller.set_speed_preset('slow')
        self.assertEqual(self.timeline.state.playback_speed, 0.5)
        
        self.controller.set_speed_preset('normal')
        self.assertEqual(self.timeline.state.playback_speed, 1.0)
        
        self.controller.set_speed_preset('fast')
        self.assertEqual(self.timeline.state.playback_speed, 2.0)
    
    def test_set_speed_preset_invalid_raises_error(self):
        """Test invalid preset raises ValueError."""
        with self.assertRaises(ValueError):
            self.controller.set_speed_preset('invalid')
    
    def test_reset_speed(self):
        """Test resetting speed to default."""
        self.controller.set_speed(2.0)
        self.controller.reset_speed()
        
        self.assertEqual(self.timeline.state.playback_speed, 1.0)
    
    def test_update_calls_timeline_and_animation(self):
        """Test update calls both timeline and animation system."""
        self.controller.play()
        self.controller.update(delta_time=1.0)
        
        # Animation system update should be called
        self.animation_system.update.assert_called()
    
    def test_get_playback_info(self):
        """Test getting playback information."""
        info = self.controller.get_playback_info()
        
        self.assertIn('state', info)
        self.assertIn('is_playing', info)
        self.assertIn('speed', info)
        self.assertIn('total_commits', info)
    
    def test_state_change_callback(self):
        """Test state change callback."""
        callback = Mock()
        self.controller.on_state_change(callback)
        
        self.controller.play()
        
        callback.assert_called_with(PlaybackState.PLAYING)
    
    def test_speed_change_callback(self):
        """Test speed change callback."""
        callback = Mock()
        self.controller.on_speed_change(callback)
        
        self.controller.set_speed(2.0)
        
        callback.assert_called_with(2.0)


if __name__ == '__main__':
    unittest.main()

# Made with Bob
