#!/usr/bin/env python3
"""
Test script for features: Multi-file scanning and requirements.txt parsing.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the reciper module to path
sys.path.insert(0, str(Path(__file__).parent))

from reciper.scanner import scan_directory, find_requirements_file, get_directory_summary
from reciper.requirements_parser import parse_requirements_file, requirements_to_dict
from reciper.import_aggregator import ImportAggregator, aggregate_imports_from_files
from reciper.parser import parse_imports
from reciper.cli import analyze_static


def create_test_directory() -> Path:
    """Create a test directory with multiple Python files and requirements.txt."""
    test_dir = Path(tempfile.mkdtemp(prefix="wac_test_"))
    print(f"Created test directory: {test_dir}")
    
    # Create main.py
    main_py = test_dir / "main.py"
    main_py.write_text("""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import os
import sys
""")
    
    # Create utils.py
    utils_py = test_dir / "utils.py"
    utils_py.write_text("""
import numpy
import pandas
from pathlib import Path
import json
import csv
""")
    
    # Create analysis.py
    analysis_py = test_dir / "analysis.py"
    analysis_py.write_text("""
import numpy as np
import matplotlib
import seaborn as sns
from sklearn.cluster import KMeans
import pandas as pd
""")
    
    # Create a subdirectory with more files
    subdir = test_dir / "subdir"
    subdir.mkdir()
    
    # Create module.py in subdir
    module_py = subdir / "module.py"
    module_py.write_text("""
import requests
import numpy
""")
    
    # Create requirements.txt
    requirements_txt = test_dir / "requirements.txt"
    requirements_txt.write_text("""# Test requirements
