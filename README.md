# Reciper — One-Command Reproducible Environments for Bioinformatics Pipelines

[![CI](https://github.com/h335h/reciper/actions/workflows/ci.yml/badge.svg)](https://github.com/h335h/reciper/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/reciper.svg)](https://pypi.org/project/reciper/)
[![Python versions](https://img.shields.io/pypi/pyversions/reciper.svg)](https://pypi.org/project/reciper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Generate working Docker and conda environments for bioinformatics pipelines with a single command.**

---

## Table of Contents

- [What is Reciper?](#what-is-reciper)
- [Quick Start](#quick-start)
- [CLI Command Reference](#cli-command-reference)
- [How It Works](#how-it-works)
- [Key Features](#key-features)
- [Supported Bioinformatics Tools](#supported-bioinformatics-tools)
- [Programmatic API](#programmatic-api)
- [Project Structure](#project-structure)
- [Testing and Development](#testing-and-development)
- [Configuration](#configuration)
- [JSON Report Structure](#json-report-structure)
- [Limitations and Future Improvements](#limitations-and-future-improvements)
- [Contributing](#contributing)
- [License](#license)

---

## What is Reciper?

Reciper is a CLI tool and Python library that **automatically generates guaranteed-to-work environments** for bioinformatics pipelines:

1. **Scans** your Python code and finds all imports
2. **Detects** external tool calls (samtools, bwa, fastqc, etc.) via subprocess analysis
3. **Generates** `Dockerfile` and `environment.yml` with correct dependencies
4. **Checks** package compatibility and finds conflicts
5. **Validates** environments through syntax checks and optional test builds
6. **Creates** lock files for full reproducibility (via `conda-lock` and `pip-compile`)

**Result:** Your colleagues can run your pipeline on the first try without "package not found" errors or version conflicts.

---

## Quick Start

### Installation

```bash
# Option 1: Via pip (recommended)
pip install reciper

# Option 2: Via pipx (isolated, doesn't pollute your system)
pipx install reciper

# Option 3: For development
git clone https://github.com/h335h/reciper
cd reciper && pip install -e ".[dev]"
```

### Basic Usage

```bash
# Navigate to your pipeline directory and run analysis
cd /path/to/your/pipeline
reciper analyze .
```

**That's it!** After execution, you'll get:
- `Dockerfile` — ready-to-build container
- `environment.yml` — conda environment
- `environment.lock.yml` — locked versions for reproducibility
- `analysis.json` — detailed report (optional, via `--report-file`)

---

## CLI Command Reference

### `reciper analyze <path>`

Analyze Python code and generate reproducible environments.

```
Usage: reciper analyze [OPTIONS] PATH

Arguments:
  PATH    Path to Python source file or directory to analyze
```

#### Options

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Output directory for generated files (default: current directory) |
| `--json`, `-j` | Output JSON report to stdout |
| `--report-file`, `-r` | Save JSON report to a file |
| `--no-lock` | Disable lock file generation |
| `--no-verify` | Skip verification step |
| `--verbose`, `-v` | Detailed output with debug information |
| `--conflict-check` / `--no-conflict-check` | Enable/disable conflict detection (default: enabled) |
| `--parallel` / `--no-parallel` | Enable/disable parallel processing (default: enabled) |
| `--max-workers` | Maximum number of worker threads (default: auto-calculated based on file count) |
| `--no-cache` | Disable AST caching (default: caching enabled) |

#### Examples

```bash
# Basic analysis
reciper analyze .

# Analyze with verbose output
reciper analyze . --verbose

# Save JSON report to file
reciper analyze . --report-file report.json

# Output JSON to console
reciper analyze . --json

# Skip verification (faster)
reciper analyze . --no-verify

# Disable conflict checking
reciper analyze . --no-conflict-check

# Specify output directory
reciper analyze . --output ./docker_files

# Disable parallel processing
reciper analyze . --no-parallel

# Disable AST caching
reciper analyze . --no-cache

# Analyze a specific file
reciper analyze pipeline.py

# Full example with multiple options
reciper analyze ./rna-seq-pipeline --verbose --output ./env --report-file analysis.json --no-lock
```

---

## How It Works

```
+-----------------------------------------------------------------+
|  1. Scanning                                                    |
|     - Find .py files recursively in directory                   |
|     - Parse AST to extract imports (with caching)               |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|  2. Dependency Discovery                                        |
|     - Python packages (numpy, pandas, biopython)                |
|     - System utilities (samtools, bwa, fastqc via subprocess)   |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|  3. Map to conda/apt                                            |
|     - Python imports -> conda packages (biopython, pysam, etc.) |
|     - Commands -> apt/conda packages (samtools, bowtie2, etc.)  |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|  4. Conflict Checking                                           |
|     - Analyze version compatibility                             |
|     - Warn about problematic package combinations               |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|  5. File Generation                                             |
|     - Dockerfile with miniconda3 and apt packages               |
|     - environment.yml for conda                                 |
|     - Lock files for reproducibility (conda-lock, pip-compile)  |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|  6. Validation                                                  |
|     - Dockerfile syntax check                                   |
|     - environment.yml YAML validation                           |
|     - (Optional) Test Docker build and import verification      |
+-----------------------------------------------------------------+
```

---

## Key Features

### AST-Based Import Extraction

Reciper uses Python's built-in `ast` module to parse Python files and extract all import statements accurately, handling:

- Standard imports (`import numpy`)
- From imports (`from pandas import DataFrame`)
- Relative imports
- Conditional imports
- Dynamic imports (where statically resolvable)

### Subprocess Command Detection

Reciper scans Python files for external tool invocations through:

- `subprocess.run()`, `subprocess.call()`, `subprocess.Popen()`
- `os.system()` calls
- Shell command strings

It detects 80+ bioinformatics and system commands, automatically mapping them to the appropriate conda or apt packages.

### Python-to-Conda Mapping with 100+ Bioinformatics Packages

Reciper maintains a comprehensive mapping database (`reciper/data/package_mappings.yaml`) that converts Python import names to conda package names, including:

- Direct mappings (numpy -> numpy, pandas -> pandas)
- Alias resolution (sklearn -> scikit-learn)
- Standard library filtering (os, sys, pathlib are excluded)
- Version constraint preservation from requirements.txt

### Version Constraint Preservation

When a `requirements.txt` file is found, Reciper preserves version constraints:

```
# requirements.txt
numpy>=1.21.0
pandas==1.3.0
```

These constraints are carried through to the generated `environment.yml` and Dockerfile.

### Conflict Detection from known_conflicts.yaml

Reciper includes a conflict database (`reciper/data/known_conflicts.yaml`) that checks for known incompatible package combinations:

- Version incompatibilities (e.g., pandas requiring specific numpy versions)
- Performance warnings
- Critical installation failures

Conflicts are reported with severity levels (ERROR, WARNING) and actionable recommendations.

### Dockerfile Generation

Reciper generates production-ready Dockerfiles with:

- Multi-stage builds for smaller images
- Miniconda3 base image
- Bioinformatics-specific environment variables
- Both conda and apt package installation
- Optional pip package installation for conda-unavailable packages
- Optional project self-installation (detected from setup.py)
- Python version constraint support

```dockerfile
FROM continuumio/miniconda3

# Environment variables for bioinformatics tools
ENV PATH="/opt/conda/envs/bio/bin:$PATH"
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install apt packages
RUN apt-get update && apt-get install -y ...

# Create conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Install pip-only packages (if any)
RUN pip install ...

# Install project itself (if setup.py detected)
COPY . /app
RUN pip install /app
```

### environment.yml Generation

Generates valid conda environment files with:

- Proper YAML syntax
- Conda channels (conda-forge, bioconda, defaults)
- Python packages with version constraints
- Pip subsections for conda-unavailable packages

### Lock File Generation

Reciper supports two lock file formats for full reproducibility:

- **conda-lock**: Generates `conda-lock.yml` via the `conda-lock` tool
- **pip-compile**: Generates `requirements-locked.txt` via `pip-tools`

Lock files pin exact versions of all transitive dependencies, ensuring bit-for-bit reproducible environments.

### Verification

Reciper validates generated files through multiple checks:

- **Dockerfile syntax check**: Ensures valid Docker build instructions
- **YAML validation**: Verifies environment.yml is parseable
- **Container testing** (optional): Builds a test Docker image and verifies imports

### JSON Reporting

Comprehensive JSON reports include:

- Scan summary (files scanned, time taken)
- Detected imports with file locations
- Requirements analysis (missing/extra packages)
- Package mapping details
- Generated file paths
- Warnings and conflicts

### Performance Optimizations

Reciper is optimized for large codebases:

- **AST caching**: Parsed ASTs are cached to avoid re-parsing unchanged files
- **Parallel processing**: Import parsing and scanning run in parallel using ThreadPoolExecutor
- **File-level caching**: Results are cached per-file hash for incremental analysis
- **Auto-scaling workers**: Number of workers is auto-calculated based on file count

---

## Supported Bioinformatics Tools

### Conda Packages (Automatic Mapping)

| Category | Packages |
|----------|----------|
| **Bioinformatics** | biopython, pysam, pybedtools, cyvcf2 |
| **Data Science** | pandas, numpy, scipy, scikit-learn |
| **Visualization** | matplotlib, seaborn, plotly |

### System Utilities (Detected via Subprocess)

| Category | Tools |
|----------|-------|
| **Alignment** | bwa, bowtie2, bowtie, star, hisat2 |
| **BAM/SAM/VCF Processing** | samtools, bcftools, bedtools, vcftools, tabix |
| **QC and Reporting** | fastqc, multiqc, trimmomatic, cutadapt |
| **BLAST and Homology Search** | blastn, blastp, blastx, hmmer, muscle, mafft |
| **Phylogenetics** | raxml, iqtree, mrbayes |
| **Variant Annotation** | snpEff, VEP, annovar |

Full command-to-package mappings are defined in `reciper/data/command_mappings.yaml`.

---

## Programmatic API

Reciper can be used as a Python library in your own scripts and pipelines.

### Basic Analysis

```python
from reciper import analyze

# Quick analysis
result = analyze("./my_pipeline")
print(f"Packages found: {len(result.imports)}")
print(f"Generated files: {result.generated_files}")

# Get JSON output
json_result = analyze("./my_pipeline", json_output=True)
print(json_result)
```

### Advanced Analysis with Custom Configuration

```python
from reciper import Analyzer, AnalysisConfig

config = AnalysisConfig(
    output_dir="./output",
    enable_conflict_check=True,
    enable_verification=True,
    parallel_processing=True,
    max_workers=4,
    use_cache=True,
)

analyzer = Analyzer(config)
result = analyzer.analyze("/path/to/project")

# Access results
print(f"Files scanned: {result.scanned_files}")
print(f"Conda packages: {list(result.conda_packages.keys())}")
print(f"Apt packages: {result.apt_packages}")
print(f"Conflicts: {result.conflicts}")
```

### Using the Analyzer Class

```python
from reciper import Analyzer, AnalysisConfig

# Custom configuration
config = AnalysisConfig(
    output_dir="./output",
    generate_dockerfile=True,
    generate_environment_yml=True,
    generate_lockfile=False,  # Skip lockfile generation
    enable_conflict_check=True,
    enable_verification=False,  # Skip verification
    parallel_processing=True,
    max_workers=4,
    use_cache=True,
    json_output=False,
    verbose=True,
)

# Create analyzer instance
analyzer = Analyzer(config)

# Analyze directory
result = analyzer.analyze("/path/to/project")

# Access results
print(f"Files scanned: {result.scanned_files}")
print(f"Conda packages: {len(result.conda_packages)}")
print(f"Apt packages: {len(result.apt_packages)}")

# Convert to dict or JSON
result_dict = result.to_dict()
result_json = result.to_json(indent=2)
```

### Analyzing a Single File

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

---

## Project Structure

```
reciper/
├── reciper/                     # Main package
│   ├── __init__.py             # Package initialization
│   ├── api.py                  # Public API (analyze, Analyzer, AnalysisConfig)
│   ├── cli.py                  # CLI interface (Click)
│   ├── parser.py               # Python import parser (AST)
│   ├── mapper.py               # Python -> conda mapping
│   ├── generator.py            # Dockerfile and environment.yml generation
│   ├── import_aggregator.py    # Import aggregation across files
│   ├── requirements_parser.py  # requirements.txt parser
│   ├── reporter.py             # JSON report generation
│   ├── scanner.py              # Recursive directory scanner
│   ├── verifier.py             # Environment validation
│   ├── cache.py                # AST caching
│   ├── command_detector.py     # Subprocess command detection
│   ├── conflict_detector.py    # Conflict detection
│   ├── lockfile_generator.py   # Lock file generation (conda-lock, pip-compile)
│   ├── error_handling.py       # Error handling utilities
│   ├── constants.py            # Constants
│   ├── utils.py                # Utilities
│   ├── conda_parser.py         # Conda environment parser
│   └── data/                   # Mapping data
│       ├── package_mappings.yaml    # Python -> conda
│       ├── command_mappings.yaml    # Commands -> apt/conda
│       └── known_conflicts.yaml     # Known package conflicts
├── tests/                     # Test suite
├── examples/                  # Example projects
├── docs/                      # Documentation
├── pyproject.toml            # Project configuration
├── environment.yml           # Project conda environment
├── requirements.txt          # Project Python dependencies
└── README.md                 # This file
```

---

## Testing and Development

### Installation for Development

```bash
git clone https://github.com/h335h/reciper
cd reciper
pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=reciper

# Specific module
pytest tests/test_command_detector.py

# Parallel test execution
pytest -n auto
```

### Code Quality Checks

```bash
# Linting
ruff check reciper/

# Formatting
black reciper/

# Type checking
mypy reciper/
```

### Pre-commit Hooks

Reciper uses pre-commit for automated quality checks:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

---

## Configuration

Reciper uses YAML mapping files for package and command resolution. These can be extended by editing the files in `reciper/data/`.

### Package Mappings (`reciper/data/package_mappings.yaml`)

Defines how Python import names map to conda package names:

```yaml
primary_mappings:
  numpy: "numpy"
  pandas: "pandas"
  biopython: "biopython"
  scikit-learn: "scikit-learn"

standard_library:
  os: ""
  sys: ""
  pathlib: ""
```

### Command Mappings (`reciper/data/command_mappings.yaml`)

Maps command names detected in subprocess calls to apt or conda packages:

```yaml
samtools: samtools
bwa: bwa
fastqc: fastqc
bowtie2: bowtie2
```

Most bioinformatics tools are installed via conda/bioconda rather than apt. The mapping file distinguishes between conda-only tools (prefixed with `conda:`) and apt-installable tools.

### Known Conflicts (`reciper/data/known_conflicts.yaml`)

Defines known package incompatibilities:

```yaml
conflicts:
  - packages: [pandas, numpy]
    severity: WARNING
    message: "For optimal performance, use numpy>=1.21.0 with pandas>=1.3.0"
```

---

## JSON Report Structure

When using `--report-file` or `--json`, Reciper generates a detailed report:

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

---

## Limitations and Future Improvements

### Current Limitations

- Supports Python imports only (not other languages like R or Julia)
- Basic version constraint handling (complex constraints may not be fully preserved)
- Focused on conda and Docker environment generation
- Static mapping files (not dynamically updated from conda repositories)
- Single-file JSON reporting is limited compared to directory analysis

### Planned Features

- Support for additional package managers (pip-native, apt, and others)
- Dynamic mapping updates from conda repositories
- R and other bioinformatics language support
- CI/CD pipeline integration
- Web interface for dependency visualization
- Incremental analysis (only re-scan changed files)
- Custom mapping file support via configuration
- Multi-platform Docker builds (linux/amd64, linux/arm64)

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/my-feature`)
3. **Make your changes**
4. **Add tests for new functionality**
5. **Ensure all tests pass** (`pytest`)
6. **Run code quality checks** (`ruff check`, `black`, `mypy`)
7. **Submit a pull request**

### Development Setup

```bash
git clone https://github.com/h335h/reciper
cd reciper
pip install -e ".[dev]"
pre-commit install
```

### Guidelines

- Follow the existing code style (enforced by Black and Ruff)
- Add type hints to all new functions
- Write tests for new functionality
- Update documentation for user-facing changes

---

## License

MIT License

Copyright (c) 2024 Reciper Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
