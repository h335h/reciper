"""
Requirements.txt parser for RECIPER Static Analyzer MVP.

This module provides functionality to parse requirements.txt files and extract
package names with version constraints.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PackageRequirement:
    """Represents a package requirement with version constraints."""

    name: str
    version_constraint: str | None = None
    line_number: int | None = None
    raw_line: str | None = None
    source: str = "requirements.txt"  # Source file: requirements.txt, pyproject.toml, setup.py, or "fallback"
    editable: bool = False  # Whether this is an editable install (-e)

    def __str__(self) -> str:
        """Return string representation of package requirement.

        Returns:
            String in format "package==version" or "package" if no version.
        """
        if self.version_constraint:
            return f"{self.name}{self.version_constraint}"
        return self.name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version_constraint,
            "source": self.source,
            "line_number": self.line_number,
            "editable": self.editable,
        }


def extract_package_name_from_editable(editable_spec: str) -> str | None:
    """
    Extract package name from an editable install specification.
    
    Args:
        editable_spec: Editable specification (e.g., ".", "./my_package", "git+https://...")
        
    Returns:
        Package name if it can be extracted, None otherwise
    """
    import os
    from pathlib import Path
    
    # If it's a local path, try to get package name from setup.py or pyproject.toml
    if editable_spec.startswith((".", "/", "~")):
        # Resolve the path
        try:
            path = Path(editable_spec).expanduser().resolve()
            
            # Check for common package configuration files
            if (path / "setup.py").exists():
                # Try to extract name from setup.py (simplified)
                try:
                    with open(path / "setup.py", "r") as f:
                        content = f.read()
                        # Look for name='package_name' pattern
                        import re
                        match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                        if match:
                            return match.group(1)
                except:
                    pass
            
            if (path / "pyproject.toml").exists():
                # Try to extract name from pyproject.toml (simplified)
                try:
                    with open(path / "pyproject.toml", "r") as f:
                        content = f.read()
                        # Look for [project] name = "package_name"
                        import re
                        match = re.search(r'\[project\][^[]*name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL)
                        if match:
                            return match.group(1)
                except:
                    pass
            
            # Fallback: use directory name
            return path.name
            
        except Exception:
            return None
    
    # If it's a VCS URL, try to extract from the URL
    elif editable_spec.startswith(("git+", "svn+", "hg+", "bzr+")):
        # Remove VCS prefix
        url = editable_spec.split("+", 1)[1] if "+" in editable_spec else editable_spec
        
        # Try to extract package name from URL
        # Common patterns: git+https://github.com/user/repo.git
        #                  git+https://github.com/user/repo@branch
        import re
        match = re.search(r"/([^/@]+?)(?:\.git)?(?:[@#].*)?$", url)
        if match:
            return match.group(1).replace("_", "-").lower()
    
    # If it's a direct package name (unlikely but possible)
    elif re.match(r"^[a-zA-Z0-9_\-\.]+$", editable_spec):
        return editable_spec
    
    return None


def extract_package_name_from_url(url_line: str) -> str | None:
    """
    Extract package name from a URL requirement.
    
    Args:
        url_line: URL requirement line (e.g., "git+https://github.com/user/repo.git")
        
    Returns:
        Package name if it can be extracted, None otherwise
    """
    import re
    
    # Remove VCS prefixes if present
    url = url_line
    if url.startswith(("git+", "svn+", "hg+", "bzr+")):
        url = url.split("+", 1)[1]
    
    # Remove any fragment or query parameters
    url = url.split("#")[0].split("?")[0]
    
    # Common patterns for extracting package names from URLs:
    
    # 1. GitHub/GitLab/Bitbucket patterns
    #    https://github.com/user/repo.git
    #    https://gitlab.com/user/repo.git
    #    https://bitbucket.org/user/repo.git
    github_pattern = r"github\.com/[^/]+/([^/.]+)"
    gitlab_pattern = r"gitlab\.com/[^/]+/([^/.]+)"
    bitbucket_pattern = r"bitbucket\.org/[^/]+/([^/.]+)"
    
    for pattern in [github_pattern, gitlab_pattern, bitbucket_pattern]:
        match = re.search(pattern, url)
        if match:
            package_name = match.group(1)
            # Remove .git suffix if present
            if package_name.endswith(".git"):
                package_name = package_name[:-4]
            return package_name.replace("_", "-").lower()
    
    # 2. PyPI direct URLs
    #    https://files.pythonhosted.org/packages/.../package-version.tar.gz
    pypi_pattern = r"/([^/-]+)-[0-9]+\.[0-9]+(\.[0-9]+)?\.(tar\.gz|zip|whl)"
    match = re.search(pypi_pattern, url)
    if match:
        return match.group(1).replace("_", "-").lower()
    
    # 3. Generic pattern for any URL ending with package name
    #    Look for something that looks like a package name before .tar.gz, .zip, etc.
    generic_pattern = r"/([^/-]+?)(?:-[0-9]+\.[0-9]+)?\.(?:tar\.gz|zip|whl|tgz)$"
    match = re.search(generic_pattern, url)
    if match:
        return match.group(1).replace("_", "-").lower()
    
    # 4. Try to extract from the last part of the path
    #    /path/to/package or /path/to/package/
    path_parts = url.split("/")
    if len(path_parts) >= 2:
        last_part = path_parts[-1] or path_parts[-2]
        # Clean up the last part
        last_part = last_part.split(".")[0]  # Remove extension
        last_part = last_part.split("@")[0]  # Remove branch/tag
        last_part = last_part.split("#")[0]  # Remove fragment
        
        # Check if it looks like a package name
        if re.match(r"^[a-zA-Z0-9_\-\.]+$", last_part) and len(last_part) > 1:
            return last_part.replace("_", "-").lower()
    
    return None


def parse_requirements_line(
    line: str, line_number: int = 0, source: str = "requirements.txt"
) -> PackageRequirement | None:
    """
    Parse a single line from a requirements.txt file.

    Args:
        line: The line to parse (already stripped of whitespace)
        line_number: Line number for error reporting
        source: Source file type (requirements.txt, pyproject.toml, setup.py)

    Returns:
        PackageRequirement object if line contains a package requirement, None otherwise

    Supported formats:
        - package==version
        - package>=version
        - package<=version
        - package>version
        - package<version
        - package~=version (compatible release)
        - package (no version)
        - package[extra]==version (extras)

    Note: This function should only receive regular package requirements.
    Special directives (-r, -e, URL requirements) are handled by parse_requirements_file.
    """
    # Skip environment markers (anything after ;)
    if ";" in line:
        line = line.split(";")[0].strip()

    # Skip platform-specific markers (anything after #)
    if "#" in line:
        line = line.split("#")[0].strip()

    # Pattern for package name with optional extras and version constraint
    # Examples:
    #   numpy
    #   numpy==1.20.0
    #   numpy>=1.20
    #   numpy[extra]==1.20.0
    #   numpy-pandas (hyphenated names)
    #   numpy.pandas (dotted names)

    # Match package name (can include letters, numbers, underscores, hyphens, dots)
    # May include extras in brackets: package[extra1,extra2]
    package_pattern = r"^([a-zA-Z0-9_\-\.]+(?:\[[a-zA-Z0-9_\-\. ,]+\])?)"

    # Match version constraint operators: ==, !=, <=, >=, <, >, ~=, ===
    version_pattern = r"([=!<>~]+)\s*([a-zA-Z0-9_\-\.*+!]+)"

    # Try to match package with version constraint
    match_with_version = re.match(rf"{package_pattern}\s*{version_pattern}", line)
    if match_with_version:
        package_name = match_with_version.group(1)
        operator = match_with_version.group(2)
        version = match_with_version.group(3)
        version_constraint = f"{operator}{version}"

        # Clean up package name (remove extras for now)
        if "[" in package_name:
            # Extract base package name before extras
            base_name = package_name.split("[")[0]
        else:
            base_name = package_name

        return PackageRequirement(
            name=base_name.lower(),  # Normalize to lowercase
            version_constraint=version_constraint,
            line_number=line_number,
            raw_line=line,
            source=source,
        )

    # Try to match package without version constraint
    match_no_version = re.match(
        r"^([a-zA-Z0-9_\-\.]+(?:\[[a-zA-Z0-9_\-\. ,]+\])?)$", line
    )
    if match_no_version:
        package_name = match_no_version.group(1)

        # Clean up package name
        if "[" in package_name:
            base_name = package_name.split("[")[0]
        else:
            base_name = package_name

        return PackageRequirement(
            name=base_name.lower(),
            version_constraint=None,
            line_number=line_number,
            raw_line=line,
            source=source,
        )

    # If we get here, the line doesn't match any known pattern
    # Could be a malformed line or unsupported format
    return None


def parse_requirements_file(file_path: Path) -> list[PackageRequirement]:
    """
    Parse a requirements.txt file and extract package requirements.

    Args:
        file_path: Path to requirements.txt file

    Returns:
        List of PackageRequirement objects

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
        ValueError: If file cannot be parsed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Requirements file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    requirements: list[PackageRequirement] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, PermissionError) as e:
        raise PermissionError(f"Cannot read requirements file {file_path}: {e}")

    for line_number, line in enumerate(lines, start=1):
        try:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle recursive requirements (-r or --requirement)
            if line.startswith("-r ") or line.startswith("--requirement "):
                # Extract the referenced file path
                parts = line.split()
                if len(parts) < 2:
                    print(
                        f"Warning: Malformed -r directive at line {line_number}: {line}",
                        file=sys.stderr,
                    )
                    continue

                ref_path = parts[1].strip()
                # Resolve relative to the current file's directory
                ref_file = file_path.parent / ref_path

                if not ref_file.exists():
                    print(
                        f"Warning: Referenced requirements file not found: {ref_file}",
                        file=sys.stderr,
                    )
                    continue

                # Recursively parse the referenced file
                try:
                    ref_requirements = parse_requirements_file(ref_file)
                    requirements.extend(ref_requirements)
                except Exception as e:
                    print(
                        f"Warning: Could not parse referenced file {ref_file}: {e}",
                        file=sys.stderr,
                    )
                continue

            # Handle editable installs (-e or --editable)
            if line.startswith("-e ") or line.startswith("--editable "):
                # Extract the path/URL after -e
                parts = line.split()
                if len(parts) < 2:
                    print(
                        f"Warning: Malformed -e directive at line {line_number}: {line}",
                        file=sys.stderr,
                    )
                    continue
                
                editable_spec = parts[1].strip()
                package_name = extract_package_name_from_editable(editable_spec)
                
                if package_name:
                    requirement = PackageRequirement(
                        name=package_name.lower(),
                        version_constraint=None,
                        line_number=line_number,
                        raw_line=line,
                        source="requirements.txt (editable)",
                        editable=True,
                    )
                    requirements.append(requirement)
                    print(
                        f"Info: Added editable package '{package_name}' from {editable_spec}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Warning: Could not extract package name from editable install: {editable_spec}",
                        file=sys.stderr,
                    )
                continue

            # Handle URL-based requirements
            if line.startswith(("http://", "https://", "git+", "svn+", "hg+", "bzr+")):
                package_name = extract_package_name_from_url(line)
                
                if package_name:
                    requirement = PackageRequirement(
                        name=package_name.lower(),
                        version_constraint=None,
                        line_number=line_number,
                        raw_line=line,
                        source="requirements.txt (URL)",
                        editable=False,
                    )
                    requirements.append(requirement)
                    print(
                        f"Info: Added package '{package_name}' from URL: {line[:50]}...",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Warning: Could not extract package name from URL requirement: {line[:50]}...",
                        file=sys.stderr,
                    )
                continue

            # Parse regular package requirement
            requirement = parse_requirements_line(
                line, line_number, source="requirements.txt"
            )
            if requirement:
                requirements.append(requirement)

        except Exception:
            # Skip malformed lines but continue parsing
            print(
                f"Warning: Could not parse line {line_number} in {file_path}: {line.strip()}",
                file=sys.stderr,
            )
            continue

    return requirements


