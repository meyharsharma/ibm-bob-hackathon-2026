"""Error handler - centralized error handling with graceful degradation."""

import sys
import traceback
from typing import Optional, Callable, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .logger import setup_logger
from .config import Config


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"           # Informational, no action needed
    WARNING = "warning"     # Warning, can continue
    ERROR = "error"         # Error, may need fallback
    CRITICAL = "critical"   # Critical, cannot continue


class ErrorCategory(Enum):
    """Error categories for better handling."""
    NETWORK = "network"           # Network/API errors
    FILE_IO = "file_io"          # File system errors
    PARSING = "parsing"          # Data parsing errors
    VALIDATION = "validation"    # Validation errors
    RENDERING = "rendering"      # Rendering errors
    NARRATION = "narration"      # Narration generation errors
    CONFIGURATION = "configuration"  # Configuration errors
    UNKNOWN = "unknown"          # Unknown errors


@dataclass
class ErrorContext:
    """
    Context information for an error.
    
    Attributes:
        category: Error category
        severity: Error severity level
        message: User-friendly error message
        technical_details: Technical error details
        timestamp: When error occurred
        component: Which component raised the error
        recoverable: Whether error is recoverable
        recovery_action: Suggested recovery action
    """
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    technical_details: Optional[str] = None
    timestamp: Optional[datetime] = None
    component: Optional[str] = None
    recoverable: bool = True
    recovery_action: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'technical_details': self.technical_details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'component': self.component,
            'recoverable': self.recoverable,
            'recovery_action': self.recovery_action
        }


class ErrorHandler:
    """
    Centralized error handling with graceful degradation.
    
    This class provides a unified approach to error handling across
    the application. It categorizes errors, determines severity,
    implements graceful degradation strategies, and provides
    user-friendly error messages.
    
    Features:
    - Centralized error handling
    - Error categorization and severity levels
    - Graceful degradation strategies
    - User-friendly error messages
    - Error logging and tracking
    - Recovery mechanisms
    - Callback support for UI updates
    
    Architecture:
    - Categorizes errors by type
    - Determines appropriate severity
    - Implements fallback strategies
    - Logs errors with context
    - Notifies registered callbacks
    - Tracks error history
    
    Graceful Degradation Strategies:
    - Network errors: Use cached/offline data
    - Parsing errors: Skip invalid data, continue with valid
    - Rendering errors: Use simplified rendering
    - Narration errors: Continue without narration
    - File I/O errors: Use in-memory fallback
    
    Example:
        ```python
        handler = ErrorHandler()
        
        # Handle an error
        try:
            risky_operation()
        except Exception as e:
            context = handler.handle_error(
                e,
                category=ErrorCategory.NETWORK,
                component="api_client"
            )
            
            if context.recoverable:
                # Use fallback strategy
                use_cached_data()
        
        # Register callback for UI updates
        handler.on_error(lambda ctx: update_ui(ctx.message))
        ```
    """
    
    def __init__(self, enable_graceful_degradation: bool = True):
        """
        Initialize the error handler.
        
        Args:
            enable_graceful_degradation: Whether to enable graceful degradation
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.enable_graceful_degradation = enable_graceful_degradation
        
        # Error tracking
        self._error_history: List[ErrorContext] = []
        self._error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        
        # Callbacks
        self._error_callbacks: List[Callable[[ErrorContext], None]] = []
        
        self.logger.info(
            f"Initialized ErrorHandler (graceful_degradation={enable_graceful_degradation})"
        )
    
    def handle_error(
        self,
        error: Exception,
        category: Optional[ErrorCategory] = None,
        component: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> ErrorContext:
        """
        Handle an error with appropriate strategy.
        
        Args:
            error: The exception that occurred
            category: Error category (auto-detected if None)
            component: Component where error occurred
            user_message: Custom user-friendly message
            
        Returns:
            ErrorContext with error details and recovery info
        """
        # Auto-detect category if not provided
        if category is None:
            category = self._detect_category(error)
        
        # Determine severity
        severity = self._determine_severity(error, category)
        
        # Create user-friendly message
        if user_message is None:
            user_message = self._create_user_message(error, category)
        
        # Get technical details
        technical_details = self._get_technical_details(error)
        
        # Determine if recoverable
        recoverable = self._is_recoverable(error, category, severity)
        
        # Get recovery action
        recovery_action = self._get_recovery_action(category, severity) if recoverable else None
        
        # Create error context
        context = ErrorContext(
            category=category,
            severity=severity,
            message=user_message,
            technical_details=technical_details,
            component=component,
            recoverable=recoverable,
            recovery_action=recovery_action
        )
        
        # Log error
        self._log_error(context)
        
        # Track error
        self._track_error(context)
        
        # Notify callbacks
        self._notify_callbacks(context)
        
        return context
    
    def handle_with_fallback(
        self,
        operation: Callable,
        fallback: Callable,
        category: ErrorCategory,
        component: Optional[str] = None
    ) -> Any:
        """
        Execute operation with automatic fallback on error.
        
        Args:
            operation: Primary operation to execute
            fallback: Fallback operation if primary fails
            category: Error category
            component: Component name
            
        Returns:
            Result from operation or fallback
        """
        try:
            return operation()
        except Exception as e:
            context = self.handle_error(e, category, component)
            
            if self.enable_graceful_degradation and context.recoverable:
                self.logger.info(f"Using fallback for {category.value}")
                try:
                    return fallback()
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")
                    raise
            else:
                raise
    
    def on_error(self, callback: Callable[[ErrorContext], None]) -> None:
        """
        Register callback for error notifications.
        
        Args:
            callback: Function to call when error occurs
        """
        self._error_callbacks.append(callback)
    
    def get_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: Optional[int] = None
    ) -> List[ErrorContext]:
        """
        Get error history with optional filtering.
        
        Args:
            category: Filter by category
            severity: Filter by severity
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorContext objects
        """
        errors = self._error_history
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        if limit:
            errors = errors[-limit:]
        
        return errors
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            'total_errors': len(self._error_history),
            'by_category': {
                cat.value: count
                for cat, count in self._error_counts.items()
            },
            'by_severity': {
                sev.value: len([e for e in self._error_history if e.severity == sev])
                for sev in ErrorSeverity
            },
            'recoverable_count': len([e for e in self._error_history if e.recoverable]),
            'critical_count': len([
                e for e in self._error_history
                if e.severity == ErrorSeverity.CRITICAL
            ])
        }
    
    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        self._error_counts = {cat: 0 for cat in ErrorCategory}
        self.logger.info("Cleared error history")
    
    def _detect_category(self, error: Exception) -> ErrorCategory:
        """Auto-detect error category from exception type."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Network errors
        if any(term in error_type.lower() for term in ['connection', 'timeout', 'network', 'http']):
            return ErrorCategory.NETWORK
        
        # File I/O errors
        if any(term in error_type.lower() for term in ['file', 'io', 'permission', 'notfound']):
            return ErrorCategory.FILE_IO
        
        # Parsing errors
        if any(term in error_type.lower() for term in ['parse', 'json', 'xml', 'decode']):
            return ErrorCategory.PARSING
        
        # Validation errors
        if any(term in error_type.lower() for term in ['validation', 'value', 'type']):
            return ErrorCategory.VALIDATION
        
        # Check error message for hints
        if any(term in error_msg for term in ['network', 'connection', 'api']):
            return ErrorCategory.NETWORK
        
        if any(term in error_msg for term in ['file', 'directory', 'path']):
            return ErrorCategory.FILE_IO
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(
        self,
        error: Exception,
        category: ErrorCategory
    ) -> ErrorSeverity:
        """Determine error severity."""
        # Critical errors that should stop execution
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        
        # Configuration errors are usually critical
        if category == ErrorCategory.CONFIGURATION:
            return ErrorSeverity.CRITICAL
        
        # Network and narration errors can be degraded
        if category in [ErrorCategory.NETWORK, ErrorCategory.NARRATION]:
            return ErrorSeverity.WARNING
        
        # File I/O errors are usually errors but recoverable
        if category == ErrorCategory.FILE_IO:
            return ErrorSeverity.ERROR
        
        # Default to error
        return ErrorSeverity.ERROR
    
    def _create_user_message(
        self,
        error: Exception,
        category: ErrorCategory
    ) -> str:
        """Create user-friendly error message."""
        messages = {
            ErrorCategory.NETWORK: "Network connection issue. Using offline mode.",
            ErrorCategory.FILE_IO: "File access issue. Using alternative data source.",
            ErrorCategory.PARSING: "Data format issue. Skipping invalid data.",
            ErrorCategory.VALIDATION: "Invalid data detected. Using defaults.",
            ErrorCategory.RENDERING: "Rendering issue. Using simplified view.",
            ErrorCategory.NARRATION: "Narration unavailable. Continuing without audio.",
            ErrorCategory.CONFIGURATION: "Configuration error. Please check settings.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred."
        }
        
        base_message = messages.get(category, messages[ErrorCategory.UNKNOWN])
        
        # Add specific error info if helpful
        error_str = str(error)
        if error_str and len(error_str) < 100:
            return f"{base_message} ({error_str})"
        
        return base_message
    
    def _get_technical_details(self, error: Exception) -> str:
        """Get technical error details."""
        return ''.join(traceback.format_exception(
            type(error),
            error,
            error.__traceback__
        ))
    
    def _is_recoverable(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity
    ) -> bool:
        """Determine if error is recoverable."""
        if not self.enable_graceful_degradation:
            return False
        
        # Critical errors are not recoverable
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        # System errors are not recoverable
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            return False
        
        # Most other errors are recoverable with degradation
        return True
    
    def _get_recovery_action(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity
    ) -> str:
        """Get suggested recovery action."""
        actions = {
            ErrorCategory.NETWORK: "Using cached data or offline mode",
            ErrorCategory.FILE_IO: "Using in-memory data or alternative source",
            ErrorCategory.PARSING: "Skipping invalid data and continuing",
            ErrorCategory.VALIDATION: "Using default values",
            ErrorCategory.RENDERING: "Using simplified rendering",
            ErrorCategory.NARRATION: "Continuing without narration",
        }
        
        return actions.get(category, "Attempting to continue with degraded functionality")
    
    def _log_error(self, context: ErrorContext) -> None:
        """Log error with appropriate level."""
        log_message = f"[{context.category.value}] {context.message}"
        
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
            if context.technical_details:
                self.logger.critical(f"Technical details:\n{context.technical_details}")
        elif context.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message)
            if context.technical_details:
                self.logger.debug(f"Technical details:\n{context.technical_details}")
        elif context.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _track_error(self, context: ErrorContext) -> None:
        """Track error in history."""
        self._error_history.append(context)
        self._error_counts[context.category] += 1
    
    def _notify_callbacks(self, context: ErrorContext) -> None:
        """Notify all registered callbacks."""
        for callback in self._error_callbacks:
            try:
                callback(context)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")


# Global error handler instance
_global_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Get global error handler instance.
    
    Returns:
        Global ErrorHandler instance
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def handle_error(
    error: Exception,
    category: Optional[ErrorCategory] = None,
    component: Optional[str] = None,
    user_message: Optional[str] = None
) -> ErrorContext:
    """
    Convenience function to handle error with global handler.
    
    Args:
        error: The exception that occurred
        category: Error category
        component: Component where error occurred
        user_message: Custom user-friendly message
        
    Returns:
        ErrorContext with error details
    """
    return get_error_handler().handle_error(error, category, component, user_message)


# Made with Bob