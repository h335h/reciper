# Reciper - Installation and Usage Guide

## 🚀 Quick Installation

### Option 1: Via pip (recommended)
```bash
pip install reciper
```

### Option 2: Via pipx (isolated installation)
```bash
pipx install reciper
```

### Option 3: From source
```bash
git clone https://github.com/h335h/reciper.git
cd reciper
pip install -e .
```

## 📋 Basic Usage

### Analyze Your Pipeline
```bash
# Navigate to your pipeline directory
cd /path/to/your/pipeline

# Run analysis with a single command
reciper analyze .
```

### Full Analysis with Verification
```bash
reciper analyze . --verbose
```

### What Reciper Does:
1. **Scans** all Python files in the directory
2. **Extracts** package imports (numpy, pandas, biopython, etc.)
3. **Detects** external tool calls via subprocess (samtools, bwa, fastqc, etc.)
4. **Generates**:
   - `environment.yml` - Conda environment
   - `Dockerfile` - Docker image with all dependencies
   - Lock files for reproducibility (if conda-lock/pip-tools are installed)
5. **Validates** generated files for syntax correctness
6. **Detects** version conflicts between packages

## 📁 Output Files

After running Reciper, you'll receive:

```
your_pipeline/
├── environment.yml      # Conda environment
├── environment.lock.yml # Locked versions for reproducibility
├── Dockerfile          # Docker image definition
└── ... your files ...
```

### Example Dockerfile (Bioinformatics):
```dockerfile
FROM continuumio/miniconda3:latest

WORKDIR /app

# System packages (auto-detected)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    samtools bcftools fastqc multiqc bwa && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python packages
COPY environment.yml .
RUN conda env update -f environment.yml

# Environment variables for bioinformatics tools
ENV AUGUSTUS_CONFIG_PATH=/opt/augustus/config

CMD ["/bin/bash"]
```

## 🔧 CLI Options Reference

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory for generated files (default: current) |
| `-v, --verbose` | Detailed output with debug information |
| `--no-verify` | Skip verification of generated files |
| `--no-lock` | Don't generate lock files |
| `--no-conflict-check` | Disable version conflict detection |
| `--json` | Output JSON report to stdout |
| `--report-file` | Save JSON report to file |
| `--parallel / --no-parallel` | Enable/disable parallel processing (default: enabled) |
| `--max-workers` | Maximum worker threads (default: auto-calculated) |
| `--no-cache` | Disable AST caching (default: caching enabled) |

## 💡 Usage Examples

### Simple Project Analysis
```bash
cd my_bioinformatics_project
reciper analyze .
```

### Analysis with Verbose Output
```bash
reciper analyze /path/to/pipeline --verbose
```

### Analysis with Report
```bash
reciper analyze . --report-file analysis_report.json
```

### Fast Analysis (Skip Verification)
```bash
reciper analyze . --no-verify
```

### Analysis with Custom Output Directory
```bash
reciper analyze . --output ./docker_files
```

## 🎯 Who Is This Tool For?

- **Bioinformaticians** publishing pipelines in papers
- **Laboratories** standardizing environments
- **NGS workflow developers**
- **Researchers** ensuring reproducibility
- **Data scientists** working with bioinformatics data

## ✅ What Reciper Guarantees

The generated Dockerfile:
- ✅ Contains all required Python packages
- ✅ Includes system utilities (samtools, bwa, etc.) detected via subprocess analysis
- ✅ Passes syntax validation
- ✅ Is ready to build and use
- ✅ Automatically adds bioconda channel for bioinformatics packages
- ✅ Sets environment variables for bioinformatics tools (e.g., AUGUSTUS_CONFIG_PATH)

## 🚀 Next Steps

After generating files:

```bash
# Build Docker image
docker build -t my_pipeline .

# Run container
docker run -it my_pipeline

# Or create conda environment
conda env create -f environment.yml
conda activate generated-environment
```

## 🔍 Performance Tips

- **First run**: Reciper builds AST cache (`.reciper_cache/`), so it may be slower
- **Subsequent runs**: Cached results make analysis much faster
- **Large projects**: Parallel processing is automatically enabled for 50+ files
- **Quick iterations**: Use `--no-verify` to skip validation during development
- **Full reproducibility**: Keep the generated lock files in version control

## 📊 Example Output

```bash
$ reciper analyze ./my_pipeline --verbose

Scanning directory: ./my_pipeline
Found 8 Python files in ./my_pipeline

Aggregated 15 unique packages from 8 files
Found dependency file: requirements.txt
Parsed 12 package requirements

Mapping Python packages to conda specifications...
Mapped to 12 conda specifications

Detected commands: fastqc, samtools, bwa, multiqc

============================================================
PACKAGE CONFLICT DETECTION
============================================================
1. [WARNING] pandas 2.0.0+ requires NumPy 1.21.0+
============================================================

Created environment.yml at environment.yml
Created Dockerfile at Dockerfile
Created conda lock file: environment.lock.yml

============================================================
VERIFICATION
============================================================
✓ Dockerfile syntax check passed
✓ environment.yml syntax check passed
✅ Verification passed

============================================================
ANALYSIS SUMMARY
============================================================
Python files scanned: 8
Unique packages found: 15
Conda specifications: 12
Apt packages: 4 (samtools, bwa, fastqc, multiqc)
============================================================
Success
```

## 🛠️ Troubleshooting

### Lock files not generated
- Install `conda-lock` for conda lock files: `conda install -c conda-forge conda-lock`
- Install `pip-tools` for pip lock files: `pip install pip-tools`

### Verification fails
- Check if Docker is running: `docker info`
- Verify Python syntax in your files
- Try `--no-verify` to skip validation

### Missing packages in generated files
- Ensure all imports use standard syntax
- Check that subprocess calls use recognized tool names
- Review `reciper/data/command_mappings.yaml` for tool support

## 🔗 Additional Resources

- Full documentation: `/docs` directory
- API reference: See main README.md
- Examples: `/examples` directory
- Issue tracker: https://github.com/h335h/reciper/issues
