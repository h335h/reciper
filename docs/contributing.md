# Contributing to Reciper

Thank you for your interest in contributing to Reciper! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## How to Contribute

### Reporting Issues

1. **Check existing issues**: Search the issue tracker to see if the issue has already been reported.
2. **Create a new issue**: If it's a new issue, provide:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Error messages or logs

### Suggesting Features

1. **Check existing feature requests**: Search for similar suggestions.
2. **Create a feature request**: Include:
   - Clear description of the feature
   - Use cases and benefits
   - Proposed implementation (if you have ideas)
   - Any alternatives considered

### Submitting Code Changes

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Add tests** for new functionality
5. **Ensure all tests pass**: `pytest`
6. **Update documentation** if needed
7. **Submit a pull request**

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- (Optional) Poetry for dependency management

### Installation

```bash
# Clone the repository
git clone https://github.com/githubuser/reciper
cd reciper

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Development Dependencies

The project uses several development tools:

- **pytest**: Testing framework
- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks
- **pytest-cov**: Test coverage

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=reciper --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code
black reciper/ tests/

# Lint code
ruff check reciper/ tests/

# Type checking
mypy reciper/

# Run all checks
pre-commit run --all-files
```

### Building Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

## Project Structure

```
reciper/
├── reciper/                    # Main package
│   ├── __init__.py            # Package exports
│   ├── cli.py                 # Command-line interface
│   ├── api.py                 # Programmatic API
│   ├── parser.py              # Import parsing
│   ├── mapper.py              # Package mapping
│   ├── generator.py           # File generation
│   ├── scanner.py             # Directory scanning
│   ├── requirements_parser.py # Requirements parsing
│   ├── command_detector.py    # Command detection
│   ├── conflict_detector.py   # Conflict detection
│   ├── verifier.py            # Verification
│   ├── reporter.py            # Reporting
│   ├── cache.py               # Caching
│   ├── utils.py               # Utilities
│   ├── error_handling.py      # Error handling
│   └── data/                  # Data files
│       ├── package_mappings.yaml
│       └── command_mappings.yaml
├── tests/                     # Test suite
│   ├── test_api.py
│   ├── test_cli.py
│   ├── test_parser.py
│   └── ...
├── docs/                      # Documentation
├── examples/                  # Example projects
├── pyproject.toml            # Project configuration
├── README.md                 # Project README
└── .github/workflows/        # GitHub Actions
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for all function signatures
- Document public functions with docstrings (Google style)
- Keep functions focused and small

### Docstring Format

```python
def analyze(path: Path, config: AnalysisConfig) -> AnalysisResult:
    """
    Analyze a directory or file and generate reproducible environment files.

    Args:
        path: Path to directory or file to analyze
        config: Analysis configuration

    Returns:
        AnalysisResult object with analysis results

    Raises:
        FileNotFoundError: If path does not exist
        ValueError: If configuration is invalid
    """
```

### Type Hints

```python
from typing import List, Dict, Optional, Union
from pathlib import Path

def process_files(
    files: List[Path],
    options: Optional[Dict[str, str]] = None
) -> Union[Dict, str]:
    """Example function with type hints."""
```

### Testing Standards

- Write unit tests for new functionality
- Use descriptive test names
- Test edge cases and error conditions
- Aim for high test coverage (>80%)
- Use fixtures for common test data

## Adding New Features

### Package Mappings

To add new package mappings:

1. Edit `reciper/data/package_mappings.yaml`
2. Add mapping in the appropriate section
3. Add tests in `tests/test_mapper.py`

```yaml
primary_mappings:
  existing-package: "existing-conda-package"
  new-package: "new-conda-package"  # Add this line
```

### Command Detection

To add new command mappings:

1. Edit `reciper/data/command_mappings.yaml`
2. Add command to apt package mapping
3. Add tests in `tests/test_command_detector.py`

```yaml
command_mappings:
  existing-command: "existing-package"
  new-command: "new-package"  # Add this line
```

### New Analysis Features

1. Create new module in `reciper/` directory
2. Add exports to `reciper/__init__.py`
3. Add tests in `tests/`
4. Update documentation

## Pull Request Process

1. **Create PR**: From your feature branch to `main`
2. **CI Checks**: GitHub Actions will run tests and checks
3. **Code Review**: Maintainers will review your code
4. **Address Feedback**: Make requested changes
5. **Merge**: Once approved, your PR will be merged

### PR Checklist

- [ ] Tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Type hints added
- [ ] No linting errors
- [ ] Commit messages are clear

### Commit Messages

Use conventional commit messages:

```
feat: add new API endpoint for batch analysis
fix: resolve issue with package mapping
docs: update API documentation
test: add tests for conflict detection
chore: update dependencies
```

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create GitHub release
4. Publish to PyPI

## Getting Help

- **Issue tracker**: For bugs and feature requests
- **Discussion forum**: For questions and discussions
- **Documentation**: For usage and API reference

## License

By contributing to Reciper, you agree that your contributions will be licensed under the MIT License.