# Reciper - Static analyzer for Python pipelines to generate reproducible environments

[![CI](https://github.com/githubuser/reciper/actions/workflows/ci.yml/badge.svg)](https://github.com/githubuser/reciper/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/reciper.svg)](https://pypi.org/project/reciper/)
[![Python versions](https://img.shields.io/pypi/pyversions/reciper.svg)](https://pypi.org/project/reciper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A static analyzer for generating reproducible environments from Python bioinformatics code.

## Overview

Reciper is a static analysis tool that scans Python codebases to:
- Parse import statements from Python files
- Map Python packages to their corresponding conda specifications
- Generate Dockerfile and environment.yml files for reproducible environments
- Compare detected imports with existing requirements.txt files
- Provide detailed JSON reports of the analysis

## Quick Start

### Installation

```bash
# Install from source (development mode)
pip install -e .

# Or install directly
pip install reciper
```

### Basic Usage

```bash
# Analyze a directory containing Python files
reciper analyze /path/to/project

# Analyze with JSON output to stdout
reciper analyze /path/to/project --json

# Analyze and save JSON report to file
reciper analyze /path/to/project --report-file analysis.json

# Specify output directory for generated files
reciper analyze /path/to/project --output ./generated
```

## Features

### Static Analysis
- **Directory scanning**: Recursively scans directories for Python files
- **Import parsing**: Extracts import statements from Python source code
- **Requirements comparison**: Compares detected imports with existing requirements.txt
- **Progress feedback**: Real-time progress updates during scanning
- **Performance caching**: Caches AST parsing results for faster repeated scans

### Package Mapping
- **Smart mapping**: Maps Python package names to conda package names using a comprehensive mapping database
- **Version handling**: Respects version constraints from requirements.txt when available
- **Standard library detection**: Identifies Python standard library modules that don't require installation

### Requirements Processing
- **Recursive requirements**: Supports `-r` and `--requirement` directives in requirements.txt
- **Editable installs**: Warns about `-e` and `--editable` installs (skipped with warning)
- **URL requirements**: Warns about URL-based requirements (skipped with warning)
- **Basic error resilience**: Continues parsing even with malformed lines

### Output Generation
- **Dockerfile generation**: Creates optimized Dockerfiles with conda environment setup
- **Conda environment.yml**: Generates conda environment specification files
- **JSON reporting**: Detailed JSON reports with scan metrics and package resolution

### Configuration
- **YAML mapping file**: Customizable package mappings at `reciper/data/package_mappings.yaml`
- **Flexible output**: Control output format and location via command-line options

### Recent Improvements
- **Recursive requirements parsing**: Full support for `-r` directives in requirements.txt
- **Performance optimization**: File-based caching for AST parsing results
- **Enhanced error handling**: Better warnings for edge cases and malformed files
- **Example projects**: Ready-to-use examples in the `examples/` directory

## Detailed Usage Examples

### Analyze a Bioinformatics Project

```bash
# Basic analysis with default settings (shows scanning progress)
reciper analyze ./my_bioinformatics_project

# Generate files in a specific directory
reciper analyze ./my_bioinformatics_project --output ./environments

# Get JSON report for programmatic processing
reciper analyze ./my_bioinformatics_project --json --report-file analysis.json
```

### Single File Analysis

```bash
# Analyze a single Python file
reciper analyze script.py

# Analyze with custom output location
reciper analyze pipeline.py --output ./docker
```

## Programmatic API Usage

Reciper provides a comprehensive Python API for programmatic use in your applications.

### Basic Analysis

```python
from reciper import analyze

# Analyze a directory
result = analyze("./my_project")
print(f"Found {len(result.imports)} imports")
print(f"Generated files: {result.generated_files}")

# Get JSON output directly
json_result = analyze("./my_project", json_output=True)
print(json_result)
```

### Using the Analyzer Class

```python
from reciper import Analyzer, AnalysisConfig

# Create custom configuration
config = AnalysisConfig(
    output_dir="./output",
    enable_conflict_check=True,
    enable_verification=True,
    parallel_processing=True,
)

# Create analyzer instance
analyzer = Analyzer(config)

# Analyze a directory
result = analyzer.analyze("/path/to/project")

# Access analysis results
print(f"Scanned {result.scanned_files} files")
print(f"Found {len(result.conda_packages)} conda packages")
print(f"Found {len(result.apt_packages)} apt packages")

# Convert to dictionary or JSON
result_dict = result.to_dict()
result_json = result.to_json(indent=2)
```

### Advanced Configuration

```python
from reciper import AnalysisConfig, analyze_with_custom_config

# Custom configuration for specific use cases
config = AnalysisConfig(
    output_dir="./custom_output",
    generate_dockerfile=True,
    generate_environment_yml=True,
    generate_lockfile=False,  # Skip lockfile generation
    enable_conflict_check=True,
    enable_verification=False,  # Skip verification
    parallel_processing=True,
    max_workers=4,  # Limit parallel workers
    use_cache=True,  # Enable AST caching
    json_output=False,
    verbose=True,
)

# Analyze with custom config
result = analyze_with_custom_config("/path/to/project", config)
```

### Single File Analysis

```python
from reciper import analyze_single_file

# Analyze a single Python file
result = analyze_single_file("script.py")
print(f"Imports in file: {[imp.module for imp in result.imports]}")
```

### Integration with Existing Code

```python
from reciper import Analyzer
from pathlib import Path

def analyze_project_and_generate_report(project_path: Path) -> dict:
    """Analyze project and return formatted report."""
    analyzer = Analyzer()
    result = analyzer.analyze(project_path)
    
    # Custom processing
    report = {
        "project": str(project_path),
        "summary": {
            "files_scanned": result.scanned_files,
            "python_files": result.python_files_found,
            "conda_packages": len(result.conda_packages),
            "apt_packages": len(result.apt_packages),
            "conflicts_found": len(result.conflicts),
        },
        "packages": list(result.conda_packages.keys()),
        "generated_files": result.generated_files,
        "verification_passed": result.verification_passed,
    }
    
    return report

# Usage
report = analyze_project_and_generate_report(Path("./my_project"))
print(report)
```

## JSON Report Structure

The tool generates comprehensive JSON reports with the following structure:

```json
{
  "scan_summary": {
    "scan_directory": "/path/to/project",
    "total_files_scanned": 42,
    "python_files_found": 15,
    "scan_time_seconds": 1.234,
    "scan_timestamp": "2024-01-15T10:30:00Z"
  },
  "detected_imports": [
    "numpy",
    "pandas",
    "matplotlib",
    "biopython",
    "scikit-learn"
  ],
  "requirements_analysis": {
    "requirements_file_found": true,
    "requirements_file_path": "/path/to/project/requirements.txt",
    "parsed_requirements_count": 8,
    "imports_missing_from_requirements": ["biopython"],
    "requirements_not_imported": ["flask", "requests"]
  },
  "package_mapping": [
    {
      "python_package": "numpy",
      "conda_package": "numpy",
      "version_constraint": ">=1.21.0",
      "mapping_source": "primary_mappings"
    },
    {
      "python_package": "biopython",
      "conda_package": "biopython",
      "version_constraint": null,
      "mapping_source": "primary_mappings"
    }
  ],
  "generated_files": {
    "dockerfile": {
      "generated": true,
      "path": "/path/to/project/Dockerfile"
    },
    "environment_yml": {
      "generated": true,
      "path": "/path/to/project/environment.yml"
    }
  },
  "warnings": [
    "3 imported packages missing from requirements"
  ]
}
```

## Configuration

### Package Mappings

The tool uses a YAML configuration file at `reciper/data/package_mappings.yaml` to map Python package names to conda package names. The file includes:

- **Primary mappings**: Direct Python-to-conda package mappings
- **Standard library modules**: Python standard library modules that don't require conda packages
- **Common bioinformatics packages**: Specialized mappings for bioinformatics tools

Example mapping structure:
```yaml
primary_mappings:
  numpy: "numpy"
  pandas: "pandas"
  matplotlib: "matplotlib"
  biopython: "biopython"
  scikit-learn: "scikit-learn"
  
standard_library:
  os: ""
  sys: ""
  json: ""
  # ... other stdlib modules
```

### Customizing Mappings

You can extend or modify the mappings by editing the YAML file or providing your own mapping file. The tool loads mappings at runtime to support custom package names.

## Development Setup

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/githubuser/reciper
cd reciper

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=reciper

# Run specific test module
pytest tests/test_features.py
```

### Code Quality

```bash
# Run linter
flake8 reciper/

# Format code with black
black reciper/

# Type checking with mypy
mypy reciper/
```

### Project Structure

```
reciper/
├── reciper/                    # Main package
│   ├── __init__.py            # Package initialization
│   ├── api.py                 # Public API interface
│   ├── cli.py                 # Command-line interface
│   ├── parser.py              # Python import parser
│   ├── mapper.py              # Package mapping logic
│   ├── generator.py           # File generation (Dockerfile, environment.yml)
│   ├── import_aggregator.py   # Import aggregation across files
│   ├── requirements_parser.py # Requirements.txt parsing
│   ├── reporter.py            # JSON report generation
│   ├── scanner.py             # Directory scanning
│   ├── verifier.py            # Verification logic
│   ├── cache.py               # AST caching for performance
│   ├── command_detector.py    # System command detection
│   ├── conda_parser.py        # Conda environment parsing
│   ├── conflict_detector.py   # Package conflict detection
│   ├── error_handling.py      # Error handling utilities
│   ├── lockfile_generator.py  # Lockfile generation
│   ├── utils.py               # Shared utilities
│   └── data/                  # Data files
│       ├── package_mappings.yaml    # Package mapping configuration
│       ├── command_mappings.yaml    # Command to apt package mappings
│       └── known_conflicts.yaml     # Known package conflicts
├── tests/                     # Test suite
├── docs/                      # Documentation
├── examples/                  # Example projects
├── pyproject.toml            # Project configuration
├── environment.yml           # Conda environment specification
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## How It Works

1. **Scanning**: The tool recursively scans the target directory for Python files
2. **Parsing**: Each Python file is parsed to extract import statements
3. **Aggregation**: Imports are aggregated across all files, removing duplicates
4. **Requirements Analysis**: If a requirements.txt file exists, it's parsed and compared with detected imports
5. **Mapping**: Python package names are mapped to conda package names using the mapping database
6. **Generation**: Dockerfile and environment.yml files are generated with the mapped packages
7. **Reporting**: A detailed JSON report is generated (if requested)

## Limitations and Future Work

### Current Limitations
- Only supports Python imports (not other languages)
- Basic version constraint handling
- Limited to conda and Docker environment generation
- Single mapping file (not dynamically updated)

### Planned Features
- Support for additional package managers (pip, apt, etc.)
- Dynamic mapping updates from conda repositories
- Support for R and other bioinformatics languages
- Integration with CI/CD pipelines
- Web interface for visualization

## Contributing

Contributions are welcome! Please see the development setup section above to get started.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT