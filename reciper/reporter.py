"""
JSON Reporter for RECIPER Static Analyzer MVP.

This module provides functionality to generate comprehensive JSON reports
with scan summaries, package resolution details, and analysis results.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from reciper.requirements_parser import (
    PackageRequirement,
)


@dataclass
class ScanMetrics:
    """Metrics collected during scanning."""

    total_files: int = 0
    python_files: int = 0
    scan_time_seconds: float = 0.0
    start_time: float | None = None
    end_time: float | None = None

    def start(self) -> None:
        """Start timing the scan."""
        self.start_time = time.time()

    def stop(self) -> None:
        """Stop timing the scan."""
        if self.start_time:
            self.end_time = time.time()
            self.scan_time_seconds = self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_files": self.total_files,
            "python_files": self.python_files,
            "scan_time_seconds": round(self.scan_time_seconds, 3),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat()
            if self.start_time
            else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
        }


class JSONReporter:
    """Generates JSON reports for RECIPER static analysis results."""

    def __init__(self, scan_directory: str | Path):
        """
        Initialize JSON reporter.

        Args:
            scan_directory: Directory that was scanned
        """
        self.scan_directory = Path(scan_directory)
        self.metrics = ScanMetrics()
        self.detected_imports: list[str] = []
        self.requirements: list[PackageRequirement] = []
        self.mapped_packages: list[dict[str, Any]] = []
        self.unmapped_imports: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.conflicts: list[dict[str, Any]] = []
        self.verification_results: dict[str, Any] = {}
        self.generated_files: dict[str, bool] = {
            "dockerfile": False,
            "environment_yml": False,
            "lock_files": False,
        }

    def set_scan_metrics(self, total_files: int, python_files: int) -> None:
        """
        Set scan metrics.

        Args:
            total_files: Total number of files scanned
            python_files: Number of Python files found
        """
        self.metrics.total_files = total_files
        self.metrics.python_files = python_files

    def set_detected_imports(self, imports: list[str]) -> None:
        """
        Set detected imports from Python files.

        Args:
            imports: List of imported package names
        """
        self.detected_imports = sorted(imports)

    def set_requirements(self, requirements: list[PackageRequirement]) -> None:
        """
        Set parsed requirements from dependency files.

        Args:
            requirements: List of PackageRequirement objects
        """
        self.requirements = requirements

    def set_mapped_packages(self, mapped_packages: list[dict[str, Any]]) -> None:
        """
        Set mapped packages with version information.

        Args:
            mapped_packages: List of mapped package dictionaries
        """
        self.mapped_packages = mapped_packages

    def set_unmapped_imports(self, unmapped_imports: list[dict[str, Any]]) -> None:
        """
        Set unmapped imports with file/line information.

        Args:
            unmapped_imports: List of unmapped import dictionaries
        """
        self.unmapped_imports = unmapped_imports

    def add_warning(self, warning: str) -> None:
        """
        Add a warning message.

        Args:
            warning: Warning message
        """
        self.warnings.append(warning)

    def set_conflicts(self, conflicts: list[dict[str, Any]]) -> None:
        """
        Set package conflict detection results.

        Args:
            conflicts: List of conflict dictionaries from ConflictDetector
        """
        self.conflicts = conflicts

    def add_conflict(self, conflict: dict[str, Any]) -> None:
        """
        Add a single conflict.

        Args:
            conflict: Conflict dictionary
        """
        self.conflicts.append(conflict)

    def set_verification_results(self, verification_results: dict[str, Any]) -> None:
        """
        Set verification results from verifier.

        Args:
            verification_results: Dictionary with verification results from Verifier
        """
        self.verification_results = verification_results

    def set_generated_files(
        self,
        dockerfile: bool,
        environment_yml: bool,
        lock_files: bool = False
    ) -> None:
        """
        Set which files were generated.

        Args:
            dockerfile: Whether Dockerfile was generated
            environment_yml: Whether environment.yml was generated
            lock_files: Whether lock files were generated
        """
        self.generated_files["dockerfile"] = dockerfile
        self.generated_files["environment_yml"] = environment_yml
        self.generated_files["lock_files"] = lock_files

    def generate_report(self) -> dict[str, Any]:
        """
        Generate comprehensive JSON report.

        Returns:
            Dictionary containing the full report
        """
        # Stop timing if not already stopped
        if self.metrics.start_time and not self.metrics.end_time:
            self.metrics.stop()

        # Requirements analysis
        requirements_found = len(self.requirements) > 0
        requirements_path = None
        if self.requirements:
            # Get the first requirement's source file path
            source_files = {req.source for req in self.requirements}
            if source_files:
                requirements_path = list(source_files)[0]

        # Create mapped packages list with simplified structure
        simplified_mapped = []
        for pkg in self.mapped_packages:
            simplified_mapped.append(
                {
                    "name": pkg.get("name", ""),
                    "version": pkg.get("version", "latest"),
                    "source": pkg.get("source", "fallback"),
                }
            )

        # Create unmapped imports list
        unmapped_list = []
        for imp in self.unmapped_imports:
            unmapped_list.append(
                {
                    "name": imp.get("name", ""),
                    "file": str(imp.get("file", "")),
                    "line": imp.get("line", 0),
                }
            )

        # Create conflict analysis section
        conflict_analysis = {
            "detected": len(self.conflicts) > 0,
            "total_conflicts": len(self.conflicts),
            "errors": len([c for c in self.conflicts if c.get("severity") == "error"]),
            "warnings": len([c for c in self.conflicts if c.get("severity") == "warning"]),
            "conflicts": self.conflicts,
        }

        # Create verification section if results exist
        verification_section = {}
        if self.verification_results:
            verification_section = {
                "performed": True,
                "overall_success": self.verification_results.get("overall_success", False),
                "docker_available": self.verification_results.get("docker_available", False),
                "checks_performed": len(self.verification_results.get("checks", {})),
                "errors": len(self.verification_results.get("errors", [])),
                "warnings": len(self.verification_results.get("warnings", [])),
                "summary": self.verification_results.get("checks", {}),
            }
        else:
            verification_section = {
                "performed": False,
                "reason": "Verification not performed or disabled",
            }

        report = {
            "scan_summary": self.metrics.to_dict(),
            "scan_directory": str(self.scan_directory),
            "detected_imports": self.detected_imports,
            "requirements_analysis": {
                "found": requirements_found,
                "path": requirements_path,
                "package_count": len(self.requirements),
                "packages": [
                    {
                        "name": req.name,
                        "version": req.version_constraint,
                        "source": req.source,
                        "line_number": req.line_number,
                    }
                    for req in self.requirements
                ],
            },
            "mapped_packages": simplified_mapped,
            "unmapped_imports": unmapped_list,
            "warnings": self.warnings,
            "conflict_analysis": conflict_analysis,
            "verification": verification_section,
            "generated_files": self.generated_files,
            "timestamp": datetime.now().isoformat(),
            "reciper_version": "0.3.0",  # Week 3 release with CLI extensions
        }

        return report

    def save_report(self, output_path: str | Path) -> None:
        """
        Save JSON report to file.

        Args:
            output_path: Path where JSON report should be saved

        Raises:
            OSError: If file cannot be written
        """
        report = self.generate_report()
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except (OSError, PermissionError) as e:
            raise OSError(f"Cannot write JSON report to {output_path}: {e}")

    def print_report(self) -> None:
        """Print JSON report to stdout in human-readable format.

        Generates the report and prints it with indentation for readability.
        """
        report = self.generate_report()
        print(json.dumps(report, indent=2))


def create_report_from_analysis(
    scan_directory: str | Path,
    file_infos: list[Any],  # List of FileInfo objects from scanner
    imports: list[str],
    requirements: list[PackageRequirement],
    mapped_packages: list[dict[str, Any]],
    unmapped_imports: list[dict[str, Any]],
    warnings: list[str],
    dockerfile_generated: bool = False,
    environment_yml_generated: bool = False,
    lock_files_generated: bool = False,
    conflicts: list[dict[str, Any]] | None = None,
    verification_results: dict[str, Any] | None = None,
) -> JSONReporter:
    """
    Create a JSON reporter from analysis results.

    Args:
        scan_directory: Directory that was scanned
        file_infos: List of FileInfo objects from scanner
        imports: List of imported package names
        requirements: List of PackageRequirement objects
        mapped_packages: List of mapped package dictionaries
        unmapped_imports: List of unmapped import dictionaries
        warnings: List of warning messages
        dockerfile_generated: Whether Dockerfile was generated
        environment_yml_generated: Whether environment.yml was generated
        lock_files_generated: Whether lock files were generated
        conflicts: Optional list of conflict dictionaries from ConflictDetector
        verification_results: Optional verification results from Verifier

    Returns:
        JSONReporter instance with all data set
    """
    reporter = JSONReporter(scan_directory)

    # Set scan metrics
    python_files = len(file_infos) if file_infos else 0
    total_files = python_files  # For now, we only track Python files
    reporter.set_scan_metrics(total_files, python_files)

    # Set other data
    reporter.set_detected_imports(imports)
    reporter.set_requirements(requirements)
    reporter.set_mapped_packages(mapped_packages)
    reporter.set_unmapped_imports(unmapped_imports)

    for warning in warnings:
        reporter.add_warning(warning)

    # Set conflicts if provided
    if conflicts is not None:
        reporter.set_conflicts(conflicts)

    # Set verification results if provided
    if verification_results is not None:
        reporter.set_verification_results(verification_results)

    reporter.set_generated_files(
        dockerfile_generated,
        environment_yml_generated,
        lock_files_generated
    )

    return reporter


if __name__ == "__main__":
    """Test the JSON reporter module."""
    import tempfile
    from pathlib import Path

    # Create test data
    test_dir = Path("/tmp/test_project")

    # Mock file infos
    class MockFileInfo:
        """Mock FileInfo class for testing."""

        def __init__(self, path: Path) -> None:
            """Initialize mock file info with path.

            Args:
                path: Path to mock file.
            """
            self.path = path

    file_infos = [
        MockFileInfo(test_dir / "script1.py"),
        MockFileInfo(test_dir / "script2.py"),
        MockFileInfo(test_dir / "utils.py"),
    ]

    # Mock imports
    imports = ["numpy", "pandas", "matplotlib", "local_utils"]

    # Mock requirements
    requirements = [
        PackageRequirement(
            name="numpy",
            version_constraint="==1.24.0",
            line_number=1,
            raw_line="numpy==1.24.0",
            source="requirements.txt",
        ),
        PackageRequirement(
            name="pandas",
            version_constraint=">=2.0.0",
            line_number=2,
            raw_line="pandas>=2.0.0",
            source="requirements.txt",
        ),
    ]

    # Mock mapped packages
    mapped_packages = [
        {
            "name": "numpy",
            "version": "==1.24.0",
            "source": "requirements.txt",
            "mapped": True,
        },
        {
            "name": "pandas",
            "version": ">=2.0.0",
            "source": "requirements.txt",
            "mapped": True,
        },
        {
            "name": "matplotlib",
            "version": "latest",
            "source": "fallback",
            "mapped": True,
        },
    ]

    # Mock unmapped imports
    unmapped_imports = [{"name": "local_utils", "file": "src/utils.py", "line": 5}]

    # Mock warnings
    warnings = ["Package 'matplotlib' version not specified, using latest"]

    # Create reporter
    reporter = create_report_from_analysis(
        scan_directory=test_dir,
        file_infos=file_infos,
        imports=imports,
        requirements=requirements,
        mapped_packages=mapped_packages,
        unmapped_imports=unmapped_imports,
        warnings=warnings,
        dockerfile_generated=True,
        environment_yml_generated=True,
    )

    # Start timing for test
    reporter.metrics.start()
    time.sleep(0.1)  # Simulate scan time
    reporter.metrics.stop()

    print("Testing JSON Reporter...")
    print("\nGenerated Report:")
    reporter.print_report()

    # Test saving to file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        test_output = Path(f.name)

    try:
        reporter.save_report(test_output)
        print(f"\nReport saved to: {test_output}")

        # Verify the file can be loaded
        with open(test_output) as report_file:
            loaded_report = json.load(report_file)

        print(f"\nReport loaded successfully with {len(loaded_report)} top-level keys")
        print(f"Scan summary: {loaded_report['scan_summary']}")
        print(f"Mapped packages: {len(loaded_report['mapped_packages'])}")
        print(f"Warnings: {len(loaded_report['warnings'])}")

        print("\n✓ All tests passed!")

    finally:
        # Cleanup
        if test_output.exists():
            test_output.unlink()
