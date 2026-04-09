"""
Constants for Reciper.

This module defines constants for file names, source types, and other magic strings
used throughout the codebase.
"""

# File names for dependency files
REQUIREMENTS_TXT = "requirements.txt"
PYPROJECT_TOML = "pyproject.toml"
SETUP_PY = "setup.py"

# Source types for package requirements
SOURCE_REQUIREMENTS_TXT = "requirements.txt"
SOURCE_PYPROJECT_TOML = "pyproject.toml"
SOURCE_SETUP_PY = "setup.py"
SOURCE_MAPPING = "mapping"
SOURCE_STANDARD_LIBRARY = "standard_library"
SOURCE_UNMAPPED = "unmapped"
SOURCE_FALLBACK = "fallback"

# Common package names (for reference, not used as mappings)
PACKAGE_NUMPY = "numpy"
PACKAGE_PANDAS = "pandas"
PACKAGE_SCIKIT_LEARN = "scikit-learn"
PACKAGE_MATPLOTLIB = "matplotlib"
PACKAGE_SCIPY = "scipy"

# File extensions
EXT_PY = ".py"
EXT_YAML = ".yaml"
EXT_YML = ".yml"
EXT_JSON = ".json"

# Default values
DEFAULT_ENCODING = "utf-8"
DEFAULT_LINE_LENGTH = 88

# CLI constants
CLI_PROGRESS_UPDATE_INTERVAL = 20  # Update progress every N directories

# CLI option defaults
DEFAULT_OUTPUT_DIR = "."
DEFAULT_CONFLICT_CHECK = True
DEFAULT_NO_LOCK = False
DEFAULT_NO_VERIFY = False
DEFAULT_VERBOSE = False

# Verification constants
VERIFICATION_TIMEOUT_SECONDS = 30
DOCKER_BUILD_TIMEOUT = 300  # 5 minutes
CONDA_DRY_RUN_TIMEOUT = 120  # 2 minutes

# File generation defaults
GENERATE_LOCK_FILES = True
GENERATE_DOCKERFILE = True
GENERATE_ENVIRONMENT_YML = True

# Cache settings
CACHE_MAXSIZE_PARSER = 256
CACHE_MAXSIZE_DEFAULT = 128

# Error messages (partial - more can be added as needed)
ERROR_FILE_NOT_FOUND = "File not found: {}"
ERROR_PERMISSION_DENIED = "Permission denied: {}"
ERROR_SYNTAX_ERROR = "Syntax error in {}: {}"
ERROR_DOCKER_NOT_AVAILABLE = "Docker not available for verification"
ERROR_CONDA_NOT_AVAILABLE = "Conda not available for dry-run verification"
WARNING_LOCK_GENERATION_FAILED = "Lock file generation failed: {}"
INFO_VERIFICATION_DISABLED = "Verification disabled via --no-verify flag"
INFO_CONFLICT_CHECK_DISABLED = "Conflict detection disabled via --no-conflict-check flag"
INFO_LOCK_GENERATION_DISABLED = "Lock file generation disabled via --no-lock flag"

# Regular expression patterns (as raw strings)
RE_VERSION_CONSTRAINT = r'[=<>!~]+.*'
RE_PACKAGE_NAME = r'[a-zA-Z0-9][a-zA-Z0-9._-]*'
RE_EDITABLE_INSTALL = r'^-e\s+'
RE_RECURSIVE_REQUIREMENT = r'^-r\s+'