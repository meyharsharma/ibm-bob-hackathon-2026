"""Utility module - common helpers and configuration."""

from .config import Config
from .logger import setup_logger
from .error_handler import (
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    get_error_handler,
    handle_error
)

__all__ = [
    "Config",
    "setup_logger",
    "ErrorHandler",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "get_error_handler",
    "handle_error"
]

# Made with Bob