def parse_pyproject_dependency(dep_spec: str, source: str = "pyproject.toml") -> PackageRequirement | None:
    """
    Parse a dependency specification from pyproject.toml.
    
    Args:
        dep_spec: Dependency specification string
        source: Source information for the requirement
        
    Returns:
        PackageRequirement object if parsing succeeds, None otherwise
    """
    # Pyproject.toml dependencies can have markers after ;
    # Format: "package>=1.0; python_version>='3.8'"
    if ";" in dep_spec:
        dep_spec = dep_spec.split(";")[0].strip()
    
    # Handle extras: "package[extra1,extra2]>=1.0"
    # We'll parse it using the existing parse_requirements_line function
    # but we need to handle it as a line without line number
    try:
        # Use parse_requirements_line with line_number=0
        requirement = parse_requirements_line(dep_spec, line_number=0, source=source)
        return requirement
    except Exception:
        # If parsing fails, try to extract package name manually
        import re
        
        # Simple pattern to extract package name
        # Handles: package, package>=1.0, package[extra], package[extra]>=1.0
        match = re.match(r"^([a-zA-Z0-9_\-\.]+(?:\[[a-zA-Z0-9_\-\. ,]+\])?)", dep_spec)
        if match:
            package_name = match.group(1)
            # Remove extras for the base name
            if "[" in package_name:
                base_name = package_name.split("[")[0]
            else:
                base_name = package_name
            
            # Try to extract version constraint
            version_constraint = None
            version_match = re.search(r"([=!<>~]+[a-zA-Z0-9_\-\.*+!]+)", dep_spec)
            if version_match:
                version_constraint = version_match.group(1)
            
            return PackageRequirement(
                name=base_name.lower(),
                version_constraint=version_constraint,
                line_number=None,
                raw_line=dep_spec,
                source=source,
                editable=False,
            )
    
    return None


