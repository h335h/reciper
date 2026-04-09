"""
Lockfile generator for Reciper.

This module provides functionality to generate lock files for reproducible environments:
1. conda-lock.yml from environment.yml (conda-lock style)
2. requirements-locked.txt from requirements.txt (pip-compile style)

Lock files pin exact versions of all dependencies for reproducibility.
"""

import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys
import json


class LockfileGenerator:
    """Generator for lock files to ensure reproducible environments."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def generate_conda_lock(
        self, 
        environment_yml_path: Path, 
        output_path: Optional[Path] = None,
        platforms: Optional[List[str]] = None
    ) -> Path:
        """
        Generate conda-lock.yml from environment.yml.
        
        Args:
            environment_yml_path: Path to environment.yml file
            output_path: Optional output path for lock file (default: same directory as input)
            platforms: List of platforms to lock for (default: ["linux-64"])
            
        Returns:
            Path to generated lock file
            
        Raises:
            FileNotFoundError: If environment.yml doesn't exist
            subprocess.CalledProcessError: If conda-lock command fails
            RuntimeError: If conda-lock is not installed
        """
        if not environment_yml_path.exists():
            raise FileNotFoundError(f"Environment file not found: {environment_yml_path}")
        
        if output_path is None:
            output_path = environment_yml_path.parent / "conda-lock.yml"
        
        if platforms is None:
            platforms = ["linux-64"]
        
        # Check if conda-lock is available
        try:
            subprocess.run(
                ["conda-lock", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "conda-lock is not installed. Install with: conda install -c conda-forge conda-lock"
            )
        
        # Build conda-lock command
        cmd = [
            "conda-lock",
            "lock",
            "--file", str(environment_yml_path),
            "--lockfile", str(output_path),
        ]
        
        # Add platform flags
        for platform in platforms:
            cmd.extend(["--platform", platform])
        
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
        
        # Run conda-lock
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.verbose:
                print(f"conda-lock stdout: {result.stdout}")
                if result.stderr:
                    print(f"conda-lock stderr: {result.stderr}")
            
            print(f"Generated conda lock file: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"conda-lock failed with exit code {e.returncode}: {e.stderr}"
            if self.verbose:
                error_msg += f"\nCommand: {' '.join(cmd)}"
            raise subprocess.CalledProcessError(e.returncode, cmd, output=e.stdout, stderr=e.stderr)
    
    def generate_pip_lock(
        self,
        requirements_path: Path,
        output_path: Optional[Path] = None,
        upgrade: bool = False,
        generate_hashes: bool = False
    ) -> Path:
        """
        Generate requirements-locked.txt from requirements.txt using pip-compile.
        
        Args:
            requirements_path: Path to requirements.txt file
            output_path: Optional output path for lock file (default: requirements-locked.txt in same directory)
            upgrade: Whether to upgrade packages to latest versions
            generate_hashes: Whether to generate hashes for packages
            
        Returns:
            Path to generated lock file
            
        Raises:
            FileNotFoundError: If requirements.txt doesn't exist
            subprocess.CalledProcessError: If pip-compile command fails
            RuntimeError: If pip-tools is not installed
        """
        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")
        
        if output_path is None:
            output_path = requirements_path.parent / "requirements-locked.txt"
        
        # Check if pip-compile is available
        try:
            subprocess.run(
                ["pip-compile", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "pip-tools is not installed. Install with: pip install pip-tools"
            )
        
        # Build pip-compile command
        cmd = [
            "pip-compile",
            str(requirements_path),
            "--output-file", str(output_path),
            "--verbose" if self.verbose else "--quiet",
        ]
        
        if upgrade:
            cmd.append("--upgrade")
        
        if generate_hashes:
            cmd.append("--generate-hashes")
        
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
        
        # Run pip-compile
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.verbose:
                print(f"pip-compile stdout: {result.stdout}")
                if result.stderr:
                    print(f"pip-compile stderr: {result.stderr}")
            
            print(f"Generated pip lock file: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"pip-compile failed with exit code {e.returncode}: {e.stderr}"
            if self.verbose:
                error_msg += f"\nCommand: {' '.join(cmd)}"
            raise subprocess.CalledProcessError(e.returncode, cmd, output=e.stdout, stderr=e.stderr)
    
    def generate_lock_files_for_project(
        self,
        project_dir: Path,
        generate_conda_lock: bool = True,
        generate_pip_lock: bool = True,
        conda_platforms: Optional[List[str]] = None
    ) -> Dict[str, Optional[Path]]:
        """
        Generate lock files for a project directory.
        
        Args:
            project_dir: Project directory to scan for dependency files
            generate_conda_lock: Whether to generate conda lock file
            generate_pip_lock: Whether to generate pip lock file
            conda_platforms: Platforms for conda-lock (default: ["linux-64"])
            
        Returns:
            Dictionary with paths to generated lock files (or None if not generated)
        """
        results = {
            "conda_lock": None,
            "pip_lock": None
        }
        
        if conda_platforms is None:
            conda_platforms = ["linux-64"]
        
        # Look for environment.yml
        environment_yml = project_dir / "environment.yml"
        if generate_conda_lock and environment_yml.exists():
            try:
                lock_file = self.generate_conda_lock(
                    environment_yml_path=environment_yml,
                    platforms=conda_platforms
                )
                results["conda_lock"] = lock_file
            except Exception as e:
                print(f"Warning: Failed to generate conda lock file: {e}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
        
        # Look for requirements.txt
        requirements_txt = project_dir / "requirements.txt"
        if generate_pip_lock and requirements_txt.exists():
            try:
                lock_file = self.generate_pip_lock(
                    requirements_path=requirements_txt
                )
                results["pip_lock"] = lock_file
            except Exception as e:
                print(f"Warning: Failed to generate pip lock file: {e}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
        
        return results
    
    def simulate_conda_lock(
        self,
        environment_yml_path: Path,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Simulate conda-lock generation without actually running conda-lock.
        Returns the expected structure of the lock file.
        
        This is useful when conda-lock is not available or for testing.
        """
        if not environment_yml_path.exists():
            raise FileNotFoundError(f"Environment file not found: {environment_yml_path}")
        
        if platforms is None:
            platforms = ["linux-64"]
        
        # Parse environment.yml
        with open(environment_yml_path, 'r') as f:
            env_data = yaml.safe_load(f)
        
        # Extract dependencies
        dependencies = env_data.get('dependencies', [])
        conda_deps = []
        pip_deps = []
        
        for dep in dependencies:
            if isinstance(dep, str):
                conda_deps.append(dep)
            elif isinstance(dep, dict) and 'pip' in dep:
                pip_deps.extend(dep['pip'])
        
        # Create simulated lock file structure
        lock_data = {
            "metadata": {
                "content_hash": {
                    platform: "simulated_hash" for platform in platforms
                },
                "channels": env_data.get('channels', ['conda-forge', 'defaults']),
                "platforms": platforms,
                "sources": [str(environment_yml_path)],
                "time_created": "2023-01-01T00:00:00Z",  # Placeholder
            },
            "package": []
        }
        
        # Add simulated packages
        for dep in conda_deps:
            # Parse package name and version
            parts = dep.split()
            name = parts[0]
            version = parts[1] if len(parts) > 1 else "1.0.0"
            
            for platform in platforms:
                lock_data["package"].append({
                    "name": name,
                    "version": version,
                    "manager": "conda",
                    "platform": platform,
                    "dependencies": [],  # Simplified
                    "url": f"https://anaconda.org/conda-forge/{name}/{version}/download/{platform}/{name}-{version}.tar.bz2",
                    "hash": {
                        "md5": "simulated_md5_hash",
                        "sha256": "simulated_sha256_hash"
                    }
                })
        
        return lock_data
    
    def simulate_pip_lock(
        self,
        requirements_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Simulate pip-compile generation without actually running pip-compile.
        Returns the expected structure of the lock file.
        
        This is useful when pip-tools is not available or for testing.
        """
        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {requirements_path}")
        
        # Parse requirements.txt
        from reciper.requirements_parser import parse_requirements_file
        
        try:
            requirements = parse_requirements_file(requirements_path)
        except Exception:
            # Fallback simple parsing
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
            
            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
        
        # Create simulated lock file entries
        lock_entries = []
        for req in requirements:
            if hasattr(req, 'name'):
                # It's a PackageRequirement object
                name = req.name
                version = req.version_constraint or "1.0.0"
                # Remove version operators for simulation
                if version.startswith("=="):
                    version = version[2:]
                elif version.startswith(">="):
                    version = version[2:]
                elif version.startswith("<="):
                    version = version[2:]
                elif version.startswith(">"):
                    version = version[1:]
                elif version.startswith("<"):
                    version = version[1:]
                elif version.startswith("~="):
                    version = version[2:]
                elif version.startswith("!="):
                    version = version[2:]
            else:
                # It's a string
                req_str = str(req)
                # Simple parsing
                if '==' in req_str:
                    name, version = req_str.split('==', 1)
                elif '>=' in req_str:
                    name, version = req_str.split('>=', 1)
                elif '<=' in req_str:
                    name, version = req_str.split('<=', 1)
                elif '>' in req_str:
                    name, version = req_str.split('>', 1)
                elif '<' in req_str:
                    name, version = req_str.split('<', 1)
                elif '~=' in req_str:
                    name, version = req_str.split('~=', 1)
                elif '!=' in req_str:
                    name, version = req_str.split('!=', 1)
                else:
                    name = req_str
                    version = "1.0.0"
            
            lock_entries.append({
                "name": name.strip(),
                "version": version.strip(),
                "hash": "sha256:simulated_hash",
                "source": "pypi",
                "dependencies": []  # Simplified
            })
        
        return lock_entries


def generate_lock_files(
    project_dir: str,
    verbose: bool = False,
    generate_conda: bool = True,
    generate_pip: bool = True
) -> Dict[str, Optional[str]]:
    """
    Convenience function to generate lock files for a project.
    
    Args:
        project_dir: Path to project directory
        verbose: Whether to print verbose output
        generate_conda: Whether to generate conda lock file
        generate_pip: Whether to generate pip lock file
        
    Returns:
        Dictionary with paths to generated lock files (as strings)
    """
    generator = LockfileGenerator(verbose=verbose)
    project_path = Path(project_dir)
    
    results = generator.generate_lock_files_for_project(
        project_dir=project_path,
        generate_conda_lock=generate_conda,
        generate_pip_lock=generate_pip
    )
    
    # Convert Path objects to strings
    return {
        "conda_lock": str(results["conda_lock"]) if results["conda_lock"] else None,
        "pip_lock": str(results["pip_lock"]) if results["pip_lock"] else None
    }


if __name__ == "__main__":
    """Test the lockfile generator module."""
    import tempfile
    import os
    
    print("Testing Lockfile Generator")
    print("=" * 60)
    
    # Create a test directory with sample dependency files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create sample environment.yml
        env_yml = tmp_path / "environment.yml"
        env_yml.write_text("""name: test-environment
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - numpy
  - pandas
  - pip
  - pip:
    - requests
    - beautifulsoup4
""")
        
        # Create sample requirements.txt
        req_txt = tmp_path / "requirements.txt"
        req_txt.write_text("""numpy>=1.21.0
pandas>=1.3.0
scikit-learn
matplotlib
# Comment line
requests>=2.26.0
""")
        
        print(f"Created test files in: {tmpdir}")
        print(f"  - {env_yml.name}")
        print(f"  - {req_txt.name}")
        
        # Test simulation (doesn't require external tools)
        print("\n1. Testing simulation (no external tools required):")
        generator = LockfileGenerator(verbose=True)
        
        try:
            # Simulate conda lock
            conda_sim = generator.simulate_conda_lock(env_yml)
            print(f"   ✓ Simulated conda lock with {len(conda_sim['package'])} packages")
            
            # Simulate pip lock
            pip_sim = generator.simulate_pip_lock(req_txt)
            print(f"   ✓ Simulated pip lock with {len(pip_sim)} packages")
            
        except Exception as e:
            print(f"   ✗ Simulation failed: {e}")
        
        # Test actual generation (if tools are available)
        print("\n2. Testing actual lock file generation:")
        print("   Note: This requires conda-lock and pip-tools to be installed.")
        
        try:
            # Try to generate conda lock
            try:
                conda_lock = generator.generate_conda_lock(env_yml)
                print(f"   ✓ Generated conda lock: {conda_lock.name}")
            except RuntimeError as e:
                print(f"   ⚠ Skipping conda lock: {e}")
            except Exception as e:
                print(f"   ✗ Conda lock generation failed: {e}")
            
            # Try to generate pip lock
            try:
                pip_lock = generator.generate_pip_lock(req_txt)
                print(f"   ✓ Generated pip lock: {pip_lock.name}")
            except RuntimeError as e:
                print(f"   ⚠ Skipping pip lock: {e}")
            except Exception as e:
                print(f"   ✗ Pip lock generation failed: {e}")
                
        except Exception as e:
            print(f"   ✗ Lock generation failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test convenience function
        print("\n3. Testing convenience function:")
        try:
            results = generate_lock_files(tmpdir, verbose=False)
            print(f"   Results: {results}")
        except Exception as e:
            print(f"   ✗ Convenience function failed: {e}")
    
    print("\n" + "=" * 60)
    print("Lockfile generator tests completed!")
    print("=" * 60)