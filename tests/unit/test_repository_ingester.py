"""Unit tests for RepositoryIngester."""

import pytest
from pathlib import Path
import tempfile
import shutil
from git import Repo

from time_machine.ingestion.repository_ingester import (
    RepositoryIngester,
    RepositoryIngestionError
)


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo = Repo.init(temp_dir)
    
    # Create initial commit
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("Hello, World!")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def ingester(tmp_path):
    """Create a RepositoryIngester with temporary data directory."""
    # Temporarily override Config.REPOSITORIES_DIR
    from time_machine.utils.config import Config
    original_dir = Config.REPOSITORIES_DIR
    Config.REPOSITORIES_DIR = tmp_path / "repositories"
    
    ingester = RepositoryIngester()
    
    yield ingester
    
    # Restore original directory
    Config.REPOSITORIES_DIR = original_dir


class TestRepositoryIngester:
    """Test suite for RepositoryIngester."""
    
    def test_is_remote_url_http(self, ingester):
        """Test detection of HTTP URLs."""
        assert ingester._is_remote_url("https://github.com/user/repo.git")
        assert ingester._is_remote_url("http://github.com/user/repo.git")
    
    def test_is_remote_url_ssh(self, ingester):
        """Test detection of SSH URLs."""
        assert ingester._is_remote_url("git@github.com:user/repo.git")
        assert ingester._is_remote_url("ssh://git@github.com/user/repo.git")
    
    def test_is_remote_url_local(self, ingester):
        """Test detection of local paths."""
        assert not ingester._is_remote_url("/path/to/repo")
        assert not ingester._is_remote_url("./relative/path")
        assert not ingester._is_remote_url("C:\\Windows\\Path")
    
    def test_extract_name_from_url_https(self, ingester):
        """Test name extraction from HTTPS URL."""
        name = ingester._extract_name_from_url("https://github.com/user/repo.git")
        assert name == "repo"
    
    def test_extract_name_from_url_ssh(self, ingester):
        """Test name extraction from SSH URL."""
        name = ingester._extract_name_from_url("git@github.com:user/repo.git")
        assert name == "repo"
    
    def test_extract_name_from_url_no_extension(self, ingester):
        """Test name extraction from URL without .git extension."""
        name = ingester._extract_name_from_url("https://github.com/user/repo")
        assert name == "repo"
    
    def test_sanitize_name_valid(self, ingester):
        """Test sanitization of valid name."""
        assert ingester._sanitize_name("my-repo") == "my-repo"
        assert ingester._sanitize_name("my_repo") == "my_repo"
    
    def test_sanitize_name_invalid_chars(self, ingester):
        """Test sanitization removes invalid characters."""
        assert ingester._sanitize_name("my:repo") == "my_repo"
        assert ingester._sanitize_name("my/repo") == "my_repo"
        assert ingester._sanitize_name("my<repo>") == "my_repo_"
    
    def test_sanitize_name_empty(self, ingester):
        """Test sanitization of empty name."""
        assert ingester._sanitize_name("") == "repository"
        assert ingester._sanitize_name("   ") == "repository"
    
    def test_ingest_local_success(self, ingester, temp_repo):
        """Test successful ingestion of local repository."""
        result = ingester.ingest(temp_repo, name="test-repo")
        
        assert result['name'] == "test-repo"
        assert result['is_remote'] is False
        assert result['commit_count'] >= 1
        assert result['file_count'] >= 1
        assert Path(result['path']).exists()
    
    def test_ingest_local_auto_name(self, ingester, temp_repo):
        """Test ingestion with auto-detected name."""
        result = ingester.ingest(temp_repo)
        
        assert result['name'] == Path(temp_repo).name
        assert result['is_remote'] is False
    
    def test_ingest_local_nonexistent_path(self, ingester):
        """Test ingestion of nonexistent path."""
        with pytest.raises(RepositoryIngestionError, match="does not exist"):
            ingester.ingest("/nonexistent/path")
    
    def test_ingest_local_not_git_repo(self, ingester, tmp_path):
        """Test ingestion of non-git directory."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        
        with pytest.raises(RepositoryIngestionError, match="not a valid git repository"):
            ingester.ingest(str(non_repo))
    
    def test_ingest_local_duplicate_without_force(self, ingester, temp_repo):
        """Test ingestion of duplicate repository without force."""
        ingester.ingest(temp_repo, name="test-repo")
        
        with pytest.raises(RepositoryIngestionError, match="already exists"):
            ingester.ingest(temp_repo, name="test-repo")
    
    def test_ingest_local_duplicate_with_force(self, ingester, temp_repo):
        """Test ingestion of duplicate repository with force."""
        result1 = ingester.ingest(temp_repo, name="test-repo")
        result2 = ingester.ingest(temp_repo, name="test-repo", force=True)
        
        assert result1['name'] == result2['name']
        assert Path(result2['path']).exists()
    
    def test_list_repositories_empty(self, ingester):
        """Test listing repositories when none exist."""
        repos = ingester.list_repositories()
        assert repos == []
    
    def test_list_repositories_with_repos(self, ingester, temp_repo):
        """Test listing repositories after ingestion."""
        ingester.ingest(temp_repo, name="repo1")
        
        repos = ingester.list_repositories()
        assert len(repos) == 1
        assert repos[0]['name'] == "repo1"
        assert repos[0]['commit_count'] >= 1
    
    def test_get_repository_stats(self, ingester, temp_repo):
        """Test getting repository statistics."""
        repo = Repo(temp_repo)
        stats = ingester._get_repository_stats(repo)
        
        assert 'commit_count' in stats
        assert 'file_count' in stats
        assert stats['commit_count'] >= 1
        assert stats['file_count'] >= 1


class TestRepositoryIngestionErrorHandling:
    """Test error handling in repository ingestion."""
    
    def test_clear_error_message_invalid_repo(self, ingester, tmp_path):
        """Test that error messages are clear and helpful."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        
        try:
            ingester.ingest(str(non_repo))
            pytest.fail("Should have raised RepositoryIngestionError")
        except RepositoryIngestionError as e:
            error_msg = str(e)
            assert "not a valid git repository" in error_msg
            assert ".git folder" in error_msg
    
    def test_clear_error_message_nonexistent(self, ingester):
        """Test error message for nonexistent path."""
        try:
            ingester.ingest("/this/path/does/not/exist")
            pytest.fail("Should have raised RepositoryIngestionError")
        except RepositoryIngestionError as e:
            error_msg = str(e)
            assert "does not exist" in error_msg

# Made with Bob