def parse_pyproject_toml(file_path: Path) -> list[PackageRequirement]:
    """
    Parse a pyproject.toml file and extract dependencies.

    Args:
        file_path: Path to pyproject.toml file

    Returns:
        List of PackageRequirement objects

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
        ValueError: If file cannot be parsed as TOML
    """
    if not file_path.exists():
        raise FileNotFoundError(f"pyproject.toml file not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    requirements: list[PackageRequirement] = []
    
    try:
        # Try to import toml library
        try:
            import toml
        except ImportError:
            # Fallback to tomli for Python 3.11+ or if toml is not installed
            try:
                import tomli as toml
            except ImportError:
                print(
                    "Warning: Neither 'toml' nor 'tomli' library is available. "
                    "Install with 'pip install toml' or 'pip install tomli'.",
                    file=sys.stderr,
                )
                return []
        
        with open(file_path, "rb") as f:
            data = toml.load(f)
        
        # Extract dependencies from PEP 621 format ([project.dependencies])
        if "project" in data and "dependencies" in data["project"]:
            deps = data["project"]["dependencies"]
            for dep in deps:
                requirement = parse_pyproject_dependency(dep, source="pyproject.toml (project)")
                if requirement:
                    requirements.append(requirement)
        
        # Extract optional dependencies (extras)
        if "project" in data and "optional-dependencies" in data["project"]:
            optional_deps = data["project"]["optional-dependencies"]
            for extra_name, extra_deps in optional_deps.items():
                for dep in extra_deps:
                    requirement = parse_pyproject_dependency(
                        dep,
                        source=f"pyproject.toml (optional:{extra_name})"
                    )
                    if requirement:
                        requirements.append(requirement)
        
        # Extract dependencies from Poetry format ([tool.poetry.dependencies])
        if "tool" in data and "poetry" in data["tool"] and "dependencies" in data["tool"]["poetry"]:
            poetry_deps = data["tool"]["poetry"]["dependencies"]
            for dep_name, dep_spec in poetry_deps.items():
                if dep_name.lower() == "python":
                    continue  # Skip Python version specifier
                
                if isinstance(dep_spec, str):
                    requirement = parse_pyproject_dependency(
                        f"{dep_name}{dep_spec}" if dep_spec else dep_name,
                        source="pyproject.toml (poetry)"
                    )
                elif isinstance(dep_spec, dict) and "version" in dep_spec:
                    version = dep_spec["version"]
                    requirement = parse_pyproject_dependency(
                        f"{dep_name}{version}",
                        source="pyproject.toml (poetry)"
                    )
                else:
                    requirement = PackageRequirement(
                        name=dep_name.lower(),
                        version_constraint=None,
                        line_number=None,
                        raw_line=str(dep_spec),
                        source="pyproject.toml (poetry)",
                        editable=False,
                    )
                
                if requirement:
                    requirements.append(requirement)
        
        # Extract dependencies from Flit format ([tool.flit.metadata])
        if "tool" in data and "flit" in data["tool"] and "metadata" in data["tool"]["flit"]:
            flit_metadata = data["tool"]["flit"]["metadata"]
            if "requires" in flit_metadata:
                flit_deps = flit_metadata["requires"]
                for dep in flit_deps:
                    requirement = parse_pyproject_dependency(dep, source="pyproject.toml (flit)")
                    if requirement:
                        requirements.append(requirement)
        
    except Exception as e:
        raise ValueError(f"Failed to parse pyproject.toml file {file_path}: {e}")
    
    return requirements


def parse_setup_py(file_path: Path) -> list[PackageRequirement]:
    """
    Parse a setup.py file and extract dependencies.

    Args:
        file_path: Path to setup.py file

    Returns:
        List of PackageRequirement objects

    Note: This is a simplified parser that only handles basic cases.
    """
    # TODO: Implement setup.py parsing in Week 2
    # For now, return empty list
    return []


def parse_dependency_file(file_path: Path) -> list[PackageRequirement]:
    """
    Parse any supported dependency file (requirements.txt, pyproject.toml, setup.py, environment.yml).

    Args:
        file_path: Path to dependency file

    Returns:
        List of PackageRequirement objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Dependency file not found: {file_path}")

    file_name = file_path.name.lower()
    
    if file_name == "requirements.txt":
        return parse_requirements_file(file_path)
    elif file_name == "pyproject.toml":
        return parse_pyproject_toml(file_path)
    elif file_name == "setup.py":
        return parse_setup_py(file_path)
    elif file_name in ["environment.yml", "environment.yaml"]:
        try:
            from reciper.conda_parser import environment_yml_to_package_requirements
            return environment_yml_to_package_requirements(file_path)
        except ImportError as e:
            print(
                f"Warning: Could not parse environment.yml file: {e}. "
                "Make sure PyYAML is installed with 'pip install pyyaml'.",
                file=sys.stderr,
            )
            return []
    else:
        raise ValueError(f"Unsupported dependency file format: {file_path.name}")


def requirements_to_dict(
    requirements: list[PackageRequirement],
) -> dict[str, str | None]:
    """
    Convert list of PackageRequirement objects to a dictionary.

    Args:
        requirements: List of PackageRequirement objects

    Returns:
        Dictionary mapping package names to version constraints (or None)
    """
    result: dict[str, str | None] = {}

    for req in requirements:
        # If package appears multiple times, keep the first occurrence
        if req.name not in result:
            result[req.name] = req.version_constraint

    return result


def compare_with_imports(
    requirements: dict[str, str | None], imports: list[str]
) -> dict[str, Any]:
    """
    Compare requirements with imported packages.

    Args:
        requirements: Dictionary of package requirements
        imports: List of imported package names

    Returns:
        Dictionary with comparison results
    """
    imported_set = set(imports)
    required_set = set(requirements.keys())

    # Packages that are both required and imported
    matched = imported_set.intersection(required_set)

    # Packages that are imported but not in requirements
    missing = imported_set - required_set

    # Packages that are in requirements but not imported
    extra = required_set - imported_set

    return {
        "matched": sorted(matched),
        "missing": sorted(missing),
        "extra": sorted(extra),
        "import_count": len(imported_set),
        "requirement_count": len(required_set),
        "match_count": len(matched),
        "missing_count": len(missing),
        "extra_count": len(extra),
    }


def resolve_package_versions(
    imports: list[str],
    requirements: list[PackageRequirement],
    default_mapping: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Resolve package versions by matching imports with requirements.

    Args:
        imports: List of imported package names
        requirements: List of PackageRequirement objects from dependency files
        default_mapping: Optional default mapping for packages not in requirements

    Returns:
        List of resolved package specifications with version and source information
    """
    # Convert requirements to dictionary for easy lookup
    req_dict: dict[str, PackageRequirement] = {}
    for req in requirements:
        if req.name not in req_dict:
            req_dict[req.name] = req

    resolved_packages = []

    for pkg in imports:
        if pkg in req_dict:
            # Package found in requirements
            req = req_dict[pkg]
            resolved_packages.append(
                {
                    "name": pkg,
                    "version": req.version_constraint,
                    "source": req.source,
                    "mapped": True,
                }
            )
        elif default_mapping and pkg in default_mapping:
            # Package in default mapping (e.g., from mapper.py)
            resolved_packages.append(
                {"name": pkg, "version": "latest", "source": "fallback", "mapped": True}
            )
        else:
            # Package not found in requirements or default mapping
            resolved_packages.append(
                {"name": pkg, "version": None, "source": "unmapped", "mapped": False}
            )

    return resolved_packages


def requirements_to_dict_with_source(
    requirements: list[PackageRequirement],
) -> dict[str, dict[str, Any]]:
    """
    Convert list of PackageRequirement objects to a dictionary with source information.

    Args:
        requirements: List of PackageRequirement objects

    Returns:
        Dictionary mapping package names to full requirement information
    """
    result: dict[str, dict[str, Any]] = {}

    for req in requirements:
        # If package appears multiple times, keep the first occurrence
        if req.name not in result:
            result[req.name] = {
                "version": req.version_constraint,
                "source": req.source,
                "line_number": req.line_number,
                "raw_line": req.raw_line,
            }

    return result


def extract_version_from_constraint(version_constraint: str | None) -> str | None:
    """
    Extract version number from version constraint string.

    Args:
        version_constraint: Version constraint string (e.g., "==1.20.0", ">=1.3.0")

    Returns:
        Version number without operator, or None if no version
    """
    if not version_constraint:
        return None

    # Remove operator characters: ==, !=, <=, >=, <, >, ~=, ===
    version = re.sub(r"^[=!<>~]+", "", version_constraint)
    return version.strip() if version else None


if __name__ == "__main__":
    """Test the requirements parser module."""
    import tempfile

    # Create a test requirements.txt file
    test_content = """# This is a comment
numpy==1.20.0
pandas>=1.3.0
scikit-learn
matplotlib<3.5.0
requests[security]>=2.25.0
-r other_requirements.txt
# Another comment
django~=3.2.0
flask
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_content)
        test_file = Path(f.name)

    try:
        print(f"Testing requirements parser with file: {test_file}")

        # Parse the file
        requirements = parse_requirements_file(test_file)

        print(f"\nParsed {len(requirements)} package requirements:")
        for req in requirements:
            print(
                f"  Line {req.line_number}: {req.name} -> {req.version_constraint or 'no version'}"
            )

        # Convert to dictionary
        req_dict = requirements_to_dict(requirements)
        print(f"\nRequirements dictionary ({len(req_dict)} packages):")
        for name, version in req_dict.items():
            print(f"  {name}: {version}")

        # Test comparison with imports
        test_imports = ["numpy", "pandas", "matplotlib", "unknown_package"]
        comparison = compare_with_imports(req_dict, test_imports)

        print(f"\nComparison with imports {test_imports}:")
        print(f"  Matched packages: {comparison['matched']}")
        print(f"  Missing from requirements: {comparison['missing']}")
        print(f"  Extra in requirements: {comparison['extra']}")

        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)
