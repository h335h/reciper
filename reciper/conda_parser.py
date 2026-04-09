"""
Conda environment.yml parser for Reciper.

This module provides functionality to parse conda environment.yml files and extract
package names with version constraints for integration with the static analyzer.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from reciper.requirements_parser import PackageRequirement


@dataclass
class CondaPackage:
    """Represents a conda package with version constraints."""
    
    name: str
    version: str | None = None
    channel: str | None = None  # e.g., conda-forge, bioconda, defaults
    build: str | None = None
    source: str = "environment.yml"
    
    def to_package_requirement(self) -> PackageRequirement:
        """Convert to PackageRequirement for consistency with other parsers."""
        version_constraint = f"=={self.version}" if self.version else None
        return PackageRequirement(
            name=self.name.lower(),
            version_constraint=version_constraint,
            line_number=None,
            raw_line=f"{self.name}={self.version}" if self.version else self.name,
            source=f"conda:{self.source}",
            editable=False,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "channel": self.channel,
            "build": self.build,
            "source": self.source,
        }


def parse_environment_yml(file_path: Path) -> list[CondaPackage]:
    """
    Parse a conda environment.yml file and extract package specifications.
    
    Args:
        file_path: Path to environment.yml file
        
    Returns:
        List of CondaPackage objects
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
        ValueError: If file cannot be parsed as YAML or has invalid structure
    """
    if not file_path.exists():
        raise FileNotFoundError(f"environment.yml file not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    if yaml is None:
        raise ImportError(
            "PyYAML library is required to parse environment.yml files. "
            "Install with 'pip install pyyaml'."
        )
    
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, PermissionError) as e:
        raise PermissionError(f"Cannot read environment.yml file {file_path}: {e}")
    
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in environment.yml file {file_path}: {e}")
    
    packages: list[CondaPackage] = []
    
    # Extract channels
    channels = data.get("channels", [])
    default_channel = "defaults"  # conda default channel
    
    # Extract dependencies
    dependencies = data.get("dependencies", [])
    
    for dep in dependencies:
        if isinstance(dep, str):
            # Regular package specification: "package=version", "package", "package=version=build"
            package = parse_conda_package_spec(dep, channels, default_channel)
            if package:
                packages.append(package)
        
        elif isinstance(dep, dict) and "pip" in dep:
            # Pip dependencies section
            pip_deps = dep["pip"]
            if isinstance(pip_deps, list):
                for pip_dep in pip_deps:
                    if isinstance(pip_dep, str):
                        # Convert pip dependency to conda package if possible
                        package = convert_pip_to_conda_spec(pip_dep, channels)
                        if package:
                            packages.append(package)
    
    return packages


def parse_conda_package_spec(
    spec: str, 
    channels: list[str], 
    default_channel: str = "defaults"
) -> CondaPackage | None:
    """
    Parse a conda package specification string.
    
    Args:
        spec: Package specification string (e.g., "numpy=1.21.0", "conda-forge::biopython")
        channels: List of channels from environment.yml
        default_channel: Default channel to use if not specified
        
    Returns:
        CondaPackage object if parsing succeeds, None otherwise
    """
    if not spec or not isinstance(spec, str):
        return None
    
    # Check for channel specification: "channel::package"
    channel = None
    package_spec = spec
    
    if "::" in spec:
        channel_part, package_spec = spec.split("::", 1)
        channel = channel_part.strip()
    
    # Parse package name, version, and build
    # Formats: "package", "package=version", "package=version=build"
    parts = package_spec.split("=")
    
    if len(parts) == 1:
        # Just package name
        name = parts[0].strip()
        version = None
        build = None
    elif len(parts) == 2:
        # Package and version
        name = parts[0].strip()
        version = parts[1].strip()
        build = None
    elif len(parts) >= 3:
        # Package, version, and build (and possibly more)
        name = parts[0].strip()
        version = parts[1].strip()
        build = parts[2].strip()
    else:
        # Invalid format
        return None
    
    if not name:
        return None
    
    # If channel not specified in package, use first channel from environment.yml
    # or default channel
    if not channel and channels:
        channel = channels[0]
    elif not channel:
        channel = default_channel
    
    return CondaPackage(
        name=name,
        version=version,
        channel=channel,
        build=build,
        source="environment.yml",
    )


def convert_pip_to_conda_spec(pip_spec: str, channels: list[str]) -> CondaPackage | None:
    """
    Convert a pip package specification to a conda package specification.
    
    Args:
        pip_spec: Pip package specification (e.g., "numpy==1.21.0", "pandas>=1.3.0")
        channels: List of channels from environment.yml
        
    Returns:
        CondaPackage object if conversion is possible, None otherwise
    """
    # Parse pip specification using requirements_parser
    from reciper.requirements_parser import parse_requirements_line
    
    requirement = parse_requirements_line(pip_spec, line_number=0, source="pip-in-conda")
    if not requirement:
        return None
    
    # Convert version constraint from pip to conda format
    version = None
    if requirement.version_constraint:
        # Remove pip operators and keep just the version
        # pip: "==1.21.0", ">=1.3.0" -> conda: "1.21.0", "1.3.0"
        # For conda, we only support exact versions from pip constraints
        version_match = re.search(r"[=!<>~]+([0-9a-zA-Z_\-\.*+!]+)", requirement.version_constraint)
        if version_match:
            version = version_match.group(1)
    
    # Determine channel - prefer conda-forge for Python packages
    channel = "conda-forge" if "conda-forge" in channels else (channels[0] if channels else "conda-forge")
    
    return CondaPackage(
        name=requirement.name,
        version=version,
        channel=channel,
        build=None,
        source="pip-in-conda",
    )


def environment_yml_to_package_requirements(file_path: Path) -> list[PackageRequirement]:
    """
    Convert environment.yml to list of PackageRequirement objects.
    
    Args:
        file_path: Path to environment.yml file
        
    Returns:
        List of PackageRequirement objects
    """
    conda_packages = parse_environment_yml(file_path)
    return [pkg.to_package_requirement() for pkg in conda_packages]


if __name__ == "__main__":
    """Test the conda parser module."""
    import tempfile
    
    # Create a test environment.yml file
    test_content = """name: test-env
channels:
  - conda-forge
  - bioconda
  - defaults
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pandas>=1.3.0
  - bioconda::samtools=1.14
  - scikit-learn
  - pip:
    - requests==2.26.0
    - matplotlib<3.5.0
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(test_content)
        test_file = Path(f.name)
    
    try:
        print(f"Testing conda parser with file: {test_file}")
        
        # Parse the file
        packages = parse_environment_yml(test_file)
        
        print(f"\nFound {len(packages)} packages:")
        for pkg in packages:
            print(f"  - {pkg.name}={pkg.version} (channel: {pkg.channel}, source: {pkg.source})")
        
        # Convert to PackageRequirement
        requirements = environment_yml_to_package_requirements(test_file)
        
        print(f"\nConverted to {len(requirements)} PackageRequirement objects:")
        for req in requirements:
            print(f"  - {req.name}{req.version_constraint or ''} (source: {req.source})")
        
    finally:
        # Clean up
        test_file.unlink()