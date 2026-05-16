"""Repository ingestion module - handles git repository parsing and history extraction."""

from .repository_ingester import RepositoryIngester
from .commit_parser import CommitParser, CommitInfo, FileChange, ChangeType
from .file_grouper import FileGrouper, Neighborhood, FileLocation

__all__ = [
    "RepositoryIngester",
    "CommitParser",
    "CommitInfo",
    "FileChange",
    "ChangeType",
    "FileGrouper",
    "Neighborhood",
    "FileLocation",
]

# Made with Bob
