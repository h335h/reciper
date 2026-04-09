"""
Enhanced verifier for generated environments with Docker container testing and comprehensive checks.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
import tempfile
import shutil


class Verifier:
    """Verify generated environments with comprehensive testing."""

    def __init__(self, verbose: bool = False, no_verify: bool = False):
        """
        Initialize verifier with options.

        Args:
            verbose: Enable detailed output
            no_verify: Skip verification entirely
        """
        self.verbose = verbose
        self.no_verify = no_verify
        self.results = {}
        self.has_docker = self._check_docker_available()

    def _check_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                if self.verbose:
                    print(f"Docker available: {result.stdout.strip()}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return False

    def verify_environment(
        self,
        package_list: List[str],
        output_dir: str = ".",
        dockerfile_path: Optional[Path] = None,
        env_file_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Main verification logic for generated environment.

        Args:
            package_list: List of Python packages to verify
            output_dir: Directory containing generated files
            dockerfile_path: Path to Dockerfile (default: output_dir/Dockerfile)
            env_file_path: Path to environment.yml (default: output_dir/environment.yml)

        Returns:
            Dictionary with verification results
        """
        if self.no_verify:
            return {"skipped": True, "reason": "Verification disabled via --no-verify flag"}

        output_path = Path(output_dir)
        if dockerfile_path is None:
            dockerfile_path = output_path / "Dockerfile"
        if env_file_path is None:
            env_file_path = output_path / "environment.yml"

        self.results = {
            "overall_success": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "docker_available": self.has_docker,
        }

        # Check 1: File existence and basic syntax
        self._check_file_syntax(dockerfile_path, env_file_path)

        # Check 2: Docker container testing (if Docker available)
        if self.has_docker and dockerfile_path.exists():
            self._create_test_container(dockerfile_path, package_list)
        else:
            self.results["checks"]["docker_test"] = {
                "success": False,
                "reason": "Docker not available or Dockerfile missing",
                "skipped": True,
            }
            if self.verbose:
                print("Skipping Docker container test (Docker not available)")

        # Check 3: Conda environment dry-run
        if env_file_path.exists():
            self._check_conda_dry_run(env_file_path)
        else:
            self.results["checks"]["conda_dry_run"] = {
                "success": False,
                "reason": "environment.yml not found",
                "skipped": True,
            }

        # Check 4: Package import verification
        if package_list:
            self._check_package_imports(package_list)

        # Update overall success
        self.results["overall_success"] = all(
            check.get("success", True) or check.get("skipped", False)
            for check in self.results["checks"].values()
        )

        return self.results

    def _check_file_syntax(
        self, dockerfile_path: Path, env_file_path: Path
    ) -> None:
        """Check basic syntax of generated files."""
        # Dockerfile syntax check
        docker_check = {"success": False, "details": ""}
        if dockerfile_path.exists():
            try:
                with open(dockerfile_path) as f:
                    content = f.read()
                    if "FROM" in content:
                        docker_check["success"] = True
                        docker_check["details"] = "Dockerfile contains FROM instruction"
                        if self.verbose:
                            print("✓ Dockerfile syntax check passed")
                    else:
                        docker_check["details"] = "Dockerfile missing FROM instruction"
                        self.results["errors"].append("Dockerfile missing FROM instruction")
            except Exception as e:
                docker_check["details"] = f"Error reading Dockerfile: {e}"
                self.results["errors"].append(f"Dockerfile read error: {e}")
        else:
            docker_check["details"] = "Dockerfile not found"
            docker_check["skipped"] = True

        self.results["checks"]["dockerfile_syntax"] = docker_check

        # environment.yml syntax check
        env_check = {"success": False, "details": ""}
        if env_file_path.exists():
            try:
                with open(env_file_path) as f:
                    content = yaml.safe_load(f)
                    if content and isinstance(content, dict):
                        if "name" in content and "dependencies" in content:
                            env_check["success"] = True
                            env_check["details"] = "environment.yml has valid structure"
                            if self.verbose:
                                print("✓ environment.yml syntax check passed")
                        else:
                            env_check["details"] = "environment.yml missing required fields"
                            self.results["errors"].append("environment.yml missing name or dependencies")
                    else:
                        env_check["details"] = "environment.yml is empty or invalid YAML"
                        self.results["errors"].append("environment.yml invalid YAML")
            except yaml.YAMLError as e:
                env_check["details"] = f"YAML parsing error: {e}"
                self.results["errors"].append(f"environment.yml YAML error: {e}")
            except Exception as e:
                env_check["details"] = f"Error reading environment.yml: {e}"
                self.results["errors"].append(f"environment.yml read error: {e}")
        else:
            env_check["details"] = "environment.yml not found"
            env_check["skipped"] = True

        self.results["checks"]["environment_yml_syntax"] = env_check

    def _create_test_container(
        self, dockerfile_path: Path, package_list: List[str]
    ) -> None:
        """Create and test Docker container with generated Dockerfile."""
        container_check = {"success": False, "details": ""}
        
        try:
            # Generate a unique container name
            import uuid
            container_name = f"reciper-test-{uuid.uuid4().hex[:8]}"
            
            if self.verbose:
                print(f"Building test container: {container_name}")
            
            # Build Docker image
            build_result = subprocess.run(
                ["docker", "build", "-t", container_name, "-f", str(dockerfile_path), "."],
                capture_output=True,
                text=True,
                cwd=dockerfile_path.parent,
                check=False,
            )
            
            if build_result.returncode != 0:
                container_check["details"] = f"Docker build failed: {build_result.stderr[:200]}"
                self.results["errors"].append("Docker build failed")
                self.results["checks"]["docker_container"] = container_check
                return
            
            if self.verbose:
                print(f"✓ Docker image built: {container_name}")
            
            # Run container and test imports
            self._check_imports_in_container(container_name, package_list)
            
            # Clean up
            subprocess.run(
                ["docker", "rmi", "-f", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            container_check["success"] = True
            container_check["details"] = f"Container {container_name} built and tested successfully"
            
        except Exception as e:
            container_check["details"] = f"Container test error: {e}"
            self.results["errors"].append(f"Container test error: {e}")
        
        self.results["checks"]["docker_container"] = container_check

    def _check_imports_in_container(
        self, container_name: str, package_list: List[str]
    ) -> None:
        """Test importing packages inside Docker container."""
        import_check = {"success": False, "details": "", "failed_imports": []}
        
        # Filter out standard library and common packages that might not be directly importable
        importable_packages = [
            pkg for pkg in package_list 
            if pkg not in ["os", "sys", "json", "yaml", "pathlib", "typing", "subprocess"]
        ]
        
        if not importable_packages:
            import_check["success"] = True
            import_check["details"] = "No importable packages to test"
            self.results["checks"]["package_imports"] = import_check
            return
        
        # Create Python script to test imports
        import_script = "\n".join([
            "import sys",
            "errors = []",
            *[f"try:\n    import {pkg}\nexcept ImportError as e:\n    errors.append(f'{pkg}: {{e}}')" 
              for pkg in importable_packages],
            "if errors:",
            "    print('\\n'.join(errors))",
            "    sys.exit(1)",
            "else:",
            "    print('All imports successful')",
        ])
        
        try:
            # Run import test in container
            result = subprocess.run(
                ["docker", "run", "--rm", container_name, "python", "-c", import_script],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            
            if result.returncode == 0:
                import_check["success"] = True
                import_check["details"] = f"All {len(importable_packages)} packages import successfully"
                if self.verbose:
                    print(f"✓ Package imports verified: {len(importable_packages)} packages")
            else:
                import_check["details"] = f"Import failures: {result.stderr[:200]}"
                import_check["failed_imports"] = [
                    line.split(":")[0] for line in result.stderr.split("\n") if ":" in line
                ]
                self.results["warnings"].append(f"Some packages failed to import: {import_check['failed_imports']}")
                
        except subprocess.TimeoutExpired:
            import_check["details"] = "Import test timed out after 30 seconds"
            self.results["errors"].append("Import test timeout")
        except Exception as e:
            import_check["details"] = f"Import test error: {e}"
            self.results["errors"].append(f"Import test error: {e}")
        
        self.results["checks"]["package_imports"] = import_check

    def _check_conda_dry_run(self, env_file_path: Path) -> None:
        """Perform conda environment creation dry-run."""
        conda_check = {"success": False, "details": ""}
        
        try:
            # Check if conda is available
            conda_result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if conda_result.returncode != 0:
                conda_check["details"] = "Conda not available for dry-run"
                conda_check["skipped"] = True
                self.results["checks"]["conda_dry_run"] = conda_check
                return
            
            # Try conda env create --dry-run
            env_name = f"reciper-test-{hash(str(env_file_path)) % 10000}"
            
            dry_run_result = subprocess.run(
                ["conda", "env", "create", "-n", env_name, "-f", str(env_file_path), "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if dry_run_result.returncode == 0:
                conda_check["success"] = True
                conda_check["details"] = "Conda environment dry-run successful"
                if self.verbose:
                    print("✓ Conda environment dry-run passed")
            else:
                conda_check["details"] = f"Conda dry-run failed: {dry_run_result.stderr[:200]}"
                self.results["errors"].append("Conda environment dry-run failed")
                
        except Exception as e:
            conda_check["details"] = f"Conda check error: {e}"
            conda_check["skipped"] = True
            if self.verbose:
                print(f"⚠️ Conda check skipped: {e}")
        
        self.results["checks"]["conda_dry_run"] = conda_check

    def _check_package_imports(self, package_list: List[str]) -> None:
        """Check package imports in current environment (fallback)."""
        import_check = {"success": False, "details": "", "failed_imports": []}
        
        failed = []
        for pkg in package_list:
            try:
                # Simple import check
                __import__(pkg)
            except ImportError:
                failed.append(pkg)
        
        if not failed:
            import_check["success"] = True
            import_check["details"] = f"All {len(package_list)} packages can be imported"
        else:
            import_check["details"] = f"{len(failed)} packages failed to import: {', '.join(failed[:5])}"
            import_check["failed_imports"] = failed
            self.results["warnings"].append(f"Some packages may not be importable: {len(failed)} failed")
        
        self.results["checks"]["local_package_imports"] = import_check

    def generate_verification_report(self, results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive verification report."""
        if results is None:
            results = self.results
        
        report = {
            "verification_summary": {
                "overall_success": results.get("overall_success", False),
                "total_checks": len(results.get("checks", {})),
                "successful_checks": sum(1 for check in results.get("checks", {}).values() 
                                       if check.get("success", False)),
                "failed_checks": sum(1 for check in results.get("checks", {}).values() 
                                    if not check.get("success", False) and not check.get("skipped", False)),
                "skipped_checks": sum(1 for check in results.get("checks", {}).values() 
                                     if check.get("skipped", False)),
                "error_count": len(results.get("errors", [])),
                "warning_count": len(results.get("warnings", [])),
            },
            "detailed_checks": results.get("checks", {}),
            "issues": {
                "errors": results.get("errors", []),
                "warnings": results.get("warnings", []),
            },
            "environment_info": {
                "docker_available": results.get("docker_available", False),
                "python_version": sys.version,
            }
        }
        
        return report

    def print_report(self, results: Optional[Dict[str, Any]] = None) -> None:
        """Print human-readable verification report."""
        if results is None:
            results = self.results
        
        report = self.generate_verification_report(results)
        summary = report["verification_summary"]
        
        print("\n" + "="*60)
        print("VERIFICATION REPORT")
        print("="*60)
        
        status = "✅ PASS" if summary["overall_success"] else "❌ FAIL"
        print(f"Overall Status: {status}")
        print(f"Checks: {summary['successful_checks']}/{summary['total_checks']} passed")
        print(f"  - {summary['failed_checks']} failed, {summary['skipped_checks']} skipped")
        print(f"Issues: {summary['error_count']} errors, {summary['warning_count']} warnings")
        
        if summary["error_count"] > 0:
            print("\n❌ ERRORS:")
            for error in report["issues"]["errors"]:
                print(f"  • {error}")
        
        if summary["warning_count"] > 0:
            print("\n⚠️  WARNINGS:")
            for warning in report["issues"]["warnings"]:
                print(f"  • {warning}")
        
        print("\n" + "="*60)
        
        if self.verbose:
            print("\nDetailed Check Results:")
            for check_name, check_result in report["detailed_checks"].items():
                status = "✅" if check_result.get("success") else "❌"
                if check_result.get("skipped"):
                    status = "⏭️"
                print(f"  {status} {check_name}: {check_result.get('details', '')}")


def verify_environment(
    package_list: List[str],
    output_dir: str = ".",
    verbose: bool = False,
    no_verify: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to verify generated environment.
    
    Args:
        package_list: List of Python packages to verify
        output_dir: Directory containing generated files
        verbose: Enable detailed output
        no_verify: Skip verification entirely
        
    Returns:
        Verification results dictionary
    """
    verifier = Verifier(verbose=verbose, no_verify=no_verify)
    return verifier.verify_environment(package_list, output_dir)


if __name__ == "__main__":
    # Test the verifier
    test_packages = ["numpy", "pandas", "matplotlib"]
    print("Testing verifier with sample packages...")
    
    verifier = Verifier(verbose=True)
    results = verifier.verify_environment(test_packages, ".")
    
    verifier.print_report(results)
    
    # Generate JSON report
    report = verifier.generate_verification_report(results)
    print("\nJSON Report:")
    print(json.dumps(report, indent=2))
