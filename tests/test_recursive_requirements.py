#!/usr/bin/env python3
"""
Test script for recursive requirements.txt parsing.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the reciper module to path
sys.path.insert(0, str(Path(__file__).parent))

from reciper.requirements_parser import parse_requirements_file, parse_requirements_line


def test_recursive_requirements():
    """Test recursive requirements parsing with -r flag."""
    print("\n" + "=" * 60)
    print("TEST: Recursive Requirements Parsing")
    print("=" * 60)
    
    # Create a temporary directory
    test_dir = Path(tempfile.mkdtemp(prefix="wac_recursive_test_"))
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create base requirements.txt with -r reference
        base_req = test_dir / "requirements.txt"
        base_req.write_text("""# Base requirements
numpy==1.21.0
-r dev-requirements.txt
pandas>=1.3.0
""")
        
        # Create referenced requirements file
        dev_req = test_dir / "dev-requirements.txt"
        dev_req.write_text("""# Development requirements
pytest>=6.0
black>=21.0
""")
        
        # Parse the base requirements file
        print(f"\nParsing {base_req}...")
        requirements = parse_requirements_file(base_req)
        
        # Check results
        package_names = [req.name for req in requirements]
        print(f"Found {len(requirements)} package requirements:")
        for req in requirements:
            print(f"  - {req.name}: {req.version_constraint or 'no version'}")
        
        # Expected packages: numpy, pytest, black, pandas
        expected = {"numpy", "pytest", "black", "pandas"}
        actual = set(package_names)
        
        missing = expected - actual
        extra = actual - expected
        
        if missing:
            print(f"\n✗ Missing expected packages: {missing}")
            return False
        if extra:
            print(f"\n✗ Unexpected packages found: {extra}")
            return False
            
        print("\n✓ Recursive requirements test passed!")
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


def test_editable_install():
    """Test handling of editable installs with -e flag."""
    print("\n" + "=" * 60)
    print("TEST: Editable Installs Parsing")
    print("=" * 60)
    
    test_dir = Path(tempfile.mkdtemp(prefix="wac_editable_test_"))
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create requirements.txt with editable install
        req_file = test_dir / "requirements.txt"
        req_file.write_text("""# Requirements with editable install
numpy==1.21.0
-e ./my-package
pandas>=1.3.0
""")
        
        # Parse the requirements file
        print(f"\nParsing {req_file}...")
        requirements = parse_requirements_file(req_file)
        
        # Check results - editable installs should be skipped with warning
        package_names = [req.name for req in requirements]
        print(f"Found {len(requirements)} package requirements:")
        for req in requirements:
            print(f"  - {req.name}: {req.version_constraint or 'no version'}")
        
        # Should only find numpy and pandas (editable skipped)
        expected = {"numpy", "pandas"}
        actual = set(package_names)
        
        if actual == expected:
            print("\n✓ Editable installs handled correctly (skipped with warning)")
            return True
        else:
            print(f"\n✗ Expected {expected}, got {actual}")
            return False
            
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


def main():
    """Run all tests."""
    print("Testing Recursive Requirements and Editable Installs")
    print("=" * 80)
    
    try:
        success1 = test_recursive_requirements()
        success2 = test_editable_install()
        
        if success1 and success2:
            print("\n" + "=" * 80)
            print("ALL TESTS PASSED! ✓")
            print("=" * 80)
            return 0
        else:
            print("\n" + "=" * 80)
            print("SOME TESTS FAILED! ✗")
            print("=" * 80)
            return 1
            
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())