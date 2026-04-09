# Reciper Documentation

Welcome to the Reciper documentation! Reciper is a static analyzer for Python pipelines that generates reproducible environments.

## Overview

Reciper analyzes Python codebases to:
- Parse import statements from Python files
- Map Python packages to their corresponding conda specifications
- Generate Dockerfile and environment.yml files for reproducible environments
- Detect system command dependencies and map them to apt packages
- Provide detailed JSON reports of the analysis

## Quick Links

- [CLI Usage](cli-usage.md) - Command-line interface reference
- [API Reference](api-reference.md) - Programmatic API documentation
- [Contributing](contributing.md) - How to contribute to Reciper

## Core Concepts

### Static Analysis
Reciper performs static analysis on Python code, meaning it examines source code without executing it. This approach is safe, fast, and doesn't require installing dependencies.

### Package Mapping
The tool maintains a mapping database that translates Python package names to their corresponding conda package names. This handles cases where package names differ between pip and conda.

### Environment Generation
Based on the analysis, Reciper generates:
- **Dockerfile**: Container definition with conda environment setup
- **environment.yml**: Conda environment specification file
- **Lock files**: Version-pinned dependency files for reproducibility

### Command Detection
Reciper can detect system commands in Python code (like `subprocess.run()`) and map them to apt packages that need to be installed.

## Getting Started

1. **Install Reciper**: `pip install reciper`
2. **Analyze a project**: `reciper analyze /path/to/project`
3. **Generate files**: Check the output directory for generated Dockerfile and environment.yml

## Features

- **Multi-file analysis**: Recursively scans directories for Python files
- **Requirements comparison**: Compares detected imports with existing requirements.txt
- **Conflict detection**: Identifies potential package conflicts
- **Performance caching**: Caches AST parsing for faster repeated scans
- **Parallel processing**: Uses multiple CPU cores for faster analysis
- **JSON reporting**: Detailed machine-readable output
- **Programmatic API**: Use Reciper as a library in your Python applications

## Use Cases

### Bioinformatics Pipelines
Analyze bioinformatics workflows to generate reproducible conda environments and Docker containers.

### Research Reproducibility
Ensure computational research can be reproduced by generating complete environment specifications.

### CI/CD Integration
Integrate Reciper into CI/CD pipelines to automatically generate environment files for deployments.

### Dependency Auditing
Understand the complete dependency graph of a Python project, including system dependencies.

## License

Reciper is released under the MIT License. See the [LICENSE](../LICENSE) file for details.