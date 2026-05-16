"""City generation - creates 3D city representation from repository data."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from pathlib import Path
import json
import math

from ..ingestion.commit_parser import CommitInfo, ChangeType
from ..ingestion.file_grouper import Neighborhood
from ..utils.config import Config
from ..utils.logger import setup_logger


@dataclass
class Building:
    """
    Represents a building (file) in the 3D city.
    
    Attributes:
        file_path: Path to the file this building represents
        position: (x, y, z) coordinates in 3D space
        height: Building height (based on file size/complexity)
        base_size: (width, depth) of building base
        color: RGB color tuple (0-255) representing file age/activity
        neighborhood: Neighborhood this building belongs to
        created_at: Commit SHA when file was created
        last_modified: Commit SHA of last modification
        modification_count: Number of times file was modified
        lines_of_code: Total lines in the file
    """
    file_path: str
    position: Tuple[float, float, float]
    height: float
    base_size: Tuple[float, float]
    color: Tuple[int, int, int]
    neighborhood: str
    created_at: str
    last_modified: str
    modification_count: int = 0
    lines_of_code: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'file_path': self.file_path,
            'position': list(self.position),
            'height': self.height,
            'base_size': list(self.base_size),
            'color': list(self.color),
            'neighborhood': self.neighborhood,
            'created_at': self.created_at,
            'last_modified': self.last_modified,
            'modification_count': self.modification_count,
            'lines_of_code': self.lines_of_code
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Building':
        """Create Building from dictionary."""
        return cls(
            file_path=data['file_path'],
            position=tuple(data['position']),
            height=data['height'],
            base_size=tuple(data['base_size']),
            color=tuple(data['color']),
            neighborhood=data['neighborhood'],
            created_at=data['created_at'],
            last_modified=data['last_modified'],
            modification_count=data.get('modification_count', 0),
            lines_of_code=data.get('lines_of_code', 0)
        )


@dataclass
class LayoutConfig:
    """
    Configuration for city layout algorithm.
    
    Attributes:
        grid_size: Size of grid cells for spatial organization
        building_spacing: Minimum spacing between buildings
        neighborhood_spacing: Spacing between neighborhoods
        max_building_height: Maximum height for buildings
        min_building_height: Minimum height for buildings
        base_building_size: Default base size for buildings
        layout_algorithm: Algorithm to use ('grid' or 'force_directed')
    """
    grid_size: float = 10.0
    building_spacing: float = 2.0
    neighborhood_spacing: float = 5.0
    max_building_height: float = 50.0
    min_building_height: float = 1.0
    base_building_size: Tuple[float, float] = (1.5, 1.5)
    layout_algorithm: str = 'grid'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'grid_size': self.grid_size,
            'building_spacing': self.building_spacing,
            'neighborhood_spacing': self.neighborhood_spacing,
            'max_building_height': self.max_building_height,
            'min_building_height': self.min_building_height,
            'base_building_size': list(self.base_building_size),
            'layout_algorithm': self.layout_algorithm
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutConfig':
        """Create LayoutConfig from dictionary."""
        return cls(
            grid_size=data.get('grid_size', 10.0),
            building_spacing=data.get('building_spacing', 2.0),
            neighborhood_spacing=data.get('neighborhood_spacing', 5.0),
            max_building_height=data.get('max_building_height', 50.0),
            min_building_height=data.get('min_building_height', 1.0),
            base_building_size=tuple(data.get('base_building_size', [1.5, 1.5])),
            layout_algorithm=data.get('layout_algorithm', 'grid')
        )


@dataclass
class CityState:
    """
    Represents the complete state of the city at a specific point in time.
    
    Attributes:
        commit_sha: Commit SHA this state represents
        timestamp: Timestamp of the commit
        buildings: Dictionary mapping file paths to Building objects
        neighborhoods: Dictionary mapping neighborhood paths to metadata
        layout_config: Configuration used for layout
        statistics: Statistics about the city state
    """
    commit_sha: str
    timestamp: datetime
    buildings: Dict[str, Building] = field(default_factory=dict)
    neighborhoods: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    layout_config: LayoutConfig = field(default_factory=LayoutConfig)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'commit_sha': self.commit_sha,
            'timestamp': self.timestamp.isoformat(),
            'buildings': {
                path: building.to_dict()
                for path, building in self.buildings.items()
            },
            'neighborhoods': self.neighborhoods,
            'layout_config': self.layout_config.to_dict(),
            'statistics': self.statistics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CityState':
        """Create CityState from dictionary."""
        return cls(
            commit_sha=data['commit_sha'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            buildings={
                path: Building.from_dict(building_data)
                for path, building_data in data['buildings'].items()
            },
            neighborhoods=data.get('neighborhoods', {}),
            layout_config=LayoutConfig.from_dict(data.get('layout_config', {})),
            statistics=data.get('statistics', {})
        )


class CityGenerator:
    """
    Generates 3D city representation from repository data.
    
    This class is the core of the city generation system. It takes commit history
    and neighborhood data from the ingestion module and creates a 3D city layout
    where files are represented as buildings and directories as neighborhoods.
    
    The generator supports:
    - Multiple layout algorithms (grid-based, force-directed)
    - Time-based city state generation (city at any commit)
    - Building property calculation based on file metrics
    - Spatial organization of neighborhoods
    - JSON serialization for persistence
    
    Architecture:
    - Uses scene graph pattern for organizing 3D objects
    - Maintains building registry for efficient lookups
    - Calculates positions using configurable layout algorithms
    - Tracks file metrics across commit history
    """
    
    def __init__(self, layout_config: Optional[LayoutConfig] = None):
        """
        Initialize the city generator.
        
        Args:
            layout_config: Configuration for city layout (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.layout_config = layout_config or LayoutConfig()
        
        # Building registry: file_path -> Building
        self.buildings: Dict[str, Building] = {}
        
        # File metrics tracking: file_path -> metrics
        self.file_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Neighborhood positions: neighborhood_path -> (x, y)
        self.neighborhood_positions: Dict[str, Tuple[float, float]] = {}
        
        self.logger.info(
            f"Initialized CityGenerator with {self.layout_config.layout_algorithm} layout"
        )
    
    def generate_city(
        self,
        commits: List[CommitInfo],
        neighborhoods: Dict[str, Neighborhood]
    ) -> CityState:
        """
        Generate complete city from repository data.
        
        This is the main entry point for city generation. It processes all commits
        to build file metrics, calculates spatial layout, and creates buildings.
        
        Args:
            commits: List of CommitInfo objects (chronological order)
            neighborhoods: Dictionary of Neighborhood objects
            
        Returns:
            CityState representing the final state of the repository
            
        Raises:
            ValueError: If commits list is empty or neighborhoods is invalid
        """
        if not commits:
            raise ValueError("Cannot generate city from empty commit history")
        
        self.logger.info(
            f"Generating city from {len(commits)} commits and "
            f"{len(neighborhoods)} neighborhoods"
        )
        
        try:
            # Step 1: Calculate file metrics from commit history
            self._calculate_file_metrics(commits)
            
            # Step 2: Calculate neighborhood positions
            self._calculate_neighborhood_positions(neighborhoods)
            
            # Step 3: Generate buildings for all files
            self._generate_buildings(neighborhoods)
            
            # Step 4: Create city state
            city_state = self._create_city_state(commits[-1], neighborhoods)
            
            self.logger.info(
                f"City generation complete: {len(self.buildings)} buildings in "
                f"{len(neighborhoods)} neighborhoods"
            )
            
            return city_state
            
        except Exception as e:
            self.logger.error(f"Failed to generate city: {e}", exc_info=True)
            raise
    
    def generate_city_at_commit(
        self,
        commits: List[CommitInfo],
        neighborhoods: Dict[str, Neighborhood],
        target_commit_sha: str
    ) -> CityState:
        """
        Generate city state at a specific commit in history.
        
        This method allows time-travel through the repository history by
        generating the city as it existed at any point in time.
        
        Args:
            commits: List of all CommitInfo objects (chronological order)
            neighborhoods: Dictionary of Neighborhood objects
            target_commit_sha: SHA of commit to generate city for
            
        Returns:
            CityState representing the repository at the target commit
            
        Raises:
            ValueError: If target commit is not found in history
        """
        # Find target commit index
        target_index = None
        for i, commit in enumerate(commits):
            if commit.sha == target_commit_sha:
                target_index = i
                break
        
        if target_index is None:
            raise ValueError(f"Commit {target_commit_sha} not found in history")
        
        self.logger.info(
            f"Generating city at commit {target_commit_sha[:8]} "
            f"({target_index + 1}/{len(commits)})"
        )
        
        # Process commits up to target
        commits_up_to_target = commits[:target_index + 1]
        
        # Calculate metrics only from commits up to target
        self._calculate_file_metrics(commits_up_to_target)
        
        # Calculate positions
        self._calculate_neighborhood_positions(neighborhoods)
        
        # Generate buildings (only for files that exist at target commit)
        self._generate_buildings_at_commit(
            neighborhoods,
            commits_up_to_target,
            target_commit_sha
        )
        
        # Create city state
        city_state = self._create_city_state(
            commits[target_index],
            neighborhoods
        )
        
        self.logger.info(
            f"Generated city at commit {target_commit_sha[:8]}: "
            f"{len(self.buildings)} buildings"
        )
        
        return city_state
    
    def _calculate_file_metrics(self, commits: List[CommitInfo]) -> None:
        """
        Calculate metrics for all files from commit history.
        
        Tracks:
        - Creation commit
        - Last modification commit
        - Total modifications
        - Lines added/deleted
        
        Args:
            commits: List of CommitInfo objects
        """
        self.logger.info("Calculating file metrics from commit history")
        
        self.file_metrics = {}
        
        for commit in commits:
            for change in commit.files_changed:
                file_path = change.path
                
                # Initialize metrics if first time seeing file
                if file_path not in self.file_metrics:
                    self.file_metrics[file_path] = {
                        'created_at': commit.sha,
                        'last_modified': commit.sha,
                        'modification_count': 0,
                        'total_lines_added': 0,
                        'total_lines_deleted': 0,
                        'current_lines': 0
                    }
                
                metrics = self.file_metrics[file_path]
                
                # Update metrics based on change type
                if change.change_type == ChangeType.ADDED:
                    metrics['created_at'] = commit.sha
                    metrics['total_lines_added'] += change.lines_added
                    metrics['current_lines'] += change.lines_added
                    
                elif change.change_type == ChangeType.MODIFIED:
                    metrics['last_modified'] = commit.sha
                    metrics['modification_count'] += 1
                    metrics['total_lines_added'] += change.lines_added
                    metrics['total_lines_deleted'] += change.lines_deleted
                    metrics['current_lines'] += (
                        change.lines_added - change.lines_deleted
                    )
                    
                elif change.change_type == ChangeType.DELETED:
                    metrics['last_modified'] = commit.sha
                    metrics['current_lines'] = 0
                    
                elif change.change_type == ChangeType.RENAMED:
                    # Handle renamed files
                    if change.old_path and change.old_path in self.file_metrics:
                        # Copy metrics from old path
                        old_metrics = self.file_metrics[change.old_path]
                        self.file_metrics[file_path] = old_metrics.copy()
                        self.file_metrics[file_path]['last_modified'] = commit.sha
                    else:
                        # Treat as new file
                        metrics['created_at'] = commit.sha
                        metrics['last_modified'] = commit.sha
        
        self.logger.info(f"Calculated metrics for {len(self.file_metrics)} files")
    
    def _calculate_neighborhood_positions(
        self,
        neighborhoods: Dict[str, Neighborhood]
    ) -> None:
        """
        Calculate spatial positions for neighborhoods using layout algorithm.
        
        Args:
            neighborhoods: Dictionary of Neighborhood objects
        """
        self.logger.info(
            f"Calculating neighborhood positions using "
            f"{self.layout_config.layout_algorithm} algorithm"
        )
        
        if self.layout_config.layout_algorithm == 'grid':
            self._calculate_grid_layout(neighborhoods)
        else:
            # Default to grid if unknown algorithm
            self.logger.warning(
                f"Unknown layout algorithm: {self.layout_config.layout_algorithm}, "
                "using grid"
            )
            self._calculate_grid_layout(neighborhoods)
    
    def _calculate_grid_layout(
        self,
        neighborhoods: Dict[str, Neighborhood]
    ) -> None:
        """
        Calculate grid-based layout for neighborhoods.
        
        Organizes neighborhoods in a grid pattern with proper spacing.
        Root-level neighborhoods are placed first, then nested ones.
        
        Args:
            neighborhoods: Dictionary of Neighborhood objects
        """
        self.neighborhood_positions = {}
        
        # Separate root and nested neighborhoods
        root_neighborhoods = [
            n for n in neighborhoods.values()
            if n.parent is None or n.parent == "."
        ]
        
        # Calculate grid dimensions
        grid_cols = math.ceil(math.sqrt(len(root_neighborhoods)))
        
        # Position root neighborhoods
        for i, neighborhood in enumerate(root_neighborhoods):
            row = i // grid_cols
            col = i % grid_cols
            
            x = col * (self.layout_config.grid_size + 
                      self.layout_config.neighborhood_spacing)
            y = row * (self.layout_config.grid_size + 
                      self.layout_config.neighborhood_spacing)
            
            self.neighborhood_positions[neighborhood.path] = (x, y)
        
        # Position nested neighborhoods relative to parents
        for neighborhood in neighborhoods.values():
            if neighborhood.path not in self.neighborhood_positions:
                if neighborhood.parent and neighborhood.parent in self.neighborhood_positions:
                    parent_pos = self.neighborhood_positions[neighborhood.parent]
                    # Offset from parent
                    offset = len([n for n in neighborhoods.values() 
                                if n.parent == neighborhood.parent])
                    x = parent_pos[0] + offset * self.layout_config.grid_size
                    y = parent_pos[1] + self.layout_config.grid_size
                    self.neighborhood_positions[neighborhood.path] = (x, y)
                else:
                    # Fallback position
                    self.neighborhood_positions[neighborhood.path] = (0, 0)
        
        self.logger.info(
            f"Positioned {len(self.neighborhood_positions)} neighborhoods in grid"
        )
    
    def _generate_buildings(self, neighborhoods: Dict[str, Neighborhood]) -> None:
        """
        Generate buildings for all files in neighborhoods.
        
        Args:
            neighborhoods: Dictionary of Neighborhood objects
        """
        self.logger.info("Generating buildings for all files")
        
        self.buildings = {}
        
        for neighborhood in neighborhoods.values():
            neighborhood_pos = self.neighborhood_positions.get(
                neighborhood.path,
                (0, 0)
            )
            
            # Position buildings within neighborhood
            files = sorted(list(neighborhood.files))
            for i, file_path in enumerate(files):
                if file_path in self.file_metrics:
                    building = self._create_building(
                        file_path,
                        neighborhood,
                        neighborhood_pos,
                        i
                    )
                    self.buildings[file_path] = building
        
        self.logger.info(f"Generated {len(self.buildings)} buildings")
    
    def _generate_buildings_at_commit(
        self,
        neighborhoods: Dict[str, Neighborhood],
        commits: List[CommitInfo],
        target_commit_sha: str
    ) -> None:
        """
        Generate buildings for files that exist at a specific commit.
        
        Args:
            neighborhoods: Dictionary of Neighborhood objects
            commits: List of commits up to target
            target_commit_sha: Target commit SHA
        """
        self.logger.info(f"Generating buildings at commit {target_commit_sha[:8]}")
        
        self.buildings = {}
        
        # Determine which files exist at target commit
        existing_files: Set[str] = set()
        for commit in commits:
            for change in commit.files_changed:
                if change.change_type in [ChangeType.ADDED, ChangeType.MODIFIED]:
                    existing_files.add(change.path)
                elif change.change_type == ChangeType.DELETED:
                    existing_files.discard(change.path)
                elif change.change_type == ChangeType.RENAMED:
                    if change.old_path:
                        existing_files.discard(change.old_path)
                    existing_files.add(change.path)
        
        # Generate buildings only for existing files
        for neighborhood in neighborhoods.values():
            neighborhood_pos = self.neighborhood_positions.get(
                neighborhood.path,
                (0, 0)
            )
            
            files = sorted([f for f in neighborhood.files if f in existing_files])
            for i, file_path in enumerate(files):
                if file_path in self.file_metrics:
                    building = self._create_building(
                        file_path,
                        neighborhood,
                        neighborhood_pos,
                        i
                    )
                    self.buildings[file_path] = building
        
        self.logger.info(
            f"Generated {len(self.buildings)} buildings at commit "
            f"{target_commit_sha[:8]}"
        )
    
    def _create_building(
        self,
        file_path: str,
        neighborhood: Neighborhood,
        neighborhood_pos: Tuple[float, float],
        index: int
    ) -> Building:
        """
        Create a building for a file.
        
        Args:
            file_path: Path to file
            neighborhood: Neighborhood containing the file
            neighborhood_pos: (x, y) position of neighborhood
            index: Index of file within neighborhood (for positioning)
            
        Returns:
            Building object
        """
        metrics = self.file_metrics[file_path]
        
        # Calculate position within neighborhood
        files_per_row = math.ceil(math.sqrt(len(neighborhood.files)))
        row = index // files_per_row
        col = index % files_per_row
        
        x = neighborhood_pos[0] + col * (
            self.layout_config.base_building_size[0] + 
            self.layout_config.building_spacing
        )
        y = neighborhood_pos[1] + row * (
            self.layout_config.base_building_size[1] + 
            self.layout_config.building_spacing
        )
        z = 0  # Ground level
        
        # Calculate height based on lines of code
        lines = metrics['current_lines']
        height = self._calculate_building_height(lines)
        
        # Calculate color based on modification count (activity)
        color = self._calculate_building_color(metrics['modification_count'])
        
        return Building(
            file_path=file_path,
            position=(x, y, z),
            height=height,
            base_size=self.layout_config.base_building_size,
            color=color,
            neighborhood=neighborhood.path,
            created_at=metrics['created_at'],
            last_modified=metrics['last_modified'],
            modification_count=metrics['modification_count'],
            lines_of_code=lines
        )
    
    def _calculate_building_height(self, lines_of_code: int) -> float:
        """
        Calculate building height based on lines of code.
        
        Uses logarithmic scaling to prevent extreme heights.
        
        Args:
            lines_of_code: Number of lines in file
            
        Returns:
            Building height
        """
        if lines_of_code <= 0:
            return self.layout_config.min_building_height
        
        # Logarithmic scaling
        height = math.log(lines_of_code + 1) * 5
        
        # Clamp to min/max
        height = max(self.layout_config.min_building_height, height)
        height = min(self.layout_config.max_building_height, height)
        
        return height
    
    def _calculate_building_color(self, modification_count: int) -> Tuple[int, int, int]:
        """
        Calculate building color based on modification count.
        
        More modifications = warmer colors (red/orange)
        Fewer modifications = cooler colors (blue/green)
        
        Args:
            modification_count: Number of times file was modified
            
        Returns:
            RGB color tuple (0-255)
        """
        # Normalize modification count (0-1 scale)
        # Use logarithmic scale for better distribution
        normalized = min(1.0, math.log(modification_count + 1) / 5.0)
        
        # Interpolate between blue (cold) and red (hot)
        r = int(normalized * 255)
        g = int((1 - normalized) * 128)
        b = int((1 - normalized) * 255)
        
        return (r, g, b)
    
    def _create_city_state(
        self,
        commit: CommitInfo,
        neighborhoods: Dict[str, Neighborhood]
    ) -> CityState:
        """
        Create a CityState object from current generator state.
        
        Args:
            commit: Commit this state represents
            neighborhoods: Dictionary of Neighborhood objects
            
        Returns:
            CityState object
        """
        # Calculate statistics
        statistics = {
            'total_buildings': len(self.buildings),
            'total_neighborhoods': len(neighborhoods),
            'total_lines_of_code': sum(
                b.lines_of_code for b in self.buildings.values()
            ),
            'avg_building_height': sum(
                b.height for b in self.buildings.values()
            ) / len(self.buildings) if self.buildings else 0,
            'most_modified_files': sorted(
                [
                    {'path': b.file_path, 'modifications': b.modification_count}
                    for b in self.buildings.values()
                ],
                key=lambda x: x['modifications'],
                reverse=True
            )[:10]
        }
        
        # Create neighborhood metadata
        neighborhood_metadata = {}
        for path, neighborhood in neighborhoods.items():
            neighborhood_metadata[path] = {
                'name': neighborhood.name,
                'position': self.neighborhood_positions.get(path, (0, 0)),
                'building_count': len([
                    b for b in self.buildings.values()
                    if b.neighborhood == path
                ]),
                'total_lines': sum(
                    b.lines_of_code for b in self.buildings.values()
                    if b.neighborhood == path
                )
            }
        
        return CityState(
            commit_sha=commit.sha,
            timestamp=commit.timestamp,
            buildings=self.buildings.copy(),
            neighborhoods=neighborhood_metadata,
            layout_config=self.layout_config,
            statistics=statistics
        )
    
    def save_city_state(self, city_state: CityState, output_path: str) -> None:
        """
        Save city state to JSON file.
        
        Args:
            city_state: CityState to save
            output_path: Path to output JSON file
        """
        self.logger.info(f"Saving city state to: {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(city_state.to_dict(), f, indent=2)
        
        self.logger.info(
            f"Saved city state with {len(city_state.buildings)} buildings"
        )
    
    def load_city_state(self, input_path: str) -> CityState:
        """
        Load city state from JSON file.
        
        Args:
            input_path: Path to input JSON file
            
        Returns:
            CityState object
        """
        self.logger.info(f"Loading city state from: {input_path}")
        
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        city_state = CityState.from_dict(data)
        
        self.logger.info(
            f"Loaded city state with {len(city_state.buildings)} buildings"
        )
        
        return city_state


# Made with Bob