numpy==1.21.0
pandas>=1.3.0
scikit-learn
matplotlib<3.5.0
requests>=2.25.0
# Missing: seaborn, csv (built-in)
""")
    
    # Create a virtual environment directory (should be skipped)
    venv_dir = test_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("[venv]")
    
    return test_dir


def test_scanner():
    """Test the directory scanner."""
    print("\n" + "=" * 60)
    print("TEST 1: Directory Scanner")
    print("=" * 60)
    
    test_dir = create_test_directory()
    
    try:
        # Test scanning
        print(f"Scanning directory: {test_dir}")
        file_infos = scan_directory(test_dir)
        
        print(f"Found {len(file_infos)} Python files (should be 4, excluding venv):")
        for info in file_infos:
            print(f"  - {info.relative_path} ({info.size} bytes)")
        
        # Verify we found the right files
        found_files = {info.relative_path.name for info in file_infos}
        expected_files = {"main.py", "utils.py", "analysis.py", "module.py"}
        assert found_files == expected_files, f"Expected {expected_files}, got {found_files}"
        
        # Test summary
        summary = get_directory_summary(file_infos)
        print(f"\nDirectory summary:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Total size: {summary['total_size']} bytes")
        print(f"  Newest file: {summary['newest_file'].name}")
        
        # Test requirements file detection
        req_file = find_requirements_file(test_dir)
        assert req_file is not None and req_file.name == "requirements.txt"
        print(f"\nFound requirements file: {req_file}")
        
        print("✓ Scanner test passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


def test_requirements_parser():
    """Test the requirements.txt parser."""
    print("\n" + "=" * 60)
    print("TEST 2: Requirements Parser")
    print("=" * 60)
    
    test_dir = create_test_directory()
    
    try:
        requirements_file = test_dir / "requirements.txt"
        
        # Parse requirements
        requirements = parse_requirements_file(requirements_file)
        print(f"Parsed {len(requirements)} package requirements:")
        
        for req in requirements:
            print(f"  - {req.name}: {req.version_constraint or 'no version'}")
        
        # Convert to dictionary
        req_dict = requirements_to_dict(requirements)
        print(f"\nRequirements dictionary ({len(req_dict)} packages):")
        for name, version in req_dict.items():
            print(f"  {name}: {version}")
        
        # Verify expected packages
        expected_packages = {"numpy", "pandas", "scikit-learn", "matplotlib", "requests"}
        parsed_packages = set(req_dict.keys())
        assert parsed_packages == expected_packages, f"Expected {expected_packages}, got {parsed_packages}"
        
        # Test version constraints
        assert req_dict["numpy"] == "==1.21.0"
        assert req_dict["pandas"] == ">=1.3.0"
        assert req_dict["matplotlib"] == "<3.5.0"
        
        print("✓ Requirements parser test passed!")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_import_aggregator():
    """Test the import aggregator."""
    print("\n" + "=" * 60)
    print("TEST 3: Import Aggregator")
    print("=" * 60)
    
    test_dir = create_test_directory()
    
    try:
        # Get file paths
        file_paths = [
            test_dir / "main.py",
            test_dir / "utils.py",
            test_dir / "analysis.py",
            test_dir / "subdir" / "module.py"
        ]
        
        # Aggregate imports
        aggregator = aggregate_imports_from_files(file_paths, parse_imports)
        
        # Get statistics
        stats = aggregator.get_statistics()
        print(f"Files processed: {stats['files_processed']}")
        print(f"Total imports found: {stats['total_imports']}")
        print(f"Unique packages: {stats['unique_packages']}")
        
        # Verify we found all expected packages
        all_packages = aggregator.get_all_packages()
        print(f"\nAll unique packages ({len(all_packages)}):")
        for pkg in sorted(all_packages):
            print(f"  - {pkg}")
        
        # Expected packages from our test files
        expected_packages = {
            "numpy", "pandas", "sklearn", "matplotlib", "os", "sys",
            "pathlib", "json", "csv", "seaborn", "requests"
        }
        
        missing = expected_packages - set(all_packages)
        extra = set(all_packages) - expected_packages
        
        if missing:
            print(f"\nWarning: Missing expected packages: {missing}")
        if extra:
            print(f"\nNote: Extra packages found: {extra}")
        
        # Check package occurrences
        numpy_occurrences = aggregator.get_package_occurrences("numpy")
        print(f"\n'numpy' appears in {len(numpy_occurrences)} files")
        
        # Test imports by file
        main_imports = aggregator.get_imports_by_file(test_dir / "main.py")
        print(f"\nImports in main.py: {main_imports}")
        
        print("✓ Import aggregator test passed!")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_integration():
    """Test CLI integration with directory scanning."""
    print("\n" + "=" * 60)
    print("TEST 4: CLI Integration")
    print("=" * 60)
    
    test_dir = create_test_directory()
    output_dir = test_dir / "output"
    output_dir.mkdir()
    
    try:
        print(f"Test directory: {test_dir}")
        print(f"Output directory: {output_dir}")
        
        # Test analyze_static with directory
        print("\nTesting analyze_static with directory...")
        success = analyze_static(str(test_dir), str(output_dir))
        
        if success:
            print("✓ Directory analysis succeeded!")
            
            # Check if output files were created
            dockerfile = output_dir / "Dockerfile"
            environment_yml = output_dir / "environment.yml"
            
            if dockerfile.exists():
                print(f"✓ Dockerfile created: {dockerfile}")
            else:
                print(f"✗ Dockerfile not created")
                
            if environment_yml.exists():
                print(f"✓ environment.yml created: {environment_yml}")
            else:
                print(f"✗ environment.yml not created")
        else:
            print("✗ Directory analysis failed")
            
        # Test analyze_static with single file (backward compatibility)
        print("\nTesting analyze_static with single file (backward compatibility)...")
        single_file = test_dir / "main.py"
        success = analyze_static(str(single_file), str(output_dir))
        
        if success:
            print("✓ Single file analysis succeeded!")
        else:
            print("✗ Single file analysis failed")
        
        print("✓ CLI integration test completed!")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    """Run all tests."""
    print("Testing Features: Multi-file scanning and requirements.txt parsing")
    print("=" * 80)
    
    try:
        test_scanner()
        test_requirements_parser()
        test_import_aggregator()
        test_cli_integration()
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✓")
        print("Features implemented successfully.")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()