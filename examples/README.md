# Reciper Examples

This directory contains example projects demonstrating Reciper capabilities.

## Simple Bioinformatics Project

The `simple_bioinformatics_project/` directory contains a basic bioinformatics analysis script with:

- **analysis.py**: A Python script with common bioinformatics imports (numpy, pandas, biopython, scikit-learn, matplotlib, seaborn)
- **requirements.txt**: Project dependencies with recursive requirements (`-r dev-requirements.txt`)
- **dev-requirements.txt**: Development dependencies referenced by requirements.txt

### Running RECIPER on the Example

```bash
# From the reciper directory
cd examples/simple_bioinformatics_project

# Analyze the project
reciper analyze .

# Analyze with JSON output
reciper analyze . --json

# Analyze and generate files in a specific directory
reciper analyze . --output ./generated
```

### Expected Output

When you run RECIPER on this example, you should see:

1. **Directory scanning**: 1 Python file found (analysis.py)
2. **Import parsing**: 7 packages detected (numpy, pandas, Bio, sklearn, matplotlib, seaborn, os, pathlib)
3. **Requirements parsing**: 11 packages parsed (including recursive dev-requirements.txt)
4. **Package mapping**: Python packages mapped to conda specifications
5. **File generation**: Dockerfile and environment.yml created

### Key Features Demonstrated

- **Recursive requirements parsing**: The `-r dev-requirements.txt` directive is processed
- **Standard library detection**: `os` and `pathlib` are identified as standard library modules
- **Bioinformatics packages**: Special handling for biopython and scikit-learn
- **Performance caching**: Repeated analysis of the same file uses cached results

## Testing the Tool

You can also test RECIPER on your own projects:

```bash
# Analyze any directory
reciper analyze /path/to/your/project

# Single file analysis
reciper analyze script.py

# Get JSON report
reciper analyze /path/to/project --json --report-file analysis.json