"""Programmatic API for Reciper - Static analyzer for Python pipelines."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from reciper.generator import generate_files
from reciper.import_aggregator import (
    AggregatedImport,
    ImportAggregator,
    aggregate_imports_from_files,
)
from reciper.mapper import map_to_conda, map_to_conda_with_details
from reciper.parser import parse_imports
from reciper.reporter import create_report_from_analysis
from reciper.requirements_parser import (
    PackageRequirement,
    parse_dependency_file,
    requirements_to_dict,
)
from reciper.scanner import find_requirements_file, scan_directory
from reciper.verifier import Verifier
from reciper.command_detector import (
    CommandDetector,
    detect_commands_in_file,
    map_commands_to_apt_packages,
    generate_apt_install_commands,
)
from reciper.conflict_detector import ConflictDetector


@dataclass
class AnalysisConfig:
    """Configuration for analysis operations."""
    
    # Output settings
    output_dir: str = "."
    generate_lockfile: bool = True
    generate_dockerfile: bool = True
    generate_environment_yml: bool = True
    
    # Analysis settings
    enable_conflict_check: bool = True
    enable_verification: bool = True
    enable_command_detection: bool = True
    
    # Performance settings
    parallel_processing: bool = True
    max_workers: Optional[int] = None
    use_cache: bool = True
    
    # Output format
    json_output: bool = False
    verbose: bool = False


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    
    # Core data
    imports: List[AggregatedImport] = field(default_factory=list)
    conda_packages: Dict[str, str] = field(default_factory=dict)
    apt_packages: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    scanned_files: int = 0
    scanned_directories: int = 0
    python_files_found: int = 0
    requirements_file_found: bool = False
    
    # Generated files
    generated_files: List[str] = field(default_factory=list)
    output_dir: str = "."
    
    # Verification results
    verification_passed: bool = False
    verification_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "imports": [
                {
                    "module": imp.module,
                    "imports": imp.imports,
                    "files": [str(f) for f in imp.files],
                    "line_numbers": imp.line_numbers,
                }
                for imp in self.imports
            ],
            "conda_packages": self.conda_packages,
            "apt_packages": self.apt_packages,
            "conflicts": self.conflicts,
            "scanned_files": self.scanned_files,
            "scanned_directories": self.scanned_directories,
            "python_files_found": self.python_files_found,
            "requirements_file_found": self.requirements_file_found,
            "generated_files": self.generated_files,
            "output_dir": self.output_dir,
            "verification_passed": self.verification_passed,
            "verification_errors": self.verification_errors,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class Analyzer:
    """Main analyzer class for programmatic use."""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize analyzer with optional configuration."""
        self.config = config or AnalysisConfig()
        self._import_aggregator = ImportAggregator()
        self._command_detector = CommandDetector()
        self._conflict_detector = ConflictDetector()
        self._verifier = Verifier()
    
    def analyze(self, path: Union[str, Path]) -> AnalysisResult:
        """
        Analyze a directory or file and generate reproducible environment files.
        
        Args:
            path: Path to directory or file to analyze
            
        Returns:
            AnalysisResult object with analysis results
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        # Initialize result
        result = AnalysisResult()
        result.output_dir = self.config.output_dir
        
        # Scan directory or file
        if path.is_dir():
            scan_result = scan_directory(
                path,
                progress_callback=None,  # No progress callback for API
                parallel=self.config.parallel_processing,
                max_workers=self.config.max_workers,
                use_cache=self.config.use_cache,
            )
            python_files = scan_result.python_files
            result.scanned_files = scan_result.scanned_files
            result.scanned_directories = scan_result.scanned_directories
            result.python_files_found = len(python_files)
        else:
            # Single file analysis
            python_files = [path]
            result.scanned_files = 1
            result.scanned_directories = 0
            result.python_files_found = 1
        
        # Aggregate imports
        imports = aggregate_imports_from_files(
            python_files,
            parallel=self.config.parallel_processing,
            max_workers=self.config.max_workers,
            use_cache=self.config.use_cache,
        )
        result.imports = imports
        
        # Map to conda packages
        conda_packages = {}
        for imp in imports:
            for module in imp.imports:
                conda_name = map_to_conda(module)
                if conda_name:
                    conda_packages[conda_name] = ""  # No version specified
        
        result.conda_packages = conda_packages
        
        # Detect commands and map to apt packages
        if self.config.enable_command_detection:
            apt_packages = []
            for file_path in python_files:
                commands = detect_commands_in_file(file_path)
                mapped = map_commands_to_apt_packages(commands)
                apt_packages.extend(mapped)
            result.apt_packages = list(set(apt_packages))  # Deduplicate
        
        # Check for conflicts
        if self.config.enable_conflict_check:
            conflicts = self._conflict_detector.check_conflicts(
                list(conda_packages.keys())
            )
            result.conflicts = conflicts
        
        # Find requirements file
        req_file = find_requirements_file(path if path.is_dir() else path.parent)
        if req_file:
            result.requirements_file_found = True
            # Parse requirements for comparison (optional)
            # This could be added to the result
        
        # Generate files
        if self.config.generate_dockerfile or self.config.generate_environment_yml:
            generated = generate_files(
                path,
                output_dir=self.config.output_dir,
                generate_dockerfile=self.config.generate_dockerfile,
                generate_environment_yml=self.config.generate_environment_yml,
                generate_lockfile=self.config.generate_lockfile,
                apt_packages=result.apt_packages,
                conda_packages=result.conda_packages,
            )
            result.generated_files = generated
        
        # Run verification
        if self.config.enable_verification:
            verification_result = self._verifier.verify(
                path,
                conda_packages=list(result.conda_packages.keys()),
                apt_packages=result.apt_packages,
            )
            result.verification_passed = verification_result.passed
            result.verification_errors = verification_result.errors
        
        return result
    
    def analyze_to_json(self, path: Union[str, Path], indent: int = 2) -> str:
        """
        Analyze and return JSON string directly.
        
        Args:
            path: Path to directory or file to analyze
            indent: JSON indentation level
            
        Returns:
            JSON string with analysis results
        """
        result = self.analyze(path)
        return result.to_json(indent=indent)


# Convenience function for simple analysis
def analyze(
    path: Union[str, Path],
    output_dir: str = ".",
    json_output: bool = False,
    enable_conflict_check: bool = True,
    enable_verification: bool = True,
) -> Union[AnalysisResult, str]:
    """
    Convenience function for simple analysis.
    
    Args:
        path: Path to directory or file to analyze
        output_dir: Directory where generated files should be placed
        json_output: If True, returns JSON string instead of AnalysisResult
        enable_conflict_check: Enable/disable conflict detection
        enable_verification: Enable/disable verification
        
    Returns:
        AnalysisResult object or JSON string if json_output=True
    """
    config = AnalysisConfig(
        output_dir=output_dir,
        enable_conflict_check=enable_conflict_check,
        enable_verification=enable_verification,
    )
    
    analyzer = Analyzer(config)
    
    if json_output:
        return analyzer.analyze_to_json(path)
    else:
        return analyzer.analyze(path)


def analyze_single_file(
    file_path: Union[str, Path],
    output_dir: str = ".",
) -> AnalysisResult:
    """
    Analyze a single Python file.
    
    Args:
        file_path: Path to Python file
        output_dir: Directory where generated files should be placed
        
    Returns:
        AnalysisResult object
    """
    config = AnalysisConfig(
        output_dir=output_dir,
        generate_dockerfile=False,
        generate_environment_yml=False,
        generate_lockfile=False,
    )
    
    analyzer = Analyzer(config)
    return analyzer.analyze(file_path)


def analyze_with_custom_config(
    path: Union[str, Path],
    config: AnalysisConfig,
) -> AnalysisResult:
    """
    Analyze with custom configuration.
    
    Args:
        path: Path to directory or file to analyze
        config: Custom AnalysisConfig object
        
    Returns:
        AnalysisResult object
    """
    analyzer = Analyzer(config)
    return analyzer.analyze(path)