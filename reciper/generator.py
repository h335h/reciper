"""
Generator module for creating Dockerfile and environment.yml files from conda package specifications.

This module provides functionality to generate minimal Dockerfile and environment.yml
files based on conda package specifications extracted by the static analyzer MVP.
"""

from pathlib import Path
from typing import Optional, List

from reciper.conflict_detector import ConflictDetector


def generate_files(
    conda_specs: list[str],
    output_dir: str = ".",
    python_files: Optional[List[Path]] = None,
    include_apt_detection: bool = True,
    no_lock: bool = False,
    conflict_check: bool = True,
    python_version: str | None = None,
    pip_packages: list[str] | None = None,
    install_project: bool = False,
    project_name: str | None = None,
    project_version: str | None = None,
    project_git_url: str | None = None,
) -> None:
    """
    Generate Dockerfile and environment.yml files from conda package specifications.

    Args:
        conda_specs: List of conda package specifications in format "conda: package_name"
                     or "conda: package_name==version" or "conda: package_name>=version"
        output_dir: Directory where files should be created (default: current directory)
        python_files: Optional list of Python files to scan for command calls
        include_apt_detection: Whether to detect apt packages from command calls
        no_lock: Disable lock file generation
        conflict_check: Enable/disable conflict detection (default: enabled)
        python_version: Python version constraint from setup.py (e.g. ">=3.6, <3.12")
        pip_packages: Packages that must be installed via pip (not available via conda)

    Returns:
        None

    Raises:
        OSError: If file creation fails due to permission or disk space issues
        ValueError: If conda_specs format is invalid
    """
    # Convert output_dir to Path object
    output_path = Path(output_dir)

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract package names and versions from "conda: package_name[==version]" format
    package_specs = []
    for spec in conda_specs:
        if not spec.startswith("conda:"):
            raise ValueError(
                f"Invalid conda specification format: {spec}. Expected 'conda: package_name'"
            )

        # Remove "conda:" prefix and strip whitespace
        spec_content = spec[6:].strip()
        if not spec_content:
            continue  # Skip empty specifications

        # Parse package name and optional version
        package_specs.append(spec_content)

    # Check for package conflicts before generating files (if enabled)
    if conflict_check and package_specs:
        try:
            # Extract package names without versions for conflict detection
            package_names = []
            version_constraints = {}
            
            for spec in package_specs:
                # Parse version constraints if present
                for op in ["==", ">=", "<=", ">", "<", "~="]:
                    if op in spec:
                        parts = spec.split(op)
                        pkg_name = parts[0].strip()
                        version = parts[1].strip()
                        package_names.append(pkg_name)
                        version_constraints[pkg_name] = f"{op}{version}"
                        break
                else:
                    # No version specified
                    package_names.append(spec.strip())
            
            # Run conflict detection
            detector = ConflictDetector(package_names, version_constraints)
            conflicts = detector.check_conflicts()
            
            if conflicts:
                print("\n" + "="*60)
                print("PACKAGE CONFLICT DETECTION")
                print("="*60)
                print(detector.get_conflict_summary())
                print("="*60 + "\n")
                
                # Count errors vs warnings
                errors = detector.get_conflicts_by_severity("error")
                warnings = detector.get_conflicts_by_severity("warning")
                
                if errors:
                    print(f"⚠️  Found {len(errors)} critical conflict(s) that may cause installation failures.")
                    print("   Consider adjusting package versions or splitting environments.\n")
                
                if warnings:
                    print(f"ℹ️  Found {len(warnings)} compatibility warning(s).")
                    print("   These are recommendations for optimal performance.\n")
        except Exception as e:
            # Don't fail generation if conflict detection fails
            print(f"⚠️  Conflict detection failed: {e}")
            print("   Continuing with file generation...\n")
    elif not conflict_check and package_specs:
        print("ℹ️  Conflict detection disabled via --no-conflict-check flag")

    # Extract conda packages from subprocess commands and merge with import-derived packages
    command_conda_packages: list[str] = []
    if include_apt_detection and python_files:
        command_conda_packages = _extract_conda_packages_from_commands(python_files)
        if command_conda_packages:
            print(f"Detected {len(command_conda_packages)} conda packages from subprocess commands")

    # Merge and deduplicate
    merged_specs = list(dict.fromkeys(package_specs + command_conda_packages))

    # Generate environment.yml
    environment_yml_path = output_path / "environment.yml"
    try:
        environment_content = generate_environment_yml_from_specs(
            merged_specs,
            pip_packages=pip_packages,
            install_project=install_project,
            project_name=project_name,
        )
        with open(environment_yml_path, "w") as f:
            f.write(environment_content)
        print(f"Created environment.yml at {environment_yml_path}")
    except Exception as e:
        raise OSError(f"Failed to create environment.yml: {e}")

    # Generate Dockerfile
    dockerfile_path = output_path / "Dockerfile"
    try:
        # Use enhanced Dockerfile generation if apt detection is enabled and Python files are provided
        if include_apt_detection and python_files:
            dockerfile_content = generate_dockerfile_for_project(
                base_image="continuumio/miniconda3:latest",
                conda_packages=merged_specs,
                python_files=python_files,
                include_apt=True,
                python_version=python_version,
                pip_packages=pip_packages,
                install_project=install_project,
                project_name=project_name,
                project_version=project_version,
                project_git_url=project_git_url,
            )
        else:
            # Use basic Dockerfile generation
            dockerfile_content = generate_dockerfile_from_specs(
                "continuumio/miniconda3:latest", merged_specs
            )
        
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        print(f"Created Dockerfile at {dockerfile_path}")
    except Exception as e:
        # Clean up environment.yml if Dockerfile creation fails
        if environment_yml_path.exists():
            environment_yml_path.unlink()
        raise OSError(f"Failed to create Dockerfile: {e}")

    # Generate lock files if enabled
    if not no_lock:
        try:
            from reciper.lockfile_generator import generate_lock_files
            
            print("\nGenerating lock files for reproducibility...")
            lock_results = generate_lock_files(
                project_dir=str(output_path),
                verbose=False,
                generate_conda=True,
                generate_pip=True
            )
            
            if lock_results.get("conda_lock"):
                print(f"Created conda lock file: {lock_results['conda_lock']}")
            if lock_results.get("pip_lock"):
                print(f"Created pip lock file: {lock_results['pip_lock']}")
                
        except ImportError as e:
            print(f"⚠️  Lock file generation unavailable: {e}")
            print("   Install required dependencies: pip install conda-lock pip-tools")
        except Exception as e:
            print(f"⚠️  Lock file generation failed: {e}")
            print("   Continuing without lock files...")
    else:
        print("ℹ️  Lock file generation disabled via --no-lock flag")


def generate_environment_yml(
    packages: list[str], versions: dict[str, str] | None = None
) -> str:
    """
    Generate environment.yml content from package names and optional version constraints.

    Args:
        packages: List of conda package names
        versions: Optional dictionary mapping package name to version constraint

    Returns:
        environment.yml content as string
    """
    # Build dependencies section
    dependencies_section = ""
    if packages:
        dependencies_lines = []
        for pkg in packages:
            if versions and pkg in versions:
                version = versions[pkg]
                dependencies_lines.append(f"  - {pkg}={version}")
            else:
                dependencies_lines.append(f"  - {pkg}")
        dependencies_section = "\ndependencies:\n" + "\n".join(dependencies_lines)

    # Detect bio packages for channel selection
    is_bio = _detect_bio_packages(packages)
    if is_bio:
        channels_section = """channels:
  - bioconda
  - conda-forge
  - defaults"""
    else:
        channels_section = """channels:
  - conda-forge
  - defaults"""

    return f"""# Generated by Reciper static analyzer
# This environment.yml file contains conda package specifications

name: generated-environment
{channels_section}
{dependencies_section}
"""


def _detect_bio_packages(package_specs: list[str]) -> bool:
    """Detect if the project is a bioinformatics pipeline based on package names."""
    bio_indicators = {
        # Python bio libraries
        "biopython", "pysam", "pybedtools", "goatools", "gffutils",
        # Common bioconda tools
        "augustus", "glimmerhmm", "snap", "trinity", "hisat2", "stringtie",
        "samtools", "bcftools", "bwa", "bowtie2", "star", "bedtools",
        "diamond", "hmmer", "exonerate", "blat", "minimap2", "mafft",
        "raxml", "iqtree", "trimal", "proteinortho", "kallisto", "salmon",
        "trimmomatic", "fastqc", "multiqc", "cutadapt", "seqtk",
        "evidencemodeler", "pasa", "codingquarry", "trnascan-se",
        "tbl2asn", "tantan", "pigz", "bamtools", "repeatmasker",
        "repeatmodeler", "interproscan", "signalp", "phobius",
        "eggnog-mapper", "busco", "prokka", "quast", "spades",
        "megahit", "canu", "flye", "racon", "pilon",
        "freebayes", "varscan", "snpeff", "snpsift", "ensembl-vep",
        "kraken2", "bracken", "metaphlan", "macs2", "meme",
        "gmap", "gsnap", "plink", "gatk4", "picard", "vcftools",
        "ncbi-blast+", "htslib", "perl", "ete3",
        # Import names that map to bio packages
        "Bio",
    }
    # Check if any package spec contains a bio indicator
    for spec in package_specs:
        spec_lower = spec.lower()
        for bio in bio_indicators:
            if bio.lower() in spec_lower:
                return True
    return False


def generate_environment_yml_from_specs(
    package_specs: list[str],
    pip_packages: list[str] | None = None,
    install_project: bool = False,
    project_name: str | None = None,
) -> str:
    """
    Generate environment.yml content from package specifications.

    Args:
        package_specs: List of package specifications (e.g., "numpy", "numpy==1.24.0", "pandas>=2.0.0")
        pip_packages: Packages that must be installed via pip
        install_project: Whether to install the project itself
        project_name: Name of the project to install via pip

    Returns:
        environment.yml content as string
    """
    # Detect if this is a bioinformatics pipeline
    is_bio = _detect_bio_packages(package_specs)

    # Build channels section
    if is_bio:
        channels_section = """channels:
  - bioconda
  - conda-forge
  - defaults"""
    else:
        channels_section = """channels:
  - conda-forge
  - defaults"""

    # Deduplicate packages (keep first occurrence)
    seen = set()
    unique_specs = []
    for spec in package_specs:
        # Extract base package name for dedup
        pkg_name = spec.split("=")[0].split(">")[0].split("<")[0].split("!")[0].split("~")[0].strip()
        if pkg_name not in seen:
            seen.add(pkg_name)
            unique_specs.append(spec)

    # Build dependencies section
    dependencies_lines = []
    for spec in unique_specs:
        dependencies_lines.append(f"  - {spec}")

    # Add pip section if there are pip-only packages or project install
    pip_deps: list[str] = list(pip_packages) if pip_packages else []
    if install_project and project_name:
        pip_deps.append(".")

    if pip_deps:
        dependencies_lines.append("  - pip:")
        for pip_pkg in pip_deps:
            dependencies_lines.append(f"    - {pip_pkg}")

    dependencies_section = "\ndependencies:\n" + "\n".join(dependencies_lines)

    return f"""# Generated by Reciper static analyzer (Week 2)
# This environment.yml file contains conda package specifications with versions

name: generated-environment
{channels_section}
{dependencies_section}
"""


def generate_dockerfile(base_image: str, packages: list[str]) -> str:
    """
    Generate Dockerfile content with specified base image and packages.

    Args:
        base_image: Base Docker image (e.g., "continuumio/miniconda3:latest")
        packages: List of conda package names to install

    Returns:
        Dockerfile content as string
    """
    # Create package install commands if packages are provided
    install_section = ""
    if packages:
        package_list = " ".join(packages)
        install_section = (
            f"\n# Install packages directly\nRUN conda install -y {package_list}"
        )

    return f"""# Generated by Reciper static analyzer
# Dockerfile for conda environment

FROM {base_image}

# Set working directory
WORKDIR /app

# Copy environment.yml (if exists)
COPY environment.yml .

# Update conda environment
RUN conda env update -f environment.yml{install_section}

# Set default command
CMD ["/bin/bash"]
"""


