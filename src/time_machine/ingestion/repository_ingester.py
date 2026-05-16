"""Repository ingestion - handles git repository parsing and validation."""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse
import git
from git import Repo, InvalidGitRepositoryError, GitCommandError

from ..utils.config import Config
from ..utils.logger import setup_logger


class RepositoryIngestionError(Exception):
    """Custom exception for repository ingestion errors."""
    pass


class RepositoryIngester:
    """
    Handles ingestion of git repositories for visualization.
    
    Accepts local paths or remote URLs, validates repositories,
    and prepares them for processing.
    """
    
    def __init__(self):
        """Initialize the repository ingester."""
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.repositories_dir = Config.REPOSITORIES_DIR
        self.repositories_dir.mkdir(parents=True, exist_ok=True)
    
    def ingest(
        self,
        repository: str,
        name: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest a git repository for visualization.
        
        Args:
            repository: Path to local repository or remote URL
            name: Custom name for the repository (auto-detected if not provided)
            force: If True, overwrite existing repository
            
        Returns:
            Dictionary with ingestion results:
                - name: Repository name
                - path: Path to ingested repository
                - commit_count: Number of commits
                - file_count: Number of files in HEAD
                - is_remote: Whether repository was cloned from remote
                
        Raises:
            RepositoryIngestionError: If repository cannot be ingested
            
        Acceptance Criteria:
            - AC-01.1: System accepts repository identifier from user ✓
            - AC-01.2: Clear error reporting if repository cannot be read ✓
            - AC-01.3: Progress reporting during ingestion ✓
        """
        self.logger.info(f"Starting ingestion of repository: {repository}")
        
        try:
            # Determine if repository is local or remote
            is_remote = self._is_remote_url(repository)
            
            if is_remote:
                self.logger.info("Detected remote repository URL")
                return self._ingest_remote(repository, name, force)
            else:
                self.logger.info("Detected local repository path")
                return self._ingest_local(repository, name, force)
                
        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository: {repository}. Error: {str(e)}"
            self.logger.error(error_msg)
            raise RepositoryIngestionError(error_msg) from e
            
        except GitCommandError as e:
            error_msg = f"Git command failed for repository: {repository}. Error: {str(e)}"
            self.logger.error(error_msg)
            raise RepositoryIngestionError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error ingesting repository: {repository}. Error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise RepositoryIngestionError(error_msg) from e
    
    def _is_remote_url(self, repository: str) -> bool:
        """
        Check if repository string is a remote URL.
        
        Args:
            repository: Repository identifier
            
        Returns:
            True if remote URL, False if local path
        """
        # Check for common URL schemes
        if repository.startswith(('http://', 'https://', 'git://', 'ssh://', 'git@')):
            return True
        
        # Check if it's a valid URL
        try:
            result = urlparse(repository)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
    
    def _ingest_local(
        self,
        repository_path: str,
        name: Optional[str],
        force: bool
    ) -> Dict[str, Any]:
        """
        Ingest a local git repository.
        
        Args:
            repository_path: Path to local repository
            name: Custom repository name
            force: Overwrite if exists
            
        Returns:
            Ingestion results dictionary
        """
        repo_path = Path(repository_path).resolve()
        
        # Validate repository exists
        if not repo_path.exists():
            raise RepositoryIngestionError(f"Repository path does not exist: {repo_path}")
        
        if not repo_path.is_dir():
            raise RepositoryIngestionError(f"Repository path is not a directory: {repo_path}")
        
        self.logger.info(f"Validating local repository at: {repo_path}")
        
        # Validate it's a git repository
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            raise RepositoryIngestionError(
                f"Path is not a valid git repository: {repo_path}. "
                "Make sure the directory contains a .git folder."
            )
        
        # Determine repository name
        if name is None:
            name = repo_path.name
        
        # Sanitize name
        name = self._sanitize_name(name)
        
        target_path = self.repositories_dir / name
        
        # Check if repository already exists
        if target_path.exists() and not force:
            raise RepositoryIngestionError(
                f"Repository '{name}' already exists. Use force=True to overwrite."
            )
        
        self.logger.info(f"Copying repository to: {target_path}")
        
        # Copy repository to data directory
        if target_path.exists():
            shutil.rmtree(target_path)
        
        shutil.copytree(repo_path, target_path, symlinks=False)
        
        # Get repository statistics
        repo = Repo(target_path)
        stats = self._get_repository_stats(repo)
        
        self.logger.info(
            f"Successfully ingested local repository '{name}': "
            f"{stats['commit_count']} commits, {stats['file_count']} files"
        )
        
        return {
            'name': name,
            'path': str(target_path),
            'commit_count': stats['commit_count'],
            'file_count': stats['file_count'],
            'is_remote': False,
            'original_path': str(repo_path)
        }
    
    def _ingest_remote(
        self,
        repository_url: str,
        name: Optional[str],
        force: bool
    ) -> Dict[str, Any]:
        """
        Ingest a remote git repository by cloning.
        
        Args:
            repository_url: Remote repository URL
            name: Custom repository name
            force: Overwrite if exists
            
        Returns:
            Ingestion results dictionary
        """
        # Determine repository name from URL if not provided
        if name is None:
            name = self._extract_name_from_url(repository_url)
        
        # Sanitize name
        name = self._sanitize_name(name)
        
        target_path = self.repositories_dir / name
        
        # Check if repository already exists
        if target_path.exists() and not force:
            raise RepositoryIngestionError(
                f"Repository '{name}' already exists. Use force=True to overwrite."
            )
        
        self.logger.info(f"Cloning remote repository to: {target_path}")
        self.logger.info("This may take a while for large repositories...")
        
        # Remove existing directory if force is True
        if target_path.exists():
            shutil.rmtree(target_path)
        
        # Clone repository with progress reporting
        try:
            class ProgressPrinter(git.RemoteProgress):
                def __init__(self, logger):
                    super().__init__()
                    self.logger = logger
                    
                def update(self, op_code, cur_count, max_count=None, message=''):
                    if max_count:
                        percentage = (cur_count / max_count) * 100
                        self.logger.info(
                            f"Cloning progress: {percentage:.1f}% "
                            f"({cur_count}/{max_count}) {message}"
                        )
            
            repo = Repo.clone_from(
                repository_url,
                target_path,
                progress=ProgressPrinter(self.logger)
            )
            
        except GitCommandError as e:
            raise RepositoryIngestionError(
                f"Failed to clone repository from {repository_url}. "
                f"Error: {str(e)}"
            ) from e
        
        # Get repository statistics
        stats = self._get_repository_stats(repo)
        
        self.logger.info(
            f"Successfully cloned remote repository '{name}': "
            f"{stats['commit_count']} commits, {stats['file_count']} files"
        )
        
        return {
            'name': name,
            'path': str(target_path),
            'commit_count': stats['commit_count'],
            'file_count': stats['file_count'],
            'is_remote': True,
            'remote_url': repository_url
        }
    
    def _extract_name_from_url(self, url: str) -> str:
        """
        Extract repository name from URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Repository name
        """
        # Handle git@github.com:user/repo.git format
        if url.startswith('git@'):
            name = url.split(':')[-1]
        else:
            # Handle https://github.com/user/repo.git format
            name = url.rstrip('/').split('/')[-1]
        
        # Remove .git extension if present
        if name.endswith('.git'):
            name = name[:-4]
        
        return name
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize repository name for use as directory name.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        name = name.strip('. ')
        
        # Ensure name is not empty
        if not name:
            name = 'repository'
        
        return name
    
    def _get_repository_stats(self, repo: Repo) -> Dict[str, int]:
        """
        Get basic statistics about a repository.
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            Dictionary with commit_count and file_count
        """
        # Count commits
        try:
            commit_count = sum(1 for _ in repo.iter_commits())
        except Exception as e:
            self.logger.warning(f"Could not count commits: {e}")
            commit_count = 0
        
        # Count files in HEAD
        try:
            head_tree = repo.head.commit.tree
            file_count = sum(1 for _ in head_tree.traverse() if _.type == 'blob')
        except Exception as e:
            self.logger.warning(f"Could not count files: {e}")
            file_count = 0
        
        return {
            'commit_count': commit_count,
            'file_count': file_count
        }
    
    def list_repositories(self) -> list[Dict[str, str]]:
        """
        List all ingested repositories.
        
        Returns:
            List of dictionaries with repository information
        """
        repositories = []
        
        if not self.repositories_dir.exists():
            return repositories
        
        for repo_dir in self.repositories_dir.iterdir():
            if repo_dir.is_dir():
                try:
                    repo = Repo(repo_dir)
                    stats = self._get_repository_stats(repo)
                    
                    repositories.append({
                        'name': repo_dir.name,
                        'path': str(repo_dir),
                        'commit_count': stats['commit_count'],
                        'file_count': stats['file_count']
                    })
                except Exception as e:
                    self.logger.warning(
                        f"Could not read repository {repo_dir.name}: {e}"
                    )
        
        return repositories

# Made with Bob
