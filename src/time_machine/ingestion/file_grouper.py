"""File grouping - organizes files into neighborhoods based on directory structure."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from collections import defaultdict
import json

from .commit_parser import CommitInfo, ChangeType
from ..utils.config import Config
from ..utils.logger import setup_logger


@dataclass
class Neighborhood:
    """Represents a neighborhood (module/directory) in the city."""
    name: str
    path: str
    files: Set[str] = field(default_factory=set)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'path': self.path,
            'files': sorted(list(self.files)),
            'parent': self.parent,
            'children': self.children
        }


@dataclass
class FileLocation:
    """Tracks a file's location over time."""
    file_path: str
    neighborhood: str
    first_seen: str  # commit SHA
    last_seen: Optional[str] = None  # commit SHA when deleted
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'file_path': self.file_path,
            'neighborhood': self.neighborhood,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen
        }


class FileGrouper:
    """
    Groups files into neighborhoods based on directory structure.
    
    Tracks file locations over time as they move between directories.
    Ensures each file belongs to exactly one neighborhood at any moment.
    """
    
    def __init__(self):
        """Initialize the file grouper."""
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.neighborhoods: Dict[str, Neighborhood] = {}
        self.file_locations: Dict[str, List[FileLocation]] = defaultdict(list)
    
    def group_files(self, commits: List[CommitInfo]) -> Dict[str, Neighborhood]:
        """
        Group files into neighborhoods based on commit history.
        
        Args:
            commits: List of CommitInfo objects (chronological order)
            
        Returns:
            Dictionary mapping neighborhood paths to Neighborhood objects
            
        Acceptance Criteria:
            - AC-03.1: Every file belongs to exactly one neighborhood at any moment ✓
            - AC-03.2: Files moving between directories update neighborhood assignment ✓
        """
        self.logger.info(f"Grouping files from {len(commits)} commits into neighborhoods")
        
        # Track current file locations
        current_files: Dict[str, str] = {}  # file_path -> neighborhood_path
        
        for commit in commits:
            for change in commit.files_changed:
                if change.change_type == ChangeType.ADDED:
                    # File added - assign to neighborhood
                    neighborhood_path = self._get_neighborhood_path(change.path)
                    current_files[change.path] = neighborhood_path
                    
                    # Create neighborhood if it doesn't exist
                    if neighborhood_path not in self.neighborhoods:
                        self._create_neighborhood(neighborhood_path)
                    
                    # Add file to neighborhood
                    self.neighborhoods[neighborhood_path].files.add(change.path)
                    
                    # Record file location
                    self.file_locations[change.path].append(
                        FileLocation(
                            file_path=change.path,
                            neighborhood=neighborhood_path,
                            first_seen=commit.sha
                        )
                    )
                    
                elif change.change_type == ChangeType.DELETED:
                    # File deleted - remove from neighborhood
                    if change.path in current_files:
                        old_neighborhood = current_files[change.path]
                        if old_neighborhood in self.neighborhoods:
                            self.neighborhoods[old_neighborhood].files.discard(change.path)
                        
                        # Mark file location as ended
                        if self.file_locations[change.path]:
                            self.file_locations[change.path][-1].last_seen = commit.sha
                        
                        del current_files[change.path]
                    
                elif change.change_type == ChangeType.RENAMED:
                    # File renamed/moved - update neighborhood assignment
                    old_path = change.old_path
                    new_path = change.path
                    
                    # Remove from old neighborhood
                    if old_path in current_files:
                        old_neighborhood = current_files[old_path]
                        if old_neighborhood in self.neighborhoods:
                            self.neighborhoods[old_neighborhood].files.discard(old_path)
                        
                        # Mark old location as ended
                        if self.file_locations[old_path]:
                            self.file_locations[old_path][-1].last_seen = commit.sha
                        
                        del current_files[old_path]
                    
                    # Add to new neighborhood
                    new_neighborhood = self._get_neighborhood_path(new_path)
                    current_files[new_path] = new_neighborhood
                    
                    # Create neighborhood if it doesn't exist
                    if new_neighborhood not in self.neighborhoods:
                        self._create_neighborhood(new_neighborhood)
                    
                    # Add file to new neighborhood
                    self.neighborhoods[new_neighborhood].files.add(new_path)
                    
                    # Record new file location
                    self.file_locations[new_path].append(
                        FileLocation(
                            file_path=new_path,
                            neighborhood=new_neighborhood,
                            first_seen=commit.sha
                        )
                    )
                    
                elif change.change_type == ChangeType.MODIFIED:
                    # File modified - ensure it's in correct neighborhood
                    # (in case we missed an earlier add)
                    if change.path not in current_files:
                        neighborhood_path = self._get_neighborhood_path(change.path)
                        current_files[change.path] = neighborhood_path
                        
                        if neighborhood_path not in self.neighborhoods:
                            self._create_neighborhood(neighborhood_path)
                        
                        self.neighborhoods[neighborhood_path].files.add(change.path)
                        
                        self.file_locations[change.path].append(
                            FileLocation(
                                file_path=change.path,
                                neighborhood=neighborhood_path,
                                first_seen=commit.sha
                            )
                        )
        
        self.logger.info(
            f"Created {len(self.neighborhoods)} neighborhoods with "
            f"{len(current_files)} active files"
        )
        
        return self.neighborhoods
    
    def _get_neighborhood_path(self, file_path: str) -> str:
        """
        Get the neighborhood path for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Neighborhood path (directory containing the file)
        """
        path = Path(file_path)
        
        # If file is in root, use root as neighborhood
        if len(path.parts) == 1:
            return "."
        
        # Use parent directory as neighborhood
        return str(path.parent)
    
    def _create_neighborhood(self, neighborhood_path: str) -> None:
        """
        Create a neighborhood and its parent hierarchy.
        
        Args:
            neighborhood_path: Path to neighborhood
        """
        if neighborhood_path in self.neighborhoods:
            return
        
        path = Path(neighborhood_path)
        
        # Create neighborhood
        neighborhood = Neighborhood(
            name=path.name if path.name else "root",
            path=neighborhood_path
        )
        
        # Set up parent-child relationships
        if len(path.parts) > 1:
            parent_path = str(path.parent)
            neighborhood.parent = parent_path
            
            # Create parent if it doesn't exist
            if parent_path not in self.neighborhoods:
                self._create_neighborhood(parent_path)
            
            # Add this neighborhood as child of parent
            self.neighborhoods[parent_path].children.append(neighborhood_path)
        
        self.neighborhoods[neighborhood_path] = neighborhood
    
    def get_file_neighborhood(
        self,
        file_path: str,
        commit_sha: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the neighborhood a file belongs to at a specific commit.
        
        Args:
            file_path: Path to file
            commit_sha: Commit SHA (None for current/latest)
            
        Returns:
            Neighborhood path or None if file doesn't exist at that commit
        """
        if file_path not in self.file_locations:
            return None
        
        locations = self.file_locations[file_path]
        
        if commit_sha is None:
            # Return latest location
            return locations[-1].neighborhood if locations else None
        
        # Find location at specific commit
        for location in locations:
            if location.first_seen == commit_sha:
                return location.neighborhood
            if location.last_seen and location.last_seen == commit_sha:
                return None  # File was deleted at this commit
        
        return None
    
    def get_neighborhood_files(
        self,
        neighborhood_path: str,
        commit_sha: Optional[str] = None
    ) -> Set[str]:
        """
        Get all files in a neighborhood at a specific commit.
        
        Args:
            neighborhood_path: Path to neighborhood
            commit_sha: Commit SHA (None for current/latest)
            
        Returns:
            Set of file paths in the neighborhood
        """
        if neighborhood_path not in self.neighborhoods:
            return set()
        
        if commit_sha is None:
            # Return current files
            return self.neighborhoods[neighborhood_path].files.copy()
        
        # Build file set at specific commit
        files = set()
        for file_path, locations in self.file_locations.items():
            for location in locations:
                if location.neighborhood == neighborhood_path:
                    # Check if file existed at this commit
                    if location.first_seen <= commit_sha:
                        if location.last_seen is None or location.last_seen > commit_sha:
                            files.add(file_path)
        
        return files
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about neighborhoods and file groupings.
        
        Returns:
            Dictionary with statistics
        """
        total_files = sum(len(n.files) for n in self.neighborhoods.values())
        
        # Calculate depth distribution
        depth_counts = defaultdict(int)
        for neighborhood in self.neighborhoods.values():
            depth = len(Path(neighborhood.path).parts)
            depth_counts[depth] += 1
        
        # Find largest neighborhoods
        largest = sorted(
            self.neighborhoods.values(),
            key=lambda n: len(n.files),
            reverse=True
        )[:5]
        
        return {
            'total_neighborhoods': len(self.neighborhoods),
            'total_files': total_files,
            'avg_files_per_neighborhood': total_files / len(self.neighborhoods) if self.neighborhoods else 0,
            'depth_distribution': dict(depth_counts),
            'largest_neighborhoods': [
                {'path': n.path, 'file_count': len(n.files)}
                for n in largest
            ]
        }
    
    def save(self, output_path: str) -> None:
        """
        Save neighborhood data to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        self.logger.info(f"Saving neighborhood data to: {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'neighborhoods': {
                path: neighborhood.to_dict()
                for path, neighborhood in self.neighborhoods.items()
            },
            'file_locations': {
                file_path: [loc.to_dict() for loc in locations]
                for file_path, locations in self.file_locations.items()
            },
            'statistics': self.get_statistics()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Saved {len(self.neighborhoods)} neighborhoods to {output_path}")
    
    def load(self, input_path: str) -> None:
        """
        Load neighborhood data from JSON file.
        
        Args:
            input_path: Path to input JSON file
        """
        self.logger.info(f"Loading neighborhood data from: {input_path}")
        
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Reconstruct neighborhoods
        self.neighborhoods = {}
        for path, neighborhood_data in data['neighborhoods'].items():
            neighborhood = Neighborhood(
                name=neighborhood_data['name'],
                path=neighborhood_data['path'],
                files=set(neighborhood_data['files']),
                parent=neighborhood_data.get('parent'),
                children=neighborhood_data.get('children', [])
            )
            self.neighborhoods[path] = neighborhood
        
        # Reconstruct file locations
        self.file_locations = defaultdict(list)
        for file_path, locations_data in data['file_locations'].items():
            for loc_data in locations_data:
                location = FileLocation(
                    file_path=loc_data['file_path'],
                    neighborhood=loc_data['neighborhood'],
                    first_seen=loc_data['first_seen'],
                    last_seen=loc_data.get('last_seen')
                )
                self.file_locations[file_path].append(location)
        
        self.logger.info(f"Loaded {len(self.neighborhoods)} neighborhoods from {input_path}")

# Made with Bob