def generate_dockerfile_from_specs(base_image: str, package_specs: list[str]) -> str:
    """
    Generate Dockerfile content with specified base image and package specifications.

    Args:
        base_image: Base Docker image (e.g., "continuumio/miniconda3:latest")
        package_specs: List of package specifications (e.g., "numpy", "numpy==1.24.0")

    Returns:
        Dockerfile content as string
    """
    # Create package install commands if packages are provided
    install_section = ""
    if package_specs:
        # For Dockerfile, we need to handle version specifications
        # Convert package specs to conda install format
        package_list = " ".join(package_specs)
        install_section = (
            f"\n# Install packages with versions\nRUN conda install -y {package_list}"
        )

    return f"""# Generated by Reciper static analyzer (Week 2)
# Dockerfile for conda environment with version support

FROM {base_image}

# Set working directory
WORKDIR /app

# Copy environment.yml (if exists)
COPY environment.yml .

# Update conda environment
RUN conda env update -f environment.yml{install_section}

# Set default command
CMD ["/bin/bash"]
"""


def generate_dockerfile_with_apt(
    base_image: str,
    conda_packages: List[str],
    apt_packages: Optional[List[str]] = None
) -> str:
    """
    Generate Dockerfile content with conda packages and optional apt packages.
    
    Args:
        base_image: Base Docker image (e.g., "continuumio/miniconda3:latest")
        conda_packages: List of conda package specifications
        apt_packages: Optional list of apt package names to install
    
    Returns:
        Dockerfile content as string
    """
    # Create conda package install commands
    conda_install_section = ""
    if conda_packages:
        package_list = " ".join(conda_packages)
        conda_install_section = f"\n# Install conda packages\nRUN conda install -y {package_list}"
    
    # Create apt package install commands
    apt_install_section = ""
    if apt_packages:
        # Deduplicate apt packages
        unique_apt_packages = sorted(set(apt_packages))
        package_list = " ".join(unique_apt_packages)
        apt_install_section = f"""
# Install system packages via apt
RUN apt-get update && \\
    apt-get install -y --no-install-recommends {package_list} && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*"""
    
    return f"""# Generated by Reciper static analyzer with apt package support
# Dockerfile for conda environment with system dependencies

FROM {base_image}

# Set working directory
WORKDIR /app

# Update package lists and install system dependencies{apt_install_section}

# Copy environment.yml (if exists)
COPY environment.yml .

# Update conda environment{conda_install_section}

# Set default command
CMD ["/bin/bash"]
"""


def _extract_conda_packages_from_commands(
    python_files: list[Path],
) -> list[str]:
    """Scan Python files for subprocess commands and extract conda package names."""
    try:
        from reciper.command_detector import (
            detect_commands_in_file,
            map_commands_to_apt_and_conda,
        )

        all_command_calls = []
        for py_file in python_files:
            if py_file.exists() and py_file.suffix == ".py":
                command_calls = detect_commands_in_file(py_file)
                all_command_calls.extend(command_calls)

        if all_command_calls:
            _, conda_packages = map_commands_to_apt_and_conda(all_command_calls)
            return conda_packages
    except ImportError:
        pass
    return []


# Environment variables commonly needed for bioinformatics tools
# Maps conda package name → dict of ENV_VAR: value
BIO_ENV_VARS: dict[str, dict[str, str]] = {
    "augustus": {
        "AUGUSTUS_CONFIG_PATH": "/opt/conda/share/augustus/config",
    },
    "evidencemodeler": {
        "EVM_HOME": "/opt/conda/opt/evidencemodeler",
    },
    "pasa": {
        "PASAHOME": "/opt/conda/opt/pasa",
    },
    "trinity": {
        "TRINITY_HOME": "/opt/conda/opt/trinity",
    },
    "codingquarry": {
        "QUARRY_PATH": "/opt/conda/opt/codingquarry/QuarryFiles",
    },
    "snap": {
        "ZOE": "/opt/conda/share/snap",
    },
    "glimmerhmm": {
        "GLIMMERHMM": "/opt/conda/opt/glimmerhmm",
    },
    "genemark": {
        "GENEMARK_PATH": "/opt/conda/opt/gmes_petap.pl",
    },
    "repeatmasker": {
        "REPEATMASKER_DIR": "/opt/conda/share/repeatmasker",
    },
    "trnascan-se": {
        "TRNASCAN_HOME": "/opt/conda/share/trnascan-se",
    },
}


