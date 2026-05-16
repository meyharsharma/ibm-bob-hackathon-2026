"""Epoch narration generator - creates narrative summaries for major time periods."""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from .bob_client import BobClient, NarrationRequest, NarrationResponse, NarrationType
from ..ingestion.commit_parser import CommitInfo, ChangeType
from ..utils.logger import setup_logger
from ..utils.config import Config


@dataclass
class Epoch:
    """
    Represents a major time period in repository history.
    
    Attributes:
        start_time: Start timestamp of epoch
        end_time: End timestamp of epoch
        commits: List of commits in this epoch
        title: Human-readable title for epoch
        significance_score: Score indicating importance (0.0-1.0)
        key_events: List of notable events in this epoch
    """
    start_time: datetime
    end_time: datetime
    commits: List[CommitInfo]
    title: str
    significance_score: float = 0.0
    key_events: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> timedelta:
        """Get duration of epoch."""
        return self.end_time - self.start_time
    
    @property
    def commit_count(self) -> int:
        """Get number of commits in epoch."""
        return len(self.commits)


@dataclass
class EpochNarration:
    """
    Narration for an epoch.
    
    Attributes:
        epoch: The epoch being narrated
        narration: Generated narration text
        highlights: Key highlights to emphasize
        metadata: Additional metadata
    """
    epoch: Epoch
    narration: str
    highlights: List[str]
    metadata: Dict[str, Any]


