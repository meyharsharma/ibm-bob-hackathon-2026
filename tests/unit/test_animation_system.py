"""Unit tests for AnimationSystem."""

import unittest
from unittest.mock import Mock

from src.time_machine.rendering.animation_system import (
    AnimationSystem,
    Animation,
    AnimationType,
    EasingFunction
)
from src.time_machine.city.city_generator import Building


class TestAnimation(unittest.TestCase):
    """Test Animation class."""
    
    def test_animation_update(self):
        """Test animation update."""
        anim = Animation(
            file_path="test.py",
            animation_type=AnimationType.GROW,
            start_time=0.0,
            duration=1.0,
            start_value=0.0,
            end_value=1.0
        )
        
        # At start
        value = anim.update(0.0)
        self.assertEqual(value, 0.0)
        
        # At middle
        value = anim.update(0.5)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)
        
        # At end
        value = anim.update(1.0)
        self.assertEqual(value, 1.0)
        self.assertTrue(anim.is_complete)
    
    def test_linear_easing(self):
        """Test linear easing function."""
        anim = Animation(
            file_path="test.py",
            animation_type=AnimationType.GROW,
            start_time=0.0,
            duration=1.0,
            easing=EasingFunction.LINEAR,
            start_value=0.0,
            end_value=1.0
        )
        
        value = anim.update(0.5)
        self.assertAlmostEqual(value, 0.5, places=2)


class TestAnimationSystem(unittest.TestCase):
    """Test AnimationSystem class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.system = AnimationSystem()
        self.building = Building(
            file_path="test.py",
            position=(0.0, 0.0, 0.0),
            height=10.0,
            base_size=(1.5, 1.5),
            color=(255, 0, 0),
            neighborhood="src",
            created_at="commit1",
            last_modified="commit2",
            modification_count=5,
            lines_of_code=100
        )
    
    def test_initialization(self):
        """Test system initialization."""
        self.assertIsNotNone(self.system)
        self.assertEqual(self.system.get_active_animation_count(), 0)
    
    def test_animate_file_added(self):
        """Test animating file addition."""
        self.system.animate_file_added("test.py", self.building, 0.0)
        
        self.assertTrue(self.system.is_animating("test.py"))
        state = self.system.get_building_state("test.py")
        self.assertIsNotNone(state)
        self.assertEqual(state.scale, 0.0)  # Starts at 0
    
    def test_animate_file_deleted_crumble(self):
        """Test animating file deletion with crumble."""
        self.system.animate_file_deleted("test.py", self.building, 0.0, use_crumble=True)
        
        self.assertTrue(self.system.is_animating("test.py"))
        state = self.system.get_building_state("test.py")
        self.assertIsNotNone(state)
    
    def test_animate_file_deleted_fade(self):
        """Test animating file deletion with fade."""
        self.system.animate_file_deleted("test.py", self.building, 0.0, use_crumble=False)
        
        self.assertTrue(self.system.is_animating("test.py"))
        state = self.system.get_building_state("test.py")
        self.assertIsNotNone(state)
    
    def test_animate_file_modified_large_change(self):
        """Test animating large file modification."""
        self.system.animate_file_modified("test.py", self.building, 0.0, lines_changed=250)
        
        self.assertTrue(self.system.is_animating("test.py"))
    
    def test_animate_file_modified_small_change_no_animation(self):
        """Test small changes don't trigger animation."""
        self.system.animate_file_modified("test.py", self.building, 0.0, lines_changed=5)
        
        # Small changes below threshold shouldn't animate
        self.assertFalse(self.system.is_animating("test.py"))
    
    def test_update_advances_animations(self):
        """Test update advances all animations."""
        self.system.animate_file_added("test.py", self.building, 0.0)
        
        # Update animation
        self.system.update(0.5)
        
        state = self.system.get_building_state("test.py")
        self.assertGreater(state.scale, 0.0)
    
    def test_animation_completion(self):
        """Test animation completes and is cleaned up."""
        self.system.animate_file_added("test.py", self.building, 0.0, duration=1.0)
        
        # Complete animation
        self.system.update(2.0)
        
        # Should be cleaned up
        self.assertFalse(self.system.is_animating("test.py"))
    
    def test_stop_animations(self):
        """Test stopping animations for a building."""
        self.system.animate_file_added("test.py", self.building, 0.0)
        self.assertTrue(self.system.is_animating("test.py"))
        
        self.system.stop_animations("test.py")
        self.assertFalse(self.system.is_animating("test.py"))
    
    def test_clear_all_animations(self):
        """Test clearing all animations."""
        self.system.animate_file_added("test1.py", self.building, 0.0)
        self.system.animate_file_added("test2.py", self.building, 0.0)
        
        self.assertEqual(self.system.get_active_animation_count(), 2)
        
        self.system.clear_all_animations()
        self.assertEqual(self.system.get_active_animation_count(), 0)
    
    def test_animation_complete_callback(self):
        """Test animation completion callback."""
        callback = Mock()
        self.system.on_animation_complete(callback)
        
        self.system.animate_file_added("test.py", self.building, 0.0, duration=1.0)
        self.system.update(2.0)
        
        callback.assert_called_once()


if __name__ == '__main__':
    unittest.main()

# Made with Bob
