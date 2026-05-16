"""Integration tests for end-to-end workflows."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.time_machine.ingestion.commit_parser import CommitParser
from src.time_machine.ingestion.file_grouper import FileGrouper
from src.time_machine.city.city_generator import CityGenerator, LayoutConfig
from src.time_machine.rendering.timeline_controller import TimelineController
from src.time_machine.rendering.playback_controller import PlaybackController
from src.time_machine.rendering.animation_system import AnimationSystem
from src.time_machine.narration.epoch_generator import EpochGenerator
from src.time_machine.narration.narration_storage import NarrationStorage


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()
        
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True
        )
        
        # Create some files and commits
        (repo_path / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True
        )
        
        # Add more files
        src_dir = repo_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def main():\n    pass\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add main.py"],
            cwd=repo_path,
            check=True
        )
        
        # Modify file
        (src_dir / "main.py").write_text(
            "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()\n"
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Implement main function"],
            cwd=repo_path,
            check=True
        )
        
        yield repo_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_complete_ingestion_to_city_generation(self, temp_repo):
        """Test UF1: Repository ingestion to city generation."""
        # Step 1: Parse repository commits
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        
        assert len(commits) >= 3, "Should have at least 3 commits"
        assert commits[0].message == "Initial commit"
        
        # Step 2: Group files into neighborhoods
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        
        assert len(neighborhoods) > 0, "Should have at least one neighborhood"
        
        # Step 3: Generate city
        generator = CityGenerator()
        city_state = generator.generate_city(commits, neighborhoods)
        
        assert city_state is not None
        assert len(city_state.buildings) > 0, "Should have buildings"
        assert city_state.commit_sha == commits[-1].sha
    
    def test_city_generation_with_time_travel(self, temp_repo):
        """Test city generation at different points in time."""
        # Parse and group
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        
        # Generate city at different commits
        generator = CityGenerator()
        
        # First commit
        city_state_1 = generator.generate_city_at_commit(
            commits, neighborhoods, commits[0].sha
        )
        
        # Last commit
        city_state_2 = generator.generate_city_at_commit(
            commits, neighborhoods, commits[-1].sha
        )
        
        # Should have more buildings in later commit
        assert len(city_state_2.buildings) >= len(city_state_1.buildings)
    
    def test_timeline_playback_workflow(self, temp_repo):
        """Test UF2: Timeline playback with controls."""
        # Setup
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        generator = CityGenerator()
        
        # Create timeline controller
        timeline = TimelineController(
            commits, neighborhoods, generator, duration=10.0
        )
        
        # Create playback controller
        animation_system = AnimationSystem()
        playback = PlaybackController(timeline, animation_system)
        
        # Test play
        playback.play()
        assert playback.is_playing()
        
        # Test pause
        playback.pause()
        assert playback.is_paused()
        
        # Test resume
        playback.resume()
        assert playback.is_playing()
        
        # Test scrub
        city_state = playback.scrub_to_progress(0.5)
        assert city_state is not None
        assert 0.4 <= timeline.state.progress <= 0.6
        
        # Test speed control
        playback.set_speed(2.0)
        assert timeline.state.playback_speed == 2.0
        
        # Test stop
        playback.stop()
        assert playback.is_stopped()
        assert timeline.state.current_time == 0.0
    
    def test_animation_system_integration(self, temp_repo):
        """Test animation system with city changes."""
        # Setup
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        generator = CityGenerator()
        
        # Generate city states
        city_state_1 = generator.generate_city_at_commit(
            commits, neighborhoods, commits[0].sha
        )
        city_state_2 = generator.generate_city_at_commit(
            commits, neighborhoods, commits[-1].sha
        )
        
        # Create animation system
        anim_system = AnimationSystem()
        
        # Find new buildings
        new_buildings = set(city_state_2.buildings.keys()) - set(city_state_1.buildings.keys())
        
        # Animate new buildings
        current_time = 0.0
        for file_path in new_buildings:
            building = city_state_2.buildings[file_path]
            anim_system.animate_file_added(file_path, building, current_time)
        
        # Update animations
        anim_system.update(current_time + 0.5)
        
        # Check that animations are active
        assert anim_system.get_active_animation_count() > 0
    
    def test_narration_generation_workflow(self, temp_repo):
        """Test UF4: Narration generation and storage."""
        # Setup
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        
        # Test narration storage (simplified - epoch generation requires Bob client)
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = NarrationStorage(Path(temp_dir))
            
            # Create mock epoch narrations
            from src.time_machine.narration.epoch_generator import Epoch, EpochNarration
            
            epoch = Epoch(
                start_time=commits[0].timestamp,
                end_time=commits[-1].timestamp,
                commits=commits,
                title="Test Epoch"
            )
            
            narration = EpochNarration(
                epoch=epoch,
                narration="Test narration for epoch",
                highlights=["Initial commit", "Added features"],
                metadata={'test': True}
            )
            
            # Store epoch narrations
            success = storage.save_epoch_narrations('test_repo', [narration])
            assert success, "Should save narrations successfully"
            
            # Retrieve narrations
            retrieved = storage.load_epoch_narrations('test_repo')
            assert retrieved is not None
            assert len(retrieved) == 1
    
    def test_graceful_degradation_missing_narration(self, temp_repo):
        """Test NFR-05: Graceful degradation when narration unavailable."""
        # Setup without narration
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        generator = CityGenerator()
        
        # Should still be able to generate city
        city_state = generator.generate_city(commits, neighborhoods)
        assert city_state is not None
        
        # Should still be able to create timeline
        timeline = TimelineController(commits, neighborhoods, generator)
        assert timeline is not None
        
        # Should still be able to play
        timeline.play()
        city_state = timeline.update(0.1)
        assert city_state is not None
    
    def test_performance_reasonable_repository(self, temp_repo):
        """Test NFR-03: Performance with reasonable repository size."""
        import time
        
        # Measure parsing time
        start = time.time()
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        ingestion_time = time.time() - start
        
        # Should complete quickly for small repo
        assert ingestion_time < 5.0, f"Ingestion took {ingestion_time:.2f}s"
        
        # Measure city generation time
        start = time.time()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        generator = CityGenerator()
        city_state = generator.generate_city(commits, neighborhoods)
        generation_time = time.time() - start
        
        # Should complete quickly
        assert generation_time < 5.0, f"City generation took {generation_time:.2f}s"
    
    def test_city_state_serialization(self, temp_repo):
        """Test city state can be saved and loaded."""
        # Generate city
        parser = CommitParser(str(temp_repo))
        commits = parser.parse_history()
        grouper = FileGrouper()
        neighborhoods = grouper.group_files(commits)
        generator = CityGenerator()
        city_state = generator.generate_city(commits, neighborhoods)
        
        # Save to file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            generator.save_city_state(city_state, temp_file)
            
            # Load from file
            loaded_state = generator.load_city_state(temp_file)
            
            # Verify
            assert loaded_state.commit_sha == city_state.commit_sha
            assert len(loaded_state.buildings) == len(city_state.buildings)
            assert loaded_state.timestamp == city_state.timestamp
        finally:
            Path(temp_file).unlink()


class TestDemoModeWorkflow:
    """Test demo mode functionality (NFR-01)."""
    
    def test_offline_playback_with_cached_data(self):
        """Test that demo can run without network access."""
        # This test verifies that all necessary data can be pre-generated
        # and stored for offline playback
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = NarrationStorage(Path(temp_dir))
            
            # Create mock epoch narrations
            from src.time_machine.narration.epoch_generator import Epoch, EpochNarration
            
            narrations = []
            for i in range(5):
                epoch = Epoch(
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(days=7),
                    commits=[],
                    title=f"Epoch {i}"
                )
                narration = EpochNarration(
                    epoch=epoch,
                    narration=f'Epoch {i} narration',
                    highlights=[f'Event {i}'],
                    metadata={'epoch_index': i}
                )
                narrations.append(narration)
            
            # Store all narrations
            success = storage.save_epoch_narrations('demo_repo', narrations)
            assert success
            
            # Verify all narrations can be retrieved
            retrieved = storage.load_epoch_narrations('demo_repo')
            assert retrieved is not None
            assert len(retrieved) == 5
    
    def test_pre_rendered_narration_fallback(self):
        """Test fallback to pre-rendered narration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = NarrationStorage(Path(temp_dir))
            
            # Create pre-rendered narration
            from src.time_machine.narration.epoch_generator import Epoch, EpochNarration
            
            epoch = Epoch(
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(days=7),
                commits=[],
                title="Pre-rendered Epoch"
            )
            
            narration = EpochNarration(
                epoch=epoch,
                narration='Pre-rendered narration',
                highlights=['Fallback content'],
                metadata={'is_fallback': True}
            )
            
            # Store pre-rendered narration
            success = storage.save_epoch_narrations('test_repo', [narration])
            assert success
            
            # Simulate failed live generation by using stored version
            retrieved = storage.load_epoch_narrations('test_repo')
            assert retrieved is not None
            assert len(retrieved) > 0
            assert retrieved[0].metadata.get('is_fallback') is True


# Made with Bob