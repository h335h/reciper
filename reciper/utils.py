"""Utility functions for Reciper"""

import hashlib
import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if it doesn't."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def print_error(message: str) -> None:
    """Print error message in red (if supported)."""
    print(f"\033[91mError: {message}\033[0m")


def print_success(message: str) -> None:
    """Print success message in green (if supported)."""
    print(f"\033[92m{message}\033[0m")


def print_warning(message: str) -> None:
    """Print warning message in yellow (if supported)."""
    print(f"\033[93mWarning: {message}\033[0m")


def file_cache(maxsize: int = 128):
    """
    Decorator for caching function results based on file path and modification time.

    Args:
        maxsize: Maximum number of cached results to keep

    The cache key is (file_path, modification_time, file_size).
    Only works for functions where the first argument is a file path.
    """
    cache: dict[tuple, Any] = {}

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(file_path: str, *args, **kwargs):
            try:
                # Get file stats for cache key
                stat = os.stat(file_path)
                key = (file_path, stat.st_mtime, stat.st_size)

                # Check cache
                if key in cache:
                    return cache[key]

                # Call function and cache result
                result = func(file_path, *args, **kwargs)
                cache[key] = result

                # Limit cache size (LRU-like eviction)
                if len(cache) > maxsize:
                    # Remove oldest entry (simplified)
                    cache.pop(next(iter(cache)))

                return result
            except (OSError, FileNotFoundError):
                # If we can't stat the file, don't cache
                return func(file_path, *args, **kwargs)

        return wrapper

    return decorator


def get_file_hash(file_path: str, algorithm: str = "md5") -> str | None:
    """
    Compute hash of file content for caching purposes.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest of file hash, or None if file cannot be read
    """
    try:
        hasher = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, FileNotFoundError):
        return None


# ============================================================================
# Performance Monitoring Utilities (Phase 9)
# ============================================================================

import time
import functools
import sys
from typing import Callable, Any, Optional
import threading
import gc


def timeit(func: Callable) -> Callable:
    """
    Decorator to measure execution time of a function.
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function that prints execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"[PERF] {func.__name__} took {elapsed_ms:.2f} ms")
        return result
    return wrapper


def timeit_verbose(threshold_ms: float = 100.0) -> Callable:
    """
    Decorator factory to measure execution time and warn if it exceeds threshold.
    
    Args:
        threshold_ms: Threshold in milliseconds above which to print a warning
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            
            if elapsed_ms > threshold_ms:
                print(f"[PERF WARNING] {func.__name__} took {elapsed_ms:.2f} ms "
                      f"(threshold: {threshold_ms} ms)")
            return result
        return wrapper
    return decorator


class PerformanceTimer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = "Block", verbose: bool = True):
        self.name = name
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
        
        if self.verbose:
            print(f"[TIMER] {self.name}: {self.elapsed_ms:.2f} ms")
            
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000


def get_memory_usage() -> Optional[float]:
    """
    Get current memory usage in MB.
    
    Returns:
        Memory usage in MB, or None if psutil is not available
    """
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except ImportError:
        return None


class MemoryMonitor:
    """Monitor memory usage changes within a context."""
    
    def __init__(self, name: str = "MemoryMonitor", verbose: bool = True):
        self.name = name
        self.verbose = verbose
        self.start_memory = None
        self.end_memory = None
        
    def __enter__(self):
        self.start_memory = get_memory_usage()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_memory = get_memory_usage()
        
        if self.verbose and self.start_memory is not None and self.end_memory is not None:
            diff = self.end_memory - self.start_memory
            print(f"[MEMORY] {self.name}: {self.start_memory:.1f} MB -> "
                  f"{self.end_memory:.1f} MB (Δ {diff:+.1f} MB)")
            
    def get_memory_diff(self) -> Optional[float]:
        """Get memory difference in MB."""
        if self.start_memory is None or self.end_memory is None:
            return None
        return self.end_memory - self.start_memory


def profile_function(func: Callable, *args, **kwargs) -> dict[str, Any]:
    """
    Profile a function's execution time and memory usage.
    
    Args:
        func: Function to profile
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function
        
    Returns:
        Dictionary with profiling results
    """
    start_time = time.perf_counter()
    start_memory = get_memory_usage()
    
    result = func(*args, **kwargs)
    
    end_time = time.perf_counter()
    end_memory = get_memory_usage()
    
    elapsed_ms = (end_time - start_time) * 1000
    memory_diff = None
    if start_memory is not None and end_memory is not None:
        memory_diff = end_memory - start_memory
    
    return {
        'function': func.__name__,
        'elapsed_ms': elapsed_ms,
        'start_memory_mb': start_memory,
        'end_memory_mb': end_memory,
        'memory_diff_mb': memory_diff,
        'result': result,
    }


def enable_gc_before_call(func: Callable) -> Callable:
    """
    Decorator to run garbage collection before function call.
    
    Useful for memory-intensive operations.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()  # Run garbage collection before function
        return func(*args, **kwargs)
    return wrapper
