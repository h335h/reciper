"""
AST parser module for extracting import statements from Python source files.

This module provides functionality to parse Python files and extract package names
from import statements for the static analyzer MVP.

Phase 9: Performance optimizations and integration with ASTCache.
"""

import ast
import sys
from pathlib import Path
from typing import Optional

from reciper.cache import ASTCache, get_global_cache
from reciper.utils import file_cache


def extract_imports_from_ast(tree: ast.AST) -> list[str]:
    """
    Extract package names from an AST tree efficiently.
    
    This is optimized to avoid unnecessary string operations and
    uses early returns where possible.
    
    Args:
        tree: Parsed AST tree
        
    Returns:
        Sorted list of unique package names
    """
    packages: set[str] = set()
    
    # Use ast.walk but with early filtering
    for node in ast.walk(tree):
        # Handle 'import numpy' and 'import numpy as np'
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Get first component of module name
                # alias.name is the full module name (e.g., 'numpy' or 'numpy.linalg')
                package = alias.name.split(".", 1)[0]  # Split only once for efficiency
                packages.add(package)
        
        # Handle 'from numpy import array' and 'from numpy.linalg import norm'
        elif isinstance(node, ast.ImportFrom):
            # Skip relative imports
            if node.level > 0:
                continue
                
            # Skip if module is None (relative import like 'from . import something')
            if node.module is None:
                continue
                
            # Get first component of module name
            package = node.module.split(".", 1)[0]  # Split only once for efficiency
            packages.add(package)
    
    return sorted(packages)


@file_cache(maxsize=256)
def parse_imports(file_path: str) -> list[str]:
    """
    Parse a Python file and extract all imported package names.
    
    Legacy function for backward compatibility. Uses file_cache decorator.

    Args:
        file_path: Path to the Python source file.

    Returns:
        List of unique package names found in import statements.

    Raises:
        FileNotFoundError: If the file does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        PermissionError: If the file cannot be read due to permissions.
        ValueError: If the file cannot be parsed for other reasons.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    except OSError as e:
        raise ValueError(f"Cannot read file {file_path}: {e}")

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in {file_path}: {e}")
    
    return extract_imports_from_ast(tree)


def parse_imports_with_cache(
    file_path: str | Path,
    cache: Optional[ASTCache] = None,
    use_cache: bool = True
) -> list[str]:
    """
    Parse a Python file with optional AST caching for better performance.
    
    This is the recommended function for new code.

    Args:
        file_path: Path to the Python source file
        cache: ASTCache instance (uses global cache if None)
        use_cache: Whether to use AST caching

    Returns:
        List of unique package names found in import statements.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        PermissionError: If the file cannot be read due to permissions.
        ValueError: If the file cannot be parsed for other reasons.
    """
    file_path = Path(file_path)
    
    if use_cache:
        if cache is None:
            cache = get_global_cache()
        
        # Try to get imports from cache
        imports = cache.get_imports(file_path)
        if imports is not None:
            return imports
    
    # Fall back to regular parsing
    return parse_imports(str(file_path))


if __name__ == "__main__":
    """Simple test case to verify the parser functionality."""
    import os
    import tempfile

    # Create a temporary Python file with various import patterns
    test_code = """
import numpy
import pandas as pd
from sklearn import preprocessing
from numpy.linalg import norm
import os.path
from .relative import something
from collections import defaultdict
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        test_file = f.name

    try:
        result = parse_imports(test_file)
        print(f"Test file: {test_file}")
        print(f"Extracted packages: {result}")

        expected = ["collections", "numpy", "os", "pandas", "sklearn"]
        if set(result) == set(expected):
            print("✓ Test passed: All expected packages found.")
        else:
            print(f"✗ Test failed: Expected {expected}, got {result}")
            sys.exit(1)
    finally:
        os.unlink(test_file)

    # Additional edge case: file not found
    try:
        parse_imports("/nonexistent/file.py")
        print("✗ Should have raised FileNotFoundError")
        sys.exit(1)
    except FileNotFoundError:
        print("✓ FileNotFoundError correctly raised for missing file.")

    print("All tests completed successfully.")
