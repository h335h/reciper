"""
AST caching module for Reciper static analyzer.

This module provides caching of parsed ASTs to avoid re-parsing unchanged files,
significantly improving performance for large projects.
"""

import ast
import hashlib
import json
import os
import pickle
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from reciper.utils import ensure_directory


class ASTCache:
    """Cache for parsed ASTs to avoid redundant parsing of unchanged files."""

    def __init__(self, cache_dir: Optional[str | Path] = None, max_size: int = 1000):
        """
        Initialize AST cache.

        Args:
            cache_dir: Directory to store cache files. Defaults to `.reciper_cache`
                       in the current working directory.
            max_size: Maximum number of ASTs to keep in memory cache.
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".reciper_cache"
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        
        # In-memory cache: OrderedDict for LRU eviction
        self.memory_cache: OrderedDict[str, Any] = OrderedDict()
        
        # Disk cache directory for persistent storage
        self.disk_cache_dir = self.cache_dir / "ast_cache"
        ensure_directory(self.disk_cache_dir)
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.disk_hits = 0
        self._load_cache_metadata()

    def _compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of file content.
        
        Args:
            content: File content as string
            
        Returns:
            Hex digest of the hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_cache_key(self, file_path: Path, content_hash: str) -> str:
        """
        Generate cache key for a file.
        
        Args:
            file_path: Path to the file
            content_hash: Hash of file content
            
        Returns:
            Cache key string
        """
        # Use a combination of file path and content hash
        # Normalize path to handle symlinks and relative paths
        normalized_path = str(file_path.resolve())
        return f"{normalized_path}:{content_hash}"

    def _get_disk_cache_path(self, cache_key: str) -> Path:
        """
        Get disk cache file path for a cache key.
        
        Args:
            cache_key: Cache key string
            
        Returns:
            Path to disk cache file
        """
        # Use hash of cache key as filename to avoid filesystem path issues
        key_hash = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
        return self.disk_cache_dir / f"{key_hash}.pkl"

    def _save_to_disk(self, cache_key: str, ast_data: Any) -> None:
        """
        Save AST data to disk cache.
        
        Args:
            cache_key: Cache key
            ast_data: AST data to cache
        """
        cache_file = self._get_disk_cache_path(cache_key)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(ast_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except (IOError, pickle.PickleError) as e:
            print(f"Warning: Failed to save cache to disk: {e}", file=sys.stderr)

    def _load_from_disk(self, cache_key: str) -> Optional[Any]:
        """
        Load AST data from disk cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached AST data or None if not found or error
        """
        cache_file = self._get_disk_cache_path(cache_key)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.PickleError, EOFError) as e:
            print(f"Warning: Failed to load cache from disk: {e}", file=sys.stderr)
            # Remove corrupted cache file
            try:
                cache_file.unlink()
            except OSError:
                pass
            return None

    def _load_cache_metadata(self) -> None:
        """Load cache metadata from disk."""
        metadata_file = self.cache_dir / "cache_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.hits = metadata.get('hits', 0)
                    self.misses = metadata.get('misses', 0)
                    self.disk_hits = metadata.get('disk_hits', 0)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_cache_metadata(self) -> None:
        """Save cache metadata to disk."""
        metadata_file = self.cache_dir / "cache_metadata.json"
        metadata = {
            'hits': self.hits,
            'misses': self.misses,
            'disk_hits': self.disk_hits,
            'cache_size': len(self.memory_cache),
        }
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
        except IOError:
            pass

    def get_ast(self, file_path: Path, content: Optional[str] = None) -> Optional[ast.AST]:
        """
        Get cached AST for a file, parsing if not cached.
        
        Args:
            file_path: Path to the Python file
            content: File content (optional). If not provided, read from file.
            
        Returns:
            Parsed AST or None if parsing fails
        """
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError) as e:
                print(f"Warning: Failed to read file {file_path}: {e}", file=sys.stderr)
                return None
        
        # Compute content hash
        content_hash = self._compute_hash(content)
        cache_key = self._get_cache_key(file_path, content_hash)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.hits += 1
            # Move to end (most recently used)
            self.memory_cache.move_to_end(cache_key)
            return self.memory_cache[cache_key]
        
        # Check disk cache
        disk_data = self._load_from_disk(cache_key)
        if disk_data is not None:
            self.disk_hits += 1
            self.hits += 1
            # Store in memory cache
            self._store_in_memory(cache_key, disk_data)
            return disk_data
        
        # Parse and cache
        self.misses += 1
        try:
            ast_data = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
            return None
        
        # Store in caches
        self._store_in_memory(cache_key, ast_data)
        self._save_to_disk(cache_key, ast_data)
        
        return ast_data

    def _store_in_memory(self, cache_key: str, ast_data: Any) -> None:
        """
        Store AST data in memory cache with LRU eviction.
        
        Args:
            cache_key: Cache key
            ast_data: AST data to cache
        """
        self.memory_cache[cache_key] = ast_data
        self.memory_cache.move_to_end(cache_key)
        
        # Evict if cache is too large
        if len(self.memory_cache) > self.max_size:
            self.memory_cache.popitem(last=False)

    def get_imports(self, file_path: Path, content: Optional[str] = None) -> Optional[list[str]]:
        """
        Get cached imports for a file.
        
        This is a convenience method that extracts imports from cached AST.
        
        Args:
            file_path: Path to the Python file
            content: File content (optional)
            
        Returns:
            List of package names or None if parsing fails
        """
        ast_data = self.get_ast(file_path, content)
        if ast_data is None:
            return None
        
        packages = set()
        for node in ast.walk(ast_data):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    package = alias.name.split(".")[0]
                    packages.add(package)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None and node.level == 0:
                    package = node.module.split(".")[0]
                    packages.add(package)
        
        return sorted(packages)

    def clear(self, memory_only: bool = False) -> None:
        """
        Clear cache.
        
        Args:
            memory_only: If True, only clear memory cache, not disk cache
        """
        self.memory_cache.clear()
        self.hits = 0
        self.misses = 0
        self.disk_hits = 0
        
        if not memory_only:
            # Clear disk cache
            for cache_file in self.disk_cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
            
            # Clear metadata
            metadata_file = self.cache_dir / "cache_metadata.json"
            if metadata_file.exists():
                try:
                    metadata_file.unlink()
                except OSError:
                    pass
        
        self._save_cache_metadata()

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        memory_hits = self.hits - self.disk_hits
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'disk_hits': self.disk_hits,
            'memory_hits': memory_hits,
            'total_requests': total,
            'hit_rate': hit_rate,
            'memory_cache_size': len(self.memory_cache),
            'disk_cache_size': len(list(self.disk_cache_dir.glob("*.pkl"))),
        }

    def __del__(self) -> None:
        """Save metadata when cache is destroyed."""
        self._save_cache_metadata()


# Global cache instance for convenience
_global_cache: Optional[ASTCache] = None

def get_global_cache() -> ASTCache:
    """Get or create global AST cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ASTCache()
    return _global_cache

def clear_global_cache(memory_only: bool = False) -> None:
    """Clear global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear(memory_only)