# CLI Usage

Reciper provides a comprehensive command-line interface for analyzing Python projects and generating reproducible environments.

## Installation

```bash
# Install from PyPI
pip install reciper

# Install from source
git clone https://github.com/githubuser/reciper
cd reciper
pip install -e .
```

## Basic Usage

### Analyze a Directory

```bash
# Basic analysis
reciper analyze /path/to/project

# Analyze with JSON output
reciper analyze /path/to/project --json

# Specify output directory
reciper analyze /path/to/project --output ./generated
```

### Analyze a Single File

```bash
# Analyze a single Python file
reciper analyze script.py

# Analyze with custom output
reciper analyze pipeline.py --output ./docker
```

## Command Reference

### `analyze` Command

Analyze Python files and generate reproducible environment files.

```bash
reciper analyze [OPTIONS] PATH
```

**Arguments:**
- `PATH`: Path to directory or file to analyze

**Options:**
- `--output DIR, -o DIR`: Output directory for generated files (default: ".")
- `--json`: Output JSON report to stdout
- `--report-file FILE`: Save JSON report to file
- `--no-lock`: Skip lock file generation
- `--no-verify`: Skip verification step
- `--verbose, -v`: Detailed output with debug information
- `--no-conflict-check`: Disable conflict detection
- `--no-parallel`: Disable parallel processing
- `--max-workers NUM`: Maximum number of worker threads
- `--no-cache`: Disable AST caching
- `--help`: Show help message

## Examples

### Basic Bioinformatics Project Analysis

```bash
# Analyze a bioinformatics project
reciper analyze ./my_bioinformatics_project

# Output:
# Scanning... Directories: 42, Files: 156, Python files: 23
# Found 15 unique imports
# Mapped to 12 conda packages
# Generated Dockerfile and environment.yml in ./my_bioinformatics_project
```

### Generate Files in Custom Directory

```bash
# Generate files in a specific directory
reciper analyze ./project --output ./environments

# Check generated files
ls ./environments/
# Dockerfile  environment.yml  lockfile.txt
```

### JSON Reporting

```bash
# Get JSON report to stdout
reciper analyze ./project --json

# Save JSON report to file
reciper analyze ./project --report-file analysis.json

# Use JSON output with jq for processing
reciper analyze ./project --json | jq '.conda_packages'
```

### Performance Tuning

```bash
# Disable parallel processing for debugging
reciper analyze ./project --no-parallel

# Limit worker threads
reciper analyze ./project --max-workers 2

# Disable caching (useful for one-time analysis)
reciper analyze ./project --no-cache
```

## Output Files

Reciper generates the following files in the output directory:

### Dockerfile

A Dockerfile with conda environment setup.

```dockerfile
FROM continuumio/miniconda3:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create conda environment
COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml && \
    conda clean -afy

# Activate environment
ENV PATH /opt/conda/envs/reciper-env/bin:$PATH
```

### environment.yml

Conda environment specification.

```yaml
name: reciper-env
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - numpy
  - pandas
  - matplotlib
  - biopython
```

### Lock Files (Optional)

Version-pinned dependency files for reproducibility.

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Analysis failed
- `4`: File generation failed

## Environment Variables

- `RECIPER_CACHE_DIR`: Custom cache directory (default: `~/.reciper_cache`)
- `RECIPER_LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)
- `RECIPER_MAX_WORKERS`: Maximum worker threads (overrides `--max-workers`)

## Integration with Shell Scripts

```bash
#!/bin/bash

# Analyze project and check for errors
if reciper analyze ./project --output ./generated; then
    echo "Analysis successful"
    
    # Count packages
    PACKAGE_COUNT=$(reciper analyze ./project --json | jq '.conda_packages | length')
    echo "Found $PACKAGE_COUNT conda packages"
    
    # Build Docker image
    docker build -t my-project ./generated
else
    echo "Analysis failed"
    exit 1
fi
```

## Bash Completion

Reciper supports bash completion. To enable it:

```bash
# For bash
eval "$(_RECIPER_COMPLETE=bash_source reciper)"

# For zsh
eval "$(_RECIPER_COMPLETE=zsh_source reciper)"

# For fish
eval "$(_RECIPER_COMPLETE=fish_source reciper)"
```

## Common Use Cases

### CI/CD Pipeline Integration

```yaml
# GitHub Actions example
name: Analyze and Build
on: [push]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install reciper
      - run: reciper analyze . --output ./docker --json --report-file analysis.json
      - uses: actions/upload-artifact@v2
        with:
          name: analysis
          path: |
            ./docker/Dockerfile
            ./docker/environment.yml
            analysis.json
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: reciper-analysis
        name: Reciper Analysis
        entry: reciper analyze . --output ./.reciper --no-lock
        language: system
        pass_filenames: false
        always_run: true
```

### Batch Processing

```bash
#!/bin/bash

# Analyze multiple projects
PROJECTS=("project1" "project2" "project3")

for project in "${PROJECTS[@]}"; do
    echo "Analyzing $project..."
    reciper analyze "./$project" --output "./output/$project" --report-file "./output/$project/analysis.json"
    
    if [ $? -eq 0 ]; then
        echo "✓ $project analyzed successfully"
    else
        echo "✗ $project analysis failed"
    fi
done
```

## Troubleshooting

### Common Issues

1. **"No Python files found"**
   - Ensure the directory contains `.py` files
   - Check file permissions

2. **"Failed to parse imports"**
   - Syntax errors in Python files
   - Try with `--no-cache` to bypass cached AST

3. **"Package mapping not found"**
   - Custom packages may not be in the mapping database
   - Check `reciper/data/package_mappings.yaml`

4. **Performance issues**
   - Use `--no-parallel` for debugging
   - Try `--max-workers 1` to isolate issues

### Debug Mode

```bash
# Enable verbose output
reciper analyze ./project --verbose

# Combine with JSON output
reciper analyze ./project --json --verbose 2> debug.log
```

## Advanced Features

### Custom Package Mappings

```bash
# Use custom mapping file
RECIPER_MAPPING_FILE=./custom_mappings.yaml reciper analyze ./project
```

### Cache Management

```bash
# Clear cache
rm -rf ~/.reciper_cache

# Or use environment variable
RECIPER_CACHE_DIR=/tmp/reciper_cache reciper analyze ./project
```

### Integration with Docker

```bash
# Analyze and build in one command
reciper analyze ./project --output ./docker
docker build -t my-project ./docker