def _collect_env_vars(conda_packages: list[str]) -> dict[str, str]:
    """Collect environment variables for detected conda packages."""
    env_vars: dict[str, str] = {}
    for pkg in conda_packages:
        pkg_lower = pkg.lower().replace("-", "").replace("_", "")
        for known_pkg, vars_dict in BIO_ENV_VARS.items():
            known_lower = known_pkg.lower().replace("-", "").replace("_", "")
            # Fuzzy match: check if one contains the other
            if known_lower in pkg_lower or pkg_lower in known_lower:
                env_vars.update(vars_dict)
    return env_vars


def generate_dockerfile_for_project(
    base_image: str,
    conda_packages: list[str],
    python_files: list[Path],
    include_apt: bool = True,
    python_version: str | None = None,
    pip_packages: list[str] | None = None,
    is_bio: bool = True,
    install_project: bool = False,
    project_name: str | None = None,
    project_version: str | None = None,
    project_git_url: str | None = None,
) -> str:
    """
    Generate Dockerfile for a project with command detection for apt packages.

    Now also extracts conda packages from subprocess commands and merges them
    into the conda install section.

    Args:
        base_image: Base Docker image
        conda_packages: List of conda package specifications (from Python imports)
        python_files: List of Python files to scan for command calls
        include_apt: Whether to include apt package detection
        python_version: Python version constraint from setup.py (e.g. ">=3.6, <3.12")
        pip_packages: Packages that must be installed via pip
        is_bio: Whether this is a bioinformatics pipeline

    Returns:
        Dockerfile content as string
    """
    apt_packages: list[str] = []
    command_conda_packages: list[str] = []

    if include_apt and python_files:
        try:
            from reciper.command_detector import (
                detect_commands_in_file,
                map_commands_to_apt_and_conda,
            )

            # Detect commands in all Python files
            all_command_calls = []
            for py_file in python_files:
                if py_file.exists() and py_file.suffix == ".py":
                    command_calls = detect_commands_in_file(py_file)
                    all_command_calls.extend(command_calls)

            # Map commands to BOTH apt and conda packages
            if all_command_calls:
                apt_pkg_objects, command_conda_packages = map_commands_to_apt_and_conda(
                    all_command_calls
                )
                apt_packages = [pkg.package_name for pkg in apt_pkg_objects]

        except ImportError:
            pass

    # Merge conda packages from imports + from commands (deduplicated)
    import_conda: list[str] = []
    for spec in conda_packages:
        if spec.startswith("conda:"):
            pkg_name = spec[6:].strip().split("=")[0].split(">")[0].split("<")[0].strip()
            if pkg_name:
                import_conda.append(pkg_name)
        else:
            pkg_name = spec.split("=")[0].split(">")[0].split("<")[0].strip()
            import_conda.append(pkg_name)

    # Combine and deduplicate preserving order
    all_conda_names = list(dict.fromkeys(import_conda + command_conda_packages))

    # Collect environment variables
    env_vars = _collect_env_vars(all_conda_names)

    # Generate Dockerfile with apt + merged conda + env vars + python version + pip
    return _generate_dockerfile_with_apt_and_env(
        base_image=base_image,
        conda_packages=all_conda_names,
        apt_packages=apt_packages,
        env_vars=env_vars,
        python_version=python_version,
        pip_packages=pip_packages,
        is_bio=is_bio,
        install_project=install_project,
        project_name=project_name,
        project_version=project_version,
        project_git_url=project_git_url,
    )


