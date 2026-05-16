"""Unit tests for narration components."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

from src.time_machine.narration.bob_client import (
    BobClient,
    NarrationRequest,
    NarrationResponse,
    NarrationType
)
from src.time_machine.narration.epoch_generator import (
    EpochGenerator,
    Epoch
)
from src.time_machine.narration.narration_storage import NarrationStorage
from src.time_machine.ingestion.commit_parser import CommitInfo
from src.time_machine.city.city_generator import Building


class TestBobClient(unittest.TestCase):
    """Test BobClient class."""
    
    def test_initialization_offline_mode(self):
        """Test client initialization in offline mode."""
        client = BobClient(offline_mode=True)
        
        self.assertTrue(client.offline_mode)
        self.assertIsNone(client.assistant)
    
    def test_narration_request_creation(self):
        """Test creating narration request."""
        request = NarrationRequest(
            narration_type=NarrationType.EPOCH_SUMMARY,
            context={'commits': []},
            max_length=200
        )
        
        self.assertEqual(request.narration_type, NarrationType.EPOCH_SUMMARY)
        self.assertEqual(request.max_length, 200)
    
    def test_offline_fallback(self):
        """Test offline fallback narration."""
        client = BobClient(offline_mode=True)
        
        request = NarrationRequest(
            narration_type=NarrationType.EPOCH_SUMMARY,
            context={'commits': [], 'timeframe': 'January 2024'}
        )
        
        response = client.generate_narration(request)
        
        self.assertTrue(response.success)
        self.assertIsNotNone(response.text)
        self.assertTrue(response.metadata.get('offline', False))


class TestEpochGenerator(unittest.TestCase):
    """Test EpochGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bob_client = Mock(spec=BobClient)
        self.generator = EpochGenerator(self.bob_client)
        
        # Create mock commits
        self.commits = [
            CommitInfo(
                sha=f"commit{i}",
                message=f"Commit {i}",
                author="Test Author",
                author_email="test@example.com",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                files_changed=[]
            )
            for i in range(30)
        ]
    
    def test_initialization(self):
        """Test generator initialization."""
        self.assertIsNotNone(self.generator)
        self.assertEqual(len(self.generator._narration_cache), 0)
    
    def test_identify_epochs(self):
        """Test epoch identification."""
        epochs = self.generator.identify_epochs(self.commits)
        
        self.assertGreater(len(epochs), 0)
        self.assertLessEqual(len(epochs), self.generator.MAX_EPOCHS)
        
        # Check epochs are ordered
        for i in range(len(epochs) - 1):
            self.assertLess(epochs[i].start_time, epochs[i+1].start_time)
    
    def test_identify_epochs_empty_commits(self):
        """Test epoch identification with empty commits."""
        epochs = self.generator.identify_epochs([])
        
        self.assertEqual(len(epochs), 0)
    
    def test_epoch_properties(self):
        """Test epoch properties."""
        epochs = self.generator.identify_epochs(self.commits)
        
        if epochs:
            epoch = epochs[0]
            self.assertIsNotNone(epoch.title)
            self.assertGreaterEqual(epoch.significance_score, 0.0)
            self.assertLessEqual(epoch.significance_score, 1.0)
            self.assertGreater(epoch.commit_count, 0)
    
    def test_generate_epoch_narration(self):
        """Test epoch narration generation."""
        epochs = self.generator.identify_epochs(self.commits)
        
        if epochs:
            # Mock Bob response
            mock_response = NarrationResponse(
                text="Test narration",
                success=True
            )
            self.bob_client.generate_narration.return_value = mock_response
            
            narration = self.generator.generate_epoch_narration(epochs[0])
            
            self.assertIsNotNone(narration)
            self.assertEqual(narration.narration, "Test narration")
            self.assertIsNotNone(narration.highlights)


class TestNarrationStorage(unittest.TestCase):
    """Test NarrationStorage class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.storage = NarrationStorage(storage_dir=Path(self.temp_dir))
        self.repo_id = "test_repo_123"
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test storage initialization."""
        self.assertIsNotNone(self.storage)
        self.assertTrue(self.storage.storage_dir.exists())
    
    def test_generate_repository_id(self):
        """Test repository ID generation."""
        repo_id = NarrationStorage.generate_repository_id("/path/to/repo")
        
        self.assertIsNotNone(repo_id)
        self.assertEqual(len(repo_id), 16)  # Hash truncated to 16 chars
    
    def test_save_and_load_epoch_narrations(self):
        """Test saving and loading epoch narrations."""
        # Create mock narrations
        epoch = Epoch(
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            commits=[],
            title="January 2024"
        )
        
        from src.time_machine.narration.epoch_generator import EpochNarration
        narrations = [
            EpochNarration(
                epoch=epoch,
                narration="Test narration",
                highlights=["Event 1", "Event 2"],
                metadata={}
            )
        ]
        
        # Save
        success = self.storage.save_epoch_narrations(self.repo_id, narrations)
        self.assertTrue(success)
        
        # Load
        loaded = self.storage.load_epoch_narrations(self.repo_id)
        self.assertIsNotNone(loaded)
        if loaded:
            self.assertEqual(len(loaded), 1)
    
    def test_has_narrations(self):
        """Test checking for narration existence."""
        # Initially no narrations
        self.assertFalse(self.storage.has_narrations(self.repo_id))
        
        # Save some narrations
        epoch = Epoch(
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            commits=[],
            title="January 2024"
        )
        
        from src.time_machine.narration.epoch_generator import EpochNarration
        narrations = [
            EpochNarration(
                epoch=epoch,
                narration="Test",
                highlights=[],
                metadata={}
            )
        ]
        
        self.storage.save_epoch_narrations(self.repo_id, narrations)
        
        # Now should have narrations
        self.assertTrue(self.storage.has_narrations(self.repo_id))
    
    def test_delete_narrations(self):
        """Test deleting narrations."""
        # Save narrations
        epoch = Epoch(
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            commits=[],
            title="January 2024"
        )
        
        from src.time_machine.narration.epoch_generator import EpochNarration
        narrations = [
            EpochNarration(
                epoch=epoch,
                narration="Test",
                highlights=[],
                metadata={}
            )
        ]
        
        self.storage.save_epoch_narrations(self.repo_id, narrations)
        self.assertTrue(self.storage.has_narrations(self.repo_id))
        
        # Delete
        success = self.storage.delete_narrations(self.repo_id)
        self.assertTrue(success)
        self.assertFalse(self.storage.has_narrations(self.repo_id))
    
    def test_list_repositories(self):
        """Test listing repositories."""
        # Initially empty
        repos = self.storage.list_repositories()
        self.assertEqual(len(repos), 0)
        
        # Save narrations for multiple repos
        for i in range(3):
            repo_id = f"repo_{i}"
            epoch = Epoch(
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 31),
                commits=[],
                title="Test"
            )
            
            from src.time_machine.narration.epoch_generator import EpochNarration
            narrations = [
                EpochNarration(
                    epoch=epoch,
                    narration="Test",
                    highlights=[],
                    metadata={}
                )
            ]
            
            self.storage.save_epoch_narrations(repo_id, narrations)
        
        # Should list all repos
        repos = self.storage.list_repositories()
        self.assertEqual(len(repos), 3)
    
    def test_get_storage_info(self):
        """Test getting storage information."""
        info = self.storage.get_storage_info(self.repo_id)
        
        self.assertIn('repository_id', info)
        self.assertIn('has_epochs', info)
        self.assertIn('has_buildings', info)
        self.assertEqual(info['repository_id'], self.repo_id)


if __name__ == '__main__':
    unittest.main()

# Made with Bob
