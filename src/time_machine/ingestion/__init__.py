"""Repository ingestion module - handles git repository parsing and history extraction."""

from .repository_ingester import RepositoryIngester
from .commit_parser import CommitParser, CommitInfo, FileChange, ChangeType

__all__ = ["RepositoryIngester", "CommitParser", "CommitInfo", "FileChange", "ChangeType"]

# Made with Bob