def _generate_dockerfile_with_apt_and_env(
    base_image: str,
    conda_packages: list[str],
    apt_packages: list[str] | None = None,
    env_vars: dict[str, str] | None = None,
    python_version: str | None = None,
    pip_packages: list[str] | None = None,
    is_bio: bool = True,
    install_project: bool = False,
    project_name: str | None = None,
    project_version: str | None = None,
    project_git_url: str | None = None,
) -> str:
    """Generate a multi-stage Dockerfile with conda, apt, pip, env vars, and Python version constraint."""

    # Determine Python version constraint
    if python_version:
        # Parse something like ">=3.6.0, <3.12" → use the upper bound or lower bound
        # conda uses something like python=3.11
        # We'll use a safe default based on the constraint
        if "<3.9" in python_version or "<3.10" in python_version:
            py_constraint = "python=3.8"
        elif "<3.12" in python_version:
            py_constraint = "python=3.11"
        elif ">=3.8" in python_version:
            py_constraint = "python>=3.8"
        else:
            py_constraint = "python>=3.8"
    else:
        py_constraint = "python>=3.8"

    # Build conda install command
    conda_pkg_list = " ".join(conda_packages) if conda_packages else ""

    # Apt install section
    apt_section = ""
    if apt_packages:
        unique_apt = sorted(set(apt_packages))
        apt_section = f"""
# Install system packages via apt
RUN apt-get update && \\
    apt-get install -y --no-install-recommends {" ".join(unique_apt)} && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*"""

    # Pip install section
    pip_section = ""
    if pip_packages:
        pip_section = f'\n# Install pip-only packages\nRUN /opt/conda/envs/env/bin/pip install --no-cache-dir {" ".join(pip_packages)}'

    # Project self-install section
    project_install_section = ""
    if install_project:
        if project_git_url:
            project_install_section = f'\n# Install {project_name} from Git\nRUN /opt/conda/envs/env/bin/pip install --no-cache-dir {project_git_url}'
        else:
            project_install_section = f"""
# Install {project_name or 'project'} from source
COPY . /app/project
WORKDIR /app/project
RUN /opt/conda/envs/env/bin/pip install --no-cache-dir ."""

    # Environment variables section
    env_section = ""
    if env_vars:
        env_lines = ["\n# Environment variables for bioinformatics tools"]
        env_lines.append("ENV \\")
        items = sorted(env_vars.items())
        for i, (key, val) in enumerate(items):
            if i < len(items) - 1:
                env_lines.append(f'    {key}="{val}" \\')
            else:
                env_lines.append(f'    {key}="{val}"')
        env_section = "\n".join(env_lines)

    # Bio channels
    if is_bio:
        channels_cmd = f"RUN conda config --add channels bioconda && conda config --add channels conda-forge"
    else:
        channels_cmd = "RUN conda config --add channels conda-forge"

    return f"""# Generated by Reciper static analyzer
# Multi-stage Dockerfile for bioinformatics pipeline

# ─── Build stage ───────────────────────────────────────────────────────────────
FROM continuumio/miniconda3:latest AS build

# Set working directory
WORKDIR /app

# Install system dependencies{apt_section}

# Configure conda channels
{channels_cmd}

# Create conda environment with {py_constraint}
RUN conda create -n env {py_constraint} {conda_pkg_list} -y && \\
    conda clean -a -y
{pip_section}
{project_install_section}

# ─── Runtime stage ─────────────────────────────────────────────────────────────
FROM continuumio/miniconda3:latest AS runtime

# Copy conda environment from build stage
COPY --from=build /opt/conda /opt/conda

# Install minimal runtime system dependencies
RUN apt-get update && \\
    apt-get install -y --no-install-recommends procps && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

# Set PATH
ENV PATH="/opt/conda/bin:$PATH"
{env_section}

# Set working directory
WORKDIR /data

# Set default command
CMD ["/bin/bash"]
"""