class EpochGenerator:
    """
    Generates narrative summaries for major epochs in repository history.
    
    This class analyzes commit history to identify significant time periods
    (epochs) and generates coherent narrative summaries using Bob/IBM Watson.
    It identifies notable events like refactors, high activity periods, dead
    periods, and large changes.
    
    Features:
    - Automatic epoch detection based on activity patterns
    - Identification of notable events (refactors, spikes, lulls)
    - Coherent story generation (not just commit lists)
    - Integration with Bob client for AI narration
    - Fallback to rule-based narration
    
    Architecture:
    - Analyzes commit patterns to segment history
    - Calculates significance scores for epochs
    - Generates context-rich prompts for Bob
    - Caches generated narrations
    
    Example:
        ```python
        generator = EpochGenerator(bob_client)
        epochs = generator.identify_epochs(commits)
        
        for epoch in epochs:
            narration = generator.generate_epoch_narration(epoch)
            print(f"{epoch.title}: {narration.narration}")
        ```
    """
    
    # Configuration
    MIN_EPOCH_DURATION_DAYS = 7  # Minimum epoch duration
    MAX_EPOCHS = 10  # Maximum number of epochs to generate
    HIGH_ACTIVITY_THRESHOLD = 10  # Commits per day for high activity
    LOW_ACTIVITY_THRESHOLD = 0.5  # Commits per day for low activity
    LARGE_CHANGE_THRESHOLD = 500  # Lines changed for "large change"
    
    def __init__(self, bob_client: Optional[BobClient] = None):
        """
        Initialize the epoch generator.
        
        Args:
            bob_client: BobClient for narration generation (creates new if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.bob_client = bob_client or BobClient()
        
        # Cache for generated narrations
        self._narration_cache: Dict[str, EpochNarration] = {}
        
        self.logger.info("Initialized EpochGenerator")
    
    def identify_epochs(self, commits: List[CommitInfo]) -> List[Epoch]:
        """
        Identify major epochs in commit history.
        
        Analyzes commit patterns to segment history into meaningful periods
        based on activity levels, time gaps, and significant events.
        
        Args:
            commits: List of CommitInfo objects (chronological order)
            
        Returns:
            List of identified Epoch objects
        """
        if not commits:
            return []
        
        self.logger.info(f"Identifying epochs from {len(commits)} commits")
        
        # Sort commits by timestamp
        sorted_commits = sorted(commits, key=lambda c: c.timestamp)
        
        # Detect natural breaks in activity
        epochs = self._segment_by_activity(sorted_commits)
        
        # Merge small epochs
        epochs = self._merge_small_epochs(epochs)
        
        # Calculate significance scores
        for epoch in epochs:
            epoch.significance_score = self._calculate_significance(epoch)
        
        # Identify key events in each epoch
        for epoch in epochs:
            epoch.key_events = self._identify_key_events(epoch)
        
        # Limit to max epochs, keeping most significant
        if len(epochs) > self.MAX_EPOCHS:
            epochs = sorted(epochs, key=lambda e: e.significance_score, reverse=True)
            epochs = epochs[:self.MAX_EPOCHS]
            epochs = sorted(epochs, key=lambda e: e.start_time)
        
        self.logger.info(f"Identified {len(epochs)} epochs")
        
        return epochs
    
    def generate_epoch_narration(
        self,
        epoch: Epoch,
        use_cache: bool = True
    ) -> EpochNarration:
        """
        Generate narration for an epoch.
        
        Args:
            epoch: Epoch to generate narration for
            use_cache: Whether to use cached narration if available
            
        Returns:
            EpochNarration with generated text
        """
        # Check cache
        cache_key = self._get_epoch_cache_key(epoch)
        if use_cache and cache_key in self._narration_cache:
            self.logger.debug(f"Using cached narration for epoch: {epoch.title}")
            return self._narration_cache[cache_key]
        
        self.logger.info(f"Generating narration for epoch: {epoch.title}")
        
        # Prepare context for Bob
        context = self._prepare_epoch_context(epoch)
        
        # Create narration request
        request = NarrationRequest(
            narration_type=NarrationType.EPOCH_SUMMARY,
            context=context,
            max_length=200
        )
        
        # Generate narration
        response = self.bob_client.generate_narration(request)
        
        # Extract highlights
        highlights = self._extract_highlights(epoch)
        
        # Create epoch narration
        narration = EpochNarration(
            epoch=epoch,
            narration=response.text,
            highlights=highlights,
            metadata={
                'success': response.success,
                'cached': response.cached,
                'significance': epoch.significance_score
            }
        )
        
        # Cache the narration
        self._narration_cache[cache_key] = narration
        
        return narration
    
    def generate_all_narrations(
        self,
        commits: List[CommitInfo]
    ) -> List[EpochNarration]:
        """
        Generate narrations for all epochs in commit history.
        
        Args:
            commits: List of CommitInfo objects
            
        Returns:
            List of EpochNarration objects
        """
        epochs = self.identify_epochs(commits)
        narrations = []
        
        for epoch in epochs:
            narration = self.generate_epoch_narration(epoch)
            narrations.append(narration)
        
        return narrations
    
    def _segment_by_activity(self, commits: List[CommitInfo]) -> List[Epoch]:
        """
        Segment commits into epochs based on activity patterns.
        
        Args:
            commits: Sorted list of commits
            
        Returns:
            List of Epoch objects
        """
        if not commits:
            return []
        
        epochs = []
        current_epoch_commits = []
        epoch_start = commits[0].timestamp
        
        for i, commit in enumerate(commits):
            current_epoch_commits.append(commit)
            
            # Check if we should start a new epoch
            should_split = False
            
            # Check time gap
            if i < len(commits) - 1:
                next_commit = commits[i + 1]
                time_gap = (next_commit.timestamp - commit.timestamp).days
                
                # Large time gap indicates epoch boundary
                if time_gap > self.MIN_EPOCH_DURATION_DAYS:
                    should_split = True
            
            # Check if we've reached the end
            if i == len(commits) - 1:
                should_split = True
            
            if should_split and current_epoch_commits:
                # Create epoch
                epoch_end = current_epoch_commits[-1].timestamp
                title = self._generate_epoch_title(
                    epoch_start,
                    epoch_end,
                    current_epoch_commits
                )
                
                epoch = Epoch(
                    start_time=epoch_start,
                    end_time=epoch_end,
                    commits=current_epoch_commits.copy(),
                    title=title
                )
                epochs.append(epoch)
                
                # Start new epoch
                current_epoch_commits = []
                if i < len(commits) - 1:
                    epoch_start = commits[i + 1].timestamp
        
        return epochs
    
    def _merge_small_epochs(self, epochs: List[Epoch]) -> List[Epoch]:
        """
        Merge epochs that are too small.
        
        Args:
            epochs: List of epochs
            
        Returns:
            List of merged epochs
        """
        if len(epochs) <= 1:
            return epochs
        
        merged = []
        i = 0
        
        while i < len(epochs):
            current = epochs[i]
            
            # Check if epoch is too small
            if current.duration.days < self.MIN_EPOCH_DURATION_DAYS and i < len(epochs) - 1:
                # Merge with next epoch
                next_epoch = epochs[i + 1]
                merged_commits = current.commits + next_epoch.commits
                
                merged_epoch = Epoch(
                    start_time=current.start_time,
                    end_time=next_epoch.end_time,
                    commits=merged_commits,
                    title=self._generate_epoch_title(
                        current.start_time,
                        next_epoch.end_time,
                        merged_commits
                    )
                )
                merged.append(merged_epoch)
                i += 2  # Skip next epoch since we merged it
            else:
                merged.append(current)
                i += 1
        
        return merged
    
    def _calculate_significance(self, epoch: Epoch) -> float:
        """
        Calculate significance score for an epoch.
        
        Args:
            epoch: Epoch to score
            
        Returns:
            Significance score (0.0-1.0)
        """
        if not epoch.commits:
            return 0.0
        
        score = 0.0
        
        # Factor 1: Activity level (0-0.3)
        days = max(1, epoch.duration.days)
        commits_per_day = len(epoch.commits) / days
        activity_score = min(0.3, commits_per_day / self.HIGH_ACTIVITY_THRESHOLD * 0.3)
        score += activity_score
        
        # Factor 2: Total changes (0-0.3)
        total_changes = sum(
            sum(f.lines_added + f.lines_deleted for f in c.files_changed)
            for c in epoch.commits
        )
        change_score = min(0.3, total_changes / (self.LARGE_CHANGE_THRESHOLD * 10) * 0.3)
        score += change_score
        
        # Factor 3: Number of files affected (0-0.2)
        unique_files = set()
        for commit in epoch.commits:
            for file_change in commit.files_changed:
                unique_files.add(file_change.path)
        file_score = min(0.2, len(unique_files) / 100 * 0.2)
        score += file_score
        
        # Factor 4: Diversity of changes (0-0.2)
        change_types = set()
        for commit in epoch.commits:
            for file_change in commit.files_changed:
                change_types.add(file_change.change_type)
        diversity_score = len(change_types) / len(ChangeType) * 0.2
        score += diversity_score
        
        return min(1.0, score)
    
    def _identify_key_events(self, epoch: Epoch) -> List[str]:
        """
        Identify key events in an epoch.
        
        Args:
            epoch: Epoch to analyze
            
        Returns:
            List of key event descriptions
        """
        events = []
        
        # Check for high activity
        days = max(1, epoch.duration.days)
        commits_per_day = len(epoch.commits) / days
        if commits_per_day >= self.HIGH_ACTIVITY_THRESHOLD:
            events.append(f"High activity period ({commits_per_day:.1f} commits/day)")
        
        # Check for large changes
        for commit in epoch.commits:
            total_changes = sum(f.lines_added + f.lines_deleted for f in commit.files_changed)
            if total_changes >= self.LARGE_CHANGE_THRESHOLD:
                events.append(f"Large change: {commit.message[:50]}...")
        
        # Check for refactors (heuristic: many files changed, similar message patterns)
        refactor_keywords = ['refactor', 'restructure', 'reorganize', 'cleanup']
        for commit in epoch.commits:
            if any(keyword in commit.message.lower() for keyword in refactor_keywords):
                if len(commit.files_changed) > 5:
                    events.append(f"Refactor: {commit.message[:50]}...")
        
        # Limit to top events
        return events[:5]
    
    def _generate_epoch_title(
        self,
        start: datetime,
        end: datetime,
        commits: List[CommitInfo]
    ) -> str:
        """
        Generate a title for an epoch.
        
        Args:
            start: Start timestamp
            end: End timestamp
            commits: Commits in epoch
            
        Returns:
            Human-readable title
        """
        # Format date range
        if start.year == end.year and start.month == end.month:
            title = start.strftime("%B %Y")
        elif start.year == end.year:
            title = f"{start.strftime('%B')} - {end.strftime('%B %Y')}"
        else:
            title = f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"
        
        return title
    
    def _prepare_epoch_context(self, epoch: Epoch) -> Dict[str, Any]:
        """
        Prepare context for epoch narration.
        
        Args:
            epoch: Epoch to prepare context for
            
        Returns:
            Context dictionary
        """
        # Summarize commits
        commit_summaries = []
        for commit in epoch.commits[:20]:  # Limit to recent commits
            commit_summaries.append({
                'message': commit.message,
                'author': commit.author,
                'timestamp': commit.timestamp.isoformat(),
                'files_changed': len(commit.files_changed)
            })
        
        # Calculate statistics
        total_changes = sum(
            sum(f.lines_added + f.lines_deleted for f in c.files_changed)
            for c in epoch.commits
        )
        
        unique_files = set()
        for commit in epoch.commits:
            for file_change in commit.files_changed:
                unique_files.add(file_change.path)
        
        return {
            'timeframe': epoch.title,
            'commits': commit_summaries,
            'total_commits': len(epoch.commits),
            'total_changes': total_changes,
            'files_affected': len(unique_files),
            'key_events': epoch.key_events,
            'significance': epoch.significance_score
        }
    
    def _extract_highlights(self, epoch: Epoch) -> List[str]:
        """
        Extract highlights from epoch.
        
        Args:
            epoch: Epoch to extract highlights from
            
        Returns:
            List of highlight strings
        """
        highlights = []
        
        # Add key events as highlights
        highlights.extend(epoch.key_events[:3])
        
        # Add commit count if significant
        if len(epoch.commits) > 50:
            highlights.append(f"{len(epoch.commits)} commits")
        
        return highlights
    
    def _get_epoch_cache_key(self, epoch: Epoch) -> str:
        """
        Generate cache key for epoch.
        
        Args:
            epoch: Epoch
            
        Returns:
            Cache key string
        """
        return f"{epoch.start_time.isoformat()}_{epoch.end_time.isoformat()}_{len(epoch.commits)}"


# Made with Bob