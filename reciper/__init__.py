"""Reciper - Static analyzer for Python pipelines to generate reproducible environments"""

__version__ = "0.1.0"
__author__ = "Reciper Developer"

# Core modules
from reciper.generator import (
    generate_files,
    generate_dockerfile_with_apt,
    generate_dockerfile_for_project,
)
from reciper.import_aggregator import (
    AggregatedImport,
    ImportAggregator,
    ImportOccurrence,
    aggregate_imports_from_files,
    print_aggregation_summary,
)
from reciper.mapper import map_to_conda
from reciper.parser import parse_imports
from reciper.requirements_parser import (
    PackageRequirement,
    compare_with_imports,
    parse_dependency_file,
    parse_requirements_file,
    requirements_to_dict,
)

# Multi-file scanning and requirements parsing
from reciper.scanner import (
    FileInfo,
    find_requirements_file,
    get_directory_summary,
    scan_directory,
    scan_single_file,
)
from reciper.verifier import Verifier

# Command detector for apt dependencies
from reciper.command_detector import (
    CommandCall,
    AptPackage,
    CommandDetector,
    detect_commands_in_file,
    load_command_mappings,
    map_commands_to_apt_packages,
    generate_apt_install_commands,
)

# Lock file generators
from reciper.lockfile_generator import (
    LockfileGenerator,
    generate_lock_files,
)

# Library API
from reciper.api import (
    AnalysisConfig,
    AnalysisResult,
    Analyzer,
    analyze,
    analyze_single_file,
    analyze_with_custom_config,
)

__all__ = [
    # Core modules
    "parse_imports",
    "map_to_conda",
    "generate_files",
    "Verifier",
    # Multi-file scanning
    "scan_directory",
    "scan_single_file",
    "find_requirements_file",
    "FileInfo",
    "get_directory_summary",
    # Requirements parsing
    "parse_requirements_file",
    "parse_dependency_file",
    "requirements_to_dict",
    "compare_with_imports",
    "PackageRequirement",
    # Import aggregation
    "ImportAggregator",
    "aggregate_imports_from_files",
    "ImportOccurrence",
    "AggregatedImport",
    "print_aggregation_summary",
    # Command detector
    "CommandCall",
    "AptPackage",
    "CommandDetector",
    "detect_commands_in_file",
    "load_command_mappings",
    "map_commands_to_apt_packages",
    "generate_apt_install_commands",
    # Enhanced generator functions
    "generate_dockerfile_with_apt",
    "generate_dockerfile_for_project",
    # Lock file generators
    "LockfileGenerator",
    "generate_lock_files",
    # Library API
    "AnalysisConfig",
    "AnalysisResult",
    "Analyzer",
    "analyze",
    "analyze_single_file",
    "analyze_with_custom_config",
]
