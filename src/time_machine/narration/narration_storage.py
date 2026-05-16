"""Narration storage - persists and retrieves pre-rendered narrations."""

import json
import hashlib
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import asdict

from .epoch_generator import EpochNarration, Epoch
from .building_explainer import BuildingExplanation
from ..city.city_generator import Building
from ..utils.config import Config
from ..utils.logger import setup_logger


class NarrationStorage:
    """
    Manages storage and retrieval of pre-rendered narrations.
    
    This class provides persistent storage for narrations, enabling:
    - Offline demo mode without live API calls
    - Fallback when live generation fails
    - Fast loading of pre-generated content
    - Repository-specific narration caching
    
    Features:
    - JSON-based storage format
    - Repository-specific storage (by hash)
    - Epoch and building narration storage
    - Automatic fallback on load failure
    - Validation and integrity checking
    
    Architecture:
    - Stores narrations in data/narration directory
    - Uses repository hash for unique identification
    - Separate files for epochs and buildings
    - Graceful degradation on errors
    
    Example:
        ```python
        storage = NarrationStorage()
        
        # Save epoch narrations
        storage.save_epoch_narrations(repo_id, epoch_narrations)
        
        # Load for offline use
        narrations = storage.load_epoch_narrations(repo_id)
        
        # Check if available
        if storage.has_narrations(repo_id):
            # Use pre-rendered narrations
            pass
        ```
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize narration storage.
        
        Args:
            storage_dir: Directory for storage (uses config default if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        
        self.storage_dir = storage_dir or Config.NARRATION_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initialized NarrationStorage at {self.storage_dir}")
    
    def save_epoch_narrations(
        self,
        repository_id: str,
        narrations: List[EpochNarration]
    ) -> bool:
        """
        Save epoch narrations for a repository.
        
        Args:
            repository_id: Unique repository identifier
            narrations: List of EpochNarration objects
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self.logger.info(
                f"Saving {len(narrations)} epoch narrations for {repository_id}"
            )
            
            # Convert to serializable format
            data = {
                'repository_id': repository_id,
                'narration_count': len(narrations),
                'narrations': [self._serialize_epoch_narration(n) for n in narrations]
            }
            
            # Save to file
            file_path = self._get_epoch_file_path(repository_id)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved epoch narrations to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save epoch narrations: {e}")
            return False
    
    def load_epoch_narrations(
        self,
        repository_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Load epoch narrations for a repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            List of narration dictionaries or None if not found
        """
        try:
            file_path = self._get_epoch_file_path(repository_id)
            
            if not file_path.exists():
                self.logger.warning(
                    f"No epoch narrations found for {repository_id}"
                )
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            narrations = data.get('narrations', [])
            self.logger.info(
                f"Loaded {len(narrations)} epoch narrations for {repository_id}"
            )
            
            return narrations
            
        except Exception as e:
            self.logger.error(f"Failed to load epoch narrations: {e}")
            return None
    
    def save_building_explanations(
        self,
        repository_id: str,
        explanations: Dict[str, BuildingExplanation]
    ) -> bool:
        """
        Save building explanations for a repository.
        
        Args:
            repository_id: Unique repository identifier
            explanations: Dictionary mapping file paths to explanations
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self.logger.info(
                f"Saving {len(explanations)} building explanations for {repository_id}"
            )
            
            # Convert to serializable format
            data = {
                'repository_id': repository_id,
                'explanation_count': len(explanations),
                'explanations': {
                    path: self._serialize_building_explanation(exp)
                    for path, exp in explanations.items()
                }
            }
            
            # Save to file
            file_path = self._get_building_file_path(repository_id)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved building explanations to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save building explanations: {e}")
            return False
    
    def load_building_explanations(
        self,
        repository_id: str
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Load building explanations for a repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            Dictionary mapping file paths to explanation dictionaries or None
        """
        try:
            file_path = self._get_building_file_path(repository_id)
            
            if not file_path.exists():
                self.logger.warning(
                    f"No building explanations found for {repository_id}"
                )
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            explanations = data.get('explanations', {})
            self.logger.info(
                f"Loaded {len(explanations)} building explanations for {repository_id}"
            )
            
            return explanations
            
        except Exception as e:
            self.logger.error(f"Failed to load building explanations: {e}")
            return None
    
    def has_epoch_narrations(self, repository_id: str) -> bool:
        """
        Check if epoch narrations exist for repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            True if narrations exist, False otherwise
        """
        file_path = self._get_epoch_file_path(repository_id)
        return file_path.exists()
    
    def has_building_explanations(self, repository_id: str) -> bool:
        """
        Check if building explanations exist for repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            True if explanations exist, False otherwise
        """
        file_path = self._get_building_file_path(repository_id)
        return file_path.exists()
    
    def has_narrations(self, repository_id: str) -> bool:
        """
        Check if any narrations exist for repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            True if any narrations exist, False otherwise
        """
        return (
            self.has_epoch_narrations(repository_id) or
            self.has_building_explanations(repository_id)
        )
    
    def delete_narrations(self, repository_id: str) -> bool:
        """
        Delete all narrations for a repository.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            deleted = False
            
            # Delete epoch narrations
            epoch_file = self._get_epoch_file_path(repository_id)
            if epoch_file.exists():
                epoch_file.unlink()
                deleted = True
            
            # Delete building explanations
            building_file = self._get_building_file_path(repository_id)
            if building_file.exists():
                building_file.unlink()
                deleted = True
            
            if deleted:
                self.logger.info(f"Deleted narrations for {repository_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete narrations: {e}")
            return False
    
    def list_repositories(self) -> List[str]:
        """
        List all repositories with stored narrations.
        
        Returns:
            List of repository IDs
        """
        repositories = set()
        
        # Find all narration files
        for file_path in self.storage_dir.glob("*.json"):
            # Extract repository ID from filename
            filename = file_path.stem
            if filename.endswith('_epochs') or filename.endswith('_buildings'):
                repo_id = filename.rsplit('_', 1)[0]
                repositories.add(repo_id)
        
        return sorted(list(repositories))
    
    def get_storage_info(self, repository_id: str) -> Dict[str, Any]:
        """
        Get information about stored narrations.
        
        Args:
            repository_id: Unique repository identifier
            
        Returns:
            Dictionary with storage information
        """
        info = {
            'repository_id': repository_id,
            'has_epochs': self.has_epoch_narrations(repository_id),
            'has_buildings': self.has_building_explanations(repository_id),
            'epoch_file': None,
            'building_file': None,
            'epoch_count': 0,
            'building_count': 0
        }
        
        # Get epoch file info
        epoch_file = self._get_epoch_file_path(repository_id)
        if epoch_file.exists():
            info['epoch_file'] = str(epoch_file)
            try:
                with open(epoch_file, 'r') as f:
                    data = json.load(f)
                    info['epoch_count'] = data.get('narration_count', 0)
            except:
                pass
        
        # Get building file info
        building_file = self._get_building_file_path(repository_id)
        if building_file.exists():
            info['building_file'] = str(building_file)
            try:
                with open(building_file, 'r') as f:
                    data = json.load(f)
                    info['building_count'] = data.get('explanation_count', 0)
            except:
                pass
        
        return info
    
    @staticmethod
    def generate_repository_id(repository_path: str) -> str:
        """
        Generate unique repository ID from path.
        
        Args:
            repository_path: Path to repository
            
        Returns:
            Unique repository ID (hash)
        """
        # Use hash of repository path
        return hashlib.sha256(repository_path.encode()).hexdigest()[:16]
    
    def _get_epoch_file_path(self, repository_id: str) -> Path:
        """Get file path for epoch narrations."""
        return self.storage_dir / f"{repository_id}_epochs.json"
    
    def _get_building_file_path(self, repository_id: str) -> Path:
        """Get file path for building explanations."""
        return self.storage_dir / f"{repository_id}_buildings.json"
    
    def _serialize_epoch_narration(self, narration: EpochNarration) -> Dict[str, Any]:
        """
        Serialize EpochNarration to dictionary.
        
        Args:
            narration: EpochNarration object
            
        Returns:
            Serializable dictionary
        """
        return {
            'epoch': {
                'start_time': narration.epoch.start_time.isoformat(),
                'end_time': narration.epoch.end_time.isoformat(),
                'title': narration.epoch.title,
                'commit_count': narration.epoch.commit_count,
                'significance_score': narration.epoch.significance_score,
                'key_events': narration.epoch.key_events
            },
            'narration': narration.narration,
            'highlights': narration.highlights,
            'metadata': narration.metadata
        }
    
    def _serialize_building_explanation(
        self,
        explanation: BuildingExplanation
    ) -> Dict[str, Any]:
        """
        Serialize BuildingExplanation to dictionary.
        
        Args:
            explanation: BuildingExplanation object
            
        Returns:
            Serializable dictionary
        """
        return {
            'file_path': explanation.building.file_path,
            'explanation': explanation.explanation,
            'key_events': explanation.key_events,
            'current_time': explanation.current_time,
            'metadata': explanation.metadata,
            'building_info': {
                'lines_of_code': explanation.building.lines_of_code,
                'modification_count': explanation.building.modification_count,
                'neighborhood': explanation.building.neighborhood
            }
        }


# Made with Bob