"""
Error handling and resilience utilities for Reciper.

Phase 9: Enhanced error handling for parallel processing and large projects.
"""

import sys
import traceback
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast
from pathlib import Path

T = TypeVar('T')


class ReciperError(Exception):
    """Base exception for Reciper errors."""
    pass


class SyntaxErrorWithContext(ReciperError):
    """Syntax error with additional context about the file."""
    
    def __init__(self, file_path: Path, line: Optional[int] = None, 
                 column: Optional[int] = None, original_error: Optional[Exception] = None):
        self.file_path = file_path
        self.line = line
        self.column = column
        self.original_error = original_error
        
        message = f"Syntax error in {file_path}"
        if line:
            message += f" at line {line}"
            if column:
                message += f", column {column}"
        
        if original_error:
            message += f": {original_error}"
            
        super().__init__(message)


class FileProcessingError(ReciperError):
    """Error processing a file."""
    
    def __init__(self, file_path: Path, operation: str, original_error: Optional[Exception] = None):
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        
        message = f"Error {operation} file {file_path}"
        if original_error:
            message += f": {original_error}"
            
        super().__init__(message)


def resilient_file_processor(max_retries: int = 2, delay: float = 0.1):
    """
    Decorator for file processing functions with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(file_path: Path, *args, **kwargs) -> T:
            import time
            
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(file_path, *args, **kwargs)
                except (OSError, PermissionError, FileNotFoundError) as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(delay)
                    else:
                        raise FileProcessingError(
                            file_path, 
                            f"processing (attempt {attempt + 1})", 
                            e
                        )
                except SyntaxError as e:
                    # Convert SyntaxError to our custom error with context
                    raise SyntaxErrorWithContext(file_path, e.lineno, e.offset, e)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(delay)
                    else:
                        raise FileProcessingError(
                            file_path,
                            f"processing (attempt {attempt + 1})",
                            e
                        )
            
            # This should never be reached, but just in case
            raise FileProcessingError(file_path, "processing", last_error)
        
        return wrapper
    return decorator


def continue_on_error(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that catches all exceptions and returns None instead of raising.
    
    Useful for parallel processing where we want to continue with other files
    even if one fails.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that returns None on error
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the error but don't raise it
            print(f"Error in {func.__name__}: {e}", file=sys.stderr)
            if len(args) > 0 and isinstance(args[0], Path):
                print(f"  File: {args[0]}", file=sys.stderr)
            return None
    
    return wrapper


class ErrorAggregator:
    """Aggregate errors from multiple file processing operations."""
    
    def __init__(self):
        self.errors: list[tuple[Path, str, Exception]] = []
        self.warnings: list[tuple[Path, str]] = []
    
    def add_error(self, file_path: Path, operation: str, error: Exception) -> None:
        """Add an error to the aggregator."""
        self.errors.append((file_path, operation, error))
    
    def add_warning(self, file_path: Path, message: str) -> None:
        """Add a warning to the aggregator."""
        self.warnings.append((file_path, message))
    
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were recorded."""
        return len(self.warnings) > 0
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of errors and warnings."""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [
                {
                    'file_path': str(file_path),
                    'operation': operation,
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
                for file_path, operation, error in self.errors
            ],
            'warnings': [
                {
                    'file_path': str(file_path),
                    'message': message
                }
                for file_path, message in self.warnings
            ]
        }
    
    def print_summary(self) -> None:
        """Print a human-readable summary of errors and warnings."""
        if not self.errors and not self.warnings:
            print("No errors or warnings.")
            return
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for i, (file_path, operation, error) in enumerate(self.errors, 1):
                print(f"  {i}. {operation} in {file_path}: {error}")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for i, (file_path, message) in enumerate(self.warnings, 1):
                print(f"  {i}. {file_path}: {message}")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging for Reciper.
    
    Args:
        verbose: Whether to enable debug logging
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger('reciper')
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    return logger


def log_errors(logger: logging.Logger):
    """
    Decorator to log errors instead of raising them.
    
    Args:
        logger: Logger instance
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return None
        
        return wrapper
    return decorator


def validate_file_path(file_path: Path, check_exists: bool = True) -> bool:
    """
    Validate a file path.
    
    Args:
        file_path: Path to validate
        check_exists: Whether to check if the file exists
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check if it's a valid path
        file_path.resolve()
        
        # Check if it exists (if requested)
        if check_exists and not file_path.exists():
            return False
        
        # Check if it's a file (not a directory)
        if check_exists and not file_path.is_file():
            return False
        
        return True
    except (OSError, ValueError):
        return False