def parse_package_spec(spec: str) -> tuple[str, str | None]:
    """
    Parse a package specification into name and version.

    Args:
        spec: Package specification (e.g., "numpy", "numpy==1.24.0", "pandas>=2.0.0")

    Returns:
        Tuple of (package_name, version_constraint)
    """
    # Check for version operators
    operators = ["==", ">=", "<=", ">", "<", "!=", "~=", "="]

    for op in operators:
        if op in spec:
            parts = spec.split(op, 1)
            if len(parts) == 2:
                return parts[0].strip(), f"{op}{parts[1].strip()}"

    # No version operator found
    return spec.strip(), None


if __name__ == "__main__":
    """Test the generator module with sample conda specifications."""

    print("Testing generator module - Week 2 Version Support")
    print("=" * 60)

    # Test 1: Basic specifications without versions
    sample_specs_basic = [
        "conda: numpy",
        "conda: pandas",
        "conda: scikit-learn",
        "conda: matplotlib",
    ]

    print("\nTest 1: Basic specifications without versions")
    print(f"Sample conda specifications: {sample_specs_basic}")

    try:
        # Create test output directory
        test_dir = Path("test_output_basic")
        test_dir.mkdir(exist_ok=True)

        # Generate files
        generate_files(sample_specs_basic, output_dir=str(test_dir))

        print("\nFiles generated successfully:")
        print(f"  - {test_dir / 'environment.yml'}")
        print(f"  - {test_dir / 'Dockerfile'}")

        # Display generated content
        print("\n--- environment.yml content ---")
        with open(test_dir / "environment.yml") as f:
            print(f.read())

        print("\n--- Dockerfile content ---")
        with open(test_dir / "Dockerfile") as f:
            print(f.read())

    except Exception as e:
        print(f"Error during test 1: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Specifications with versions
    sample_specs_with_versions = [
        "conda: numpy==1.24.0",
        "conda: pandas>=2.0.0",
        "conda: scikit-learn<1.3.0",
        "conda: matplotlib",
    ]

    print("\n" + "=" * 60)
    print("\nTest 2: Specifications with versions")
    print(f"Sample conda specifications: {sample_specs_with_versions}")

    try:
        # Create test output directory
        test_dir2 = Path("test_output_versions")
        test_dir2.mkdir(exist_ok=True)

        # Generate files
        generate_files(sample_specs_with_versions, output_dir=str(test_dir2))

        print("\nFiles generated successfully:")
        print(f"  - {test_dir2 / 'environment.yml'}")
        print(f"  - {test_dir2 / 'Dockerfile'}")

        # Display generated content
        print("\n--- environment.yml content ---")
        with open(test_dir2 / "environment.yml") as f:
            print(f.read())

        print("\n--- Dockerfile content ---")
        with open(test_dir2 / "Dockerfile") as f:
            print(f.read())

    except Exception as e:
        print(f"Error during test 2: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Parse package spec function
    print("\n" + "=" * 60)
    print("\nTest 3: Parse package specification function")

    test_specs = [
        "numpy",
        "numpy==1.24.0",
        "pandas>=2.0.0",
        "scikit-learn<1.3.0",
        "matplotlib~=3.7.0",
    ]

    for spec in test_specs:
        name, version = parse_package_spec(spec)
        print(f"  '{spec}' -> name: '{name}', version: '{version}'")

    # Test 4: Environment.yml generation with versions
    print("\n" + "=" * 60)
    print("\nTest 4: Environment.yml generation with versions")

    package_specs = [
        "numpy==1.24.0",
        "pandas>=2.0.0",
        "scikit-learn",
        "matplotlib<3.5.0",
    ]
    env_content = generate_environment_yml_from_specs(package_specs)
    print("Generated environment.yml content:")
    print(env_content)

    # Test 5: Dockerfile generation with versions
    print("\n" + "=" * 60)
    print("\nTest 5: Dockerfile generation with versions")

    docker_content = generate_dockerfile_from_specs(
        "continuumio/miniconda3:latest", package_specs
    )
    print("Generated Dockerfile content:")
    print(docker_content)

    print("\n" + "=" * 60)
    print("All generator tests completed!")

    # Cleanup test directories
    import shutil

    for dir_path in [Path("test_output_basic"), Path("test_output_versions")]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Cleaned up {dir_path}")
