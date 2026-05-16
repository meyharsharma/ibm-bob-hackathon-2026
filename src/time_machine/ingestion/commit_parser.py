"""Commit history parser - extracts and processes git commit history."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Set, Any
from pathlib import Path
from enum import Enum
import json

from git import Repo, Commit, Diff
from git.exc import GitCommandError

from ..utils.config import Config
from ..utils.logger import setup_logger


class ChangeType(Enum):
    """Types of file changes in commits."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """Represents a change to a file in a commit."""
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None  # For renames
    lines_added: int = 0
    lines_deleted: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'path': self.path,
            'change_type': self.change_type.value,
            'old_path': self.old_path,
            'lines_added': self.lines_added,
            'lines_deleted': self.lines_deleted
        }


@dataclass
class CommitInfo:
    """Represents a git commit with metadata and changes."""
    sha: str
    author: str
    author_email: str
    timestamp: datetime
    message: str
    files_changed: List[FileChange] = field(default_factory=list)
    parent_shas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'sha': self.sha,
            'author': self.author,
            'author_email': self.author_email,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'files_changed': [fc.to_dict() for fc in self.files_changed],
            'parent_shas': self.parent_shas
        }


class CommitParser:
    """
    Parses git commit history and extracts detailed information.
    
    Handles commit metadata, file changes, and change types.
    Implements robust error handling for unparseable commits.
    """
    
    def __init__(self, repository_path: str):
        """
        Initialize the commit parser.
        
        Args:
            repository_path: Path to git repository
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.repository_path = Path(repository_path)
        self.repo = Repo(repository_path)
        self.max_commits = Config.MAX_COMMITS
    
    def parse_history(self) -> List[CommitInfo]:
        """
        Parse the full commit history of the repository.
        
        Returns:
            List of CommitInfo objects, ordered from oldest to newest
            
        Raises:
            Exception: If repository cannot be parsed
            
        Acceptance Criteria:
            - AC-02.1: Record all N commits with metadata ✓
            - AC-02.2: Track changed files and change types ✓
            - AC-02.3: Skip unparseable commits with logged warnings ✓
        """
        self.logger.info(f"Starting commit history parsing for: {self.repository_path}")
        
        commits = []
        skipped_count = 0
        processed_count = 0
        
        try:
            # Get all commits in reverse chronological order
            all_commits = list(self.repo.iter_commits())
            total_commits = len(all_commits)
            
            self.logger.info(f"Found {total_commits} commits in repository")
            
            # Check if we need to limit commits
            if total_commits > self.max_commits:
                self.logger.warning(
                    f"Repository has {total_commits} commits, "
                    f"limiting to {self.max_commits} most recent commits"
                )
                all_commits = all_commits[:self.max_commits]
            
            # Process commits (reverse to get oldest first)
            for i, commit in enumerate(reversed(all_commits)):
                try:
                    commit_info = self._parse_commit(commit)
                    commits.append(commit_info)
                    processed_count += 1
                    
                    # Progress reporting
                    if (i + 1) % 100 == 0:
                        self.logger.info(
                            f"Processed {i + 1}/{len(all_commits)} commits"
                        )
                        
                except Exception as e:
                    # AC-02.3: Skip unparseable commits with logged warnings
                    skipped_count += 1
                    self.logger.warning(
                        f"Skipping unparseable commit {commit.hexsha[:8]}: {str(e)}"
                    )
                    continue
            
            self.logger.info(
                f"Commit parsing complete: {processed_count} processed, "
                f"{skipped_count} skipped"
            )
            
            return commits
            
        except Exception as e:
            self.logger.error(f"Failed to parse commit history: {e}", exc_info=True)
            raise
    
    def _parse_commit(self, commit: Commit) -> CommitInfo:
        """
        Parse a single commit and extract all relevant information.
        
        Args:
            commit: GitPython Commit object
            
        Returns:
            CommitInfo object with parsed data
        """
        # Extract basic metadata (AC-02.1)
        commit_info = CommitInfo(
            sha=commit.hexsha,
            author=commit.author.name,
            author_email=commit.author.email,
            timestamp=datetime.fromtimestamp(commit.committed_date),
            message=commit.message.strip(),
            parent_shas=[p.hexsha for p in commit.parents]
        )
        
        # Parse file changes (AC-02.2)
        commit_info.files_changed = self._parse_file_changes(commit)
        
        return commit_info
    
    def _parse_file_changes(self, commit: Commit) -> List[FileChange]:
        """
        Parse file changes in a commit.
        
        Args:
            commit: GitPython Commit object
            
        Returns:
            List of FileChange objects
        """
        changes = []
        
        # Handle initial commit (no parents)
        if not commit.parents:
            # All files in initial commit are additions
            for item in commit.tree.traverse():
                if item.type == 'blob':  # It's a file
                    changes.append(FileChange(
                        path=item.path,
                        change_type=ChangeType.ADDED,
                        lines_added=self._count_lines(item)
                    ))
            return changes
        
        # Compare with parent commit
        parent = commit.parents[0]
        
        try:
            diffs = parent.diff(commit, create_patch=True)
            
            for diff in diffs:
                change = self._parse_diff(diff)
                if change:
                    changes.append(change)
                    
        except GitCommandError as e:
            self.logger.warning(f"Could not parse diffs for commit {commit.hexsha[:8]}: {e}")
        
        return changes
    
    def _parse_diff(self, diff: Diff) -> Optional[FileChange]:
        """
        Parse a single diff to extract file change information.
        
        Args:
            diff: GitPython Diff object
            
        Returns:
            FileChange object or None if diff cannot be parsed
        """
        try:
            # Determine change type
            if diff.new_file:
                change_type = ChangeType.ADDED
                path = diff.b_path
                old_path = None
            elif diff.deleted_file:
                change_type = ChangeType.DELETED
                path = diff.a_path
                old_path = None
            elif diff.renamed_file:
                change_type = ChangeType.RENAMED
                path = diff.b_path
                old_path = diff.a_path
            else:
                change_type = ChangeType.MODIFIED
                path = diff.b_path or diff.a_path
                old_path = None
            
            # Count line changes
            lines_added = 0
            lines_deleted = 0
            
            if diff.diff:
                diff_text = diff.diff.decode('utf-8', errors='ignore')
                for line in diff_text.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        lines_added += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        lines_deleted += 1
            
            return FileChange(
                path=path,
                change_type=change_type,
                old_path=old_path,
                lines_added=lines_added,
                lines_deleted=lines_deleted
            )
            
        except Exception as e:
            self.logger.warning(f"Could not parse diff: {e}")
            return None
    
    def _count_lines(self, blob) -> int:
        """
        Count lines in a blob (file).
        
        Args:
            blob: GitPython blob object
            
        Returns:
            Number of lines in the file
        """
        try:
            content = blob.data_stream.read().decode('utf-8', errors='ignore')
            return len(content.split('\n'))
        except Exception:
            return 0
    
    def save_history(self, output_path: str, commits: List[CommitInfo]) -> None:
        """
        Save parsed commit history to JSON file.
        
        Args:
            output_path: Path to output JSON file
            commits: List of CommitInfo objects to save
        """
        self.logger.info(f"Saving commit history to: {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'repository': str(self.repository_path),
            'commit_count': len(commits),
            'commits': [c.to_dict() for c in commits]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Saved {len(commits)} commits to {output_path}")
    
    def load_history(self, input_path: str) -> List[CommitInfo]:
        """
        Load parsed commit history from JSON file.
        
        Args:
            input_path: Path to input JSON file
            
        Returns:
            List of CommitInfo objects
        """
        self.logger.info(f"Loading commit history from: {input_path}")
        
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        commits = []
        for commit_data in data['commits']:
            # Reconstruct FileChange objects
            files_changed = [
                FileChange(
                    path=fc['path'],
                    change_type=ChangeType(fc['change_type']),
                    old_path=fc.get('old_path'),
                    lines_added=fc.get('lines_added', 0),
                    lines_deleted=fc.get('lines_deleted', 0)
                )
                for fc in commit_data['files_changed']
            ]
            
            # Reconstruct CommitInfo object
            commit = CommitInfo(
                sha=commit_data['sha'],
                author=commit_data['author'],
                author_email=commit_data['author_email'],
                timestamp=datetime.fromisoformat(commit_data['timestamp']),
                message=commit_data['message'],
                files_changed=files_changed,
                parent_shas=commit_data.get('parent_shas', [])
            )
            commits.append(commit)
        
        self.logger.info(f"Loaded {len(commits)} commits from {input_path}")
        return commits
    
    def get_statistics(self, commits: List[CommitInfo]) -> Dict[str, Any]:
        """
        Calculate statistics about the commit history.
        
        Args:
            commits: List of CommitInfo objects
            
        Returns:
            Dictionary with statistics
        """
        if not commits:
            return {
                'total_commits': 0,
                'total_files_changed': 0,
                'unique_files': 0,
                'authors': [],
                'date_range': None
            }
        
        unique_files: Set[str] = set()
        authors: Set[str] = set()
        total_files_changed = 0
        
        for commit in commits:
            authors.add(commit.author)
            total_files_changed += len(commit.files_changed)
            for change in commit.files_changed:
                unique_files.add(change.path)
        
        return {
            'total_commits': len(commits),
            'total_files_changed': total_files_changed,
            'unique_files': len(unique_files),
            'authors': sorted(list(authors)),
            'author_count': len(authors),
            'date_range': {
                'start': commits[0].timestamp.isoformat(),
                'end': commits[-1].timestamp.isoformat()
            }
        }

# Made with Bob
