# API Reference

Reciper provides a comprehensive Python API for programmatic use. This document covers all public API components.

## Importing the API

```python
# Import the main API components
from reciper import (
    analyze,
    analyze_single_file,
    analyze_with_custom_config,
    Analyzer,
    AnalysisConfig,
    AnalysisResult,
)
```

## Core Functions

### `analyze()`

The main convenience function for analyzing directories or files.

```python
from reciper import analyze

# Analyze a directory
result = analyze("./my_project")

# Analyze with JSON output
json_result = analyze("./my_project", json_output=True)

# Analyze with custom options
result = analyze(
    "./my_project",
    output_dir="./output",
    enable_conflict_check=True,
    enable_verification=True,
)
```

**Parameters:**
- `path` (str or Path): Path to directory or file to analyze
- `output_dir` (str, default="."): Directory where generated files should be placed
- `json_output` (bool, default=False): If True, returns JSON string instead of AnalysisResult
- `enable_conflict_check` (bool, default=True): Enable/disable conflict detection
- `enable_verification` (bool, default=True): Enable/disable verification

**Returns:**
- `AnalysisResult` object if `json_output=False`
- JSON string if `json_output=True`

### `analyze_single_file()`

Analyze a single Python file (doesn't generate environment files by default).

```python
from reciper import analyze_single_file

result = analyze_single_file("script.py", output_dir=".")
```

**Parameters:**
- `file_path` (str or Path): Path to Python file
- `output_dir` (str, default="."): Directory where generated files should be placed

**Returns:**
- `AnalysisResult` object

### `analyze_with_custom_config()`

Analyze with a custom configuration object.

```python
from reciper import analyze_with_custom_config, AnalysisConfig

config = AnalysisConfig(
    output_dir="./output",
    enable_conflict_check=False,
    parallel_processing=True,
)

result = analyze_with_custom_config("./my_project", config)
```

**Parameters:**
- `path` (str or Path): Path to directory or file to analyze
- `config` (AnalysisConfig): Custom configuration object

**Returns:**
- `AnalysisResult` object

## Core Classes

### `AnalysisConfig`

Configuration class for analysis operations.

```python
from reciper import AnalysisConfig

config = AnalysisConfig(
    output_dir="./output",
    generate_lockfile=True,
    generate_dockerfile=True,
    generate_environment_yml=True,
    enable_conflict_check=True,
    enable_verification=True,
    enable_command_detection=True,
    parallel_processing=True,
    max_workers=None,  # Auto-detect
    use_cache=True,
    json_output=False,
    verbose=False,
)
```

**Attributes:**
- `output_dir` (str): Output directory for generated files
- `generate_lockfile` (bool): Generate lock files
- `generate_dockerfile` (bool): Generate Dockerfile
- `generate_environment_yml` (bool): Generate environment.yml
- `enable_conflict_check` (bool): Enable conflict detection
- `enable_verification` (bool): Enable verification
- `enable_command_detection` (bool): Enable command detection
- `parallel_processing` (bool): Use parallel processing
- `max_workers` (int or None): Maximum worker threads
- `use_cache` (bool): Use AST caching
- `json_output` (bool): Output JSON format
- `verbose` (bool): Verbose output

### `AnalysisResult`

Result class containing analysis results.

```python
from reciper import AnalysisResult

result = analyzer.analyze("./project")

# Access results
print(f"Found {len(result.imports)} imports")
print(f"Scanned {result.scanned_files} files")
print(f"Generated files: {result.generated_files}")

# Convert to dictionary
result_dict = result.to_dict()

# Convert to JSON
result_json = result.to_json(indent=2)
```

**Attributes:**
- `imports` (List[AggregatedImport]): Detected imports
- `conda_packages` (Dict[str, str]): Mapped conda packages
- `apt_packages` (List[str]): Detected apt packages
- `conflicts` (List[Dict]): Detected package conflicts
- `scanned_files` (int): Number of files scanned
- `scanned_directories` (int): Number of directories scanned
- `python_files_found` (int): Number of Python files found
- `requirements_file_found` (bool): Whether requirements.txt was found
- `generated_files` (List[str]): Paths to generated files
- `output_dir` (str): Output directory used
- `verification_passed` (bool): Verification status
- `verification_errors` (List[str]): Verification errors

**Methods:**
- `to_dict()`: Convert result to dictionary
- `to_json(indent=2)`: Convert result to JSON string

### `Analyzer`

Main analyzer class for programmatic use.

```python
from reciper import Analyzer, AnalysisConfig

# Create analyzer with default config
analyzer = Analyzer()

# Create analyzer with custom config
config = AnalysisConfig(output_dir="./custom")
analyzer = Analyzer(config)

# Analyze a directory
result = analyzer.analyze("./my_project")

# Analyze and get JSON directly
json_result = analyzer.analyze_to_json("./my_project", indent=2)
```

**Methods:**
- `__init__(config=None)`: Initialize analyzer
- `analyze(path)`: Analyze directory or file
- `analyze_to_json(path, indent=2)`: Analyze and return JSON string

## Data Classes

### `AggregatedImport`

Represents aggregated import information across multiple files.

```python
from reciper import AggregatedImport

# Attributes
import_obj = AggregatedImport(
    module="numpy",           # Module name
    imports=["np"],           # Import aliases
    files=[Path("file1.py")], # Files where imported
    line_numbers=[10, 20],    # Line numbers
)
```

### `PackageRequirement`

Represents a package requirement from requirements.txt.

```python
from reciper import PackageRequirement

req = PackageRequirement(
    name="numpy",
    specifier=">=1.21.0",
    line_number=1,
)
```

## Example: Complete Workflow

```python
from pathlib import Path
from reciper import Analyzer, AnalysisConfig
import json

def analyze_project(project_path: Path) -> dict:
    """Analyze project and return formatted report."""
    
    # Configure analysis
    config = AnalysisConfig(
        output_dir=project_path / "generated",
        generate_dockerfile=True,
        generate_environment_yml=True,
        enable_conflict_check=True,
        parallel_processing=True,
    )
    
    # Create analyzer
    analyzer = Analyzer(config)
    
    # Perform analysis
    result = analyzer.analyze(project_path)
    
    # Create custom report
    report = {
        "project": str(project_path),
        "summary": {
            "files_scanned": result.scanned_files,
            "python_files": result.python_files_found,
            "conda_packages": len(result.conda_packages),
            "apt_packages": len(result.apt_packages),
            "conflicts": len(result.conflicts),
            "verification_passed": result.verification_passed,
        },
        "packages": {
            "conda": list(result.conda_packages.keys()),
            "apt": result.apt_packages,
        },
        "generated_files": result.generated_files,
        "conflicts": result.conflicts,
    }
    
    return report

# Usage
project_path = Path("./my_bioinformatics_project")
report = analyze_project(project_path)

# Save report
with open(project_path / "analysis_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

## Error Handling

The API raises standard Python exceptions:

- `FileNotFoundError`: When the specified path doesn't exist
- `ValueError`: When invalid arguments are provided
- `ImportError`: When required dependencies are missing

```python
from reciper import analyze

try:
    result = analyze("/nonexistent/path")
except FileNotFoundError as e:
    print(f"Path not found: {e}")
except Exception as e:
    print(f"Analysis failed: {e}")
```

## Type Hints

All API functions and classes include type hints for better IDE support and static type checking.

```python
from typing import Union
from pathlib import Path
from reciper import AnalysisResult

def process_result(result: AnalysisResult) -> None:
    """Type-hinted function using Reciper API."""
    # Your code here
```

## Integration with Other Tools

### Pandas Integration

```python
import pandas as pd
from reciper import analyze

result = analyze("./project")

# Create DataFrame from imports
imports_df = pd.DataFrame([
    {
        "module": imp.module,
        "import_count": len(imp.imports),
        "file_count": len(imp.files),
    }
    for imp in result.imports
])
```

### JSON Schema Validation

```python
import jsonschema
from reciper import analyze

result = analyze("./project", json_output=True)
data = json.loads(result)

# Validate against schema
schema = {
    "type": "object",
    "properties": {
        "imports": {"type": "array"},
        "conda_packages": {"type": "object"},
    },
    "required": ["imports", "conda_packages"],
}

jsonschema.validate(data, schema)