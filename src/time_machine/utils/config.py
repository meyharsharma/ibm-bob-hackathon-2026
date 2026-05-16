"""Configuration management for The Time Machine."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    REPOSITORIES_DIR = DATA_DIR / "repositories"
    CACHE_DIR = DATA_DIR / "cache"
    NARRATION_DIR = DATA_DIR / "narration"

    # IBM Watson/Bob Configuration
    IBM_WATSON_API_KEY: Optional[str] = os.getenv("IBM_WATSON_API_KEY")
    IBM_WATSON_URL: Optional[str] = os.getenv("IBM_WATSON_URL")
    IBM_WATSON_ASSISTANT_ID: Optional[str] = os.getenv("IBM_WATSON_ASSISTANT_ID")

    # Flask Configuration
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

    # Repository Configuration
    MAX_COMMITS: int = int(os.getenv("MAX_COMMITS", "10000"))
    MAX_FILES: int = int(os.getenv("MAX_FILES", "5000"))
    DEFAULT_PLAYBACK_DURATION: int = int(os.getenv("DEFAULT_PLAYBACK_DURATION", "90"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "time_machine.log")

    # Cache Configuration
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() == "true"

    # Narration Configuration
    ENABLE_OFFLINE_MODE: bool = os.getenv("ENABLE_OFFLINE_MODE", "False").lower() == "true"

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        for directory in [cls.DATA_DIR, cls.REPOSITORIES_DIR, cls.CACHE_DIR, cls.NARRATION_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.ENABLE_OFFLINE_MODE:
            if not cls.IBM_WATSON_API_KEY:
                raise ValueError("IBM_WATSON_API_KEY is required when offline mode is disabled")
            if not cls.IBM_WATSON_URL:
                raise ValueError("IBM_WATSON_URL is required when offline mode is disabled")
            if not cls.IBM_WATSON_ASSISTANT_ID:
                raise ValueError("IBM_WATSON_ASSISTANT_ID is required when offline mode is disabled")
        return True

# Made with Bob
