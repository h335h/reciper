"""
Conflict Detector for Reciper static analyzer.

This module provides functionality to detect package version conflicts
in Python environments before generating environment.yml files.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detects package version conflicts in Python environments."""

    def __init__(self, package_list: List[str], version_constraints: Optional[Dict[str, str]] = None):
        """
        Initialize the conflict detector.

        Args:
            package_list: List of package names (e.g., ["numpy", "pandas"])
            version_constraints: Optional dictionary mapping package names to version constraints
                                 (e.g., {"numpy": ">=1.21.0", "pandas": "==1.5.0"})
        """
        self.package_list = package_list
        self.version_constraints = version_constraints or {}
        self.known_conflicts = self._load_known_conflicts()
        self.detected_conflicts = []

    def _load_known_conflicts(self) -> List[Dict[str, Any]]:
        """
        Load known conflicts from YAML configuration file.

        Returns:
            List of conflict dictionaries
        """
        # Try to load from the data directory
        data_dir = Path(__file__).parent / "data"
        conflicts_file = data_dir / "known_conflicts.yaml"

        if not conflicts_file.exists():
            logger.warning(f"Known conflicts file not found at {conflicts_file}")
            # Return some default conflicts
            return self._get_default_conflicts()

        try:
            with open(conflicts_file, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('known_conflicts', [])
        except (yaml.YAMLError, IOError) as e:
            logger.error(f"Failed to load known conflicts: {e}")
            return self._get_default_conflicts()

    def _get_default_conflicts(self) -> List[Dict[str, Any]]:
        """Return a list of default known conflicts."""
        return [
            {
                "packages": ["python", "tensorflow"],
                "min_python": "3.8",
                "max_python": "3.10",
                "conflict_type": "version_range",
                "message": "TensorFlow 2.x requires Python 3.8-3.10"
            },
            {
                "packages": ["braker", "augustus"],
                "incompatible_versions": [
                    {"braker": ">=3.0", "augustus": "<3.4"}
                ],
                "conflict_type": "package_pair",
                "message": "BRAKER 3.0+ requires Augustus 3.4+"
            },
            {
                "packages": ["numpy", "pandas"],
                "recommended_pair": {
                    "numpy": ">=1.21.0",
                    "pandas": ">=1.3.0"
                },
                "conflict_type": "recommendation",
                "message": "For optimal performance, use numpy>=1.21.0 with pandas>=1.3.0"
            }
        ]

    def _extract_version(self, package_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract version constraint from package name or version_constraints dict.

        Args:
            package_name: Name of the package

        Returns:
            Tuple of (operator, version) or (None, None) if no version specified
        """
        # Check if version is in version_constraints
        if package_name in self.version_constraints:
            constraint = self.version_constraints[package_name]
            return self._parse_version_constraint(constraint)

        # Check if version is embedded in package_list entry (e.g., "numpy==1.21.0")
        for pkg in self.package_list:
            if pkg.startswith(package_name):
                # Check for version operators
                for op in ["==", ">=", "<=", ">", "<", "~="]:
                    if op in pkg:
                        version_part = pkg.split(op, 1)[1].strip()
                        return op, version_part

        return None, None

    def _parse_version_constraint(self, constraint: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse version constraint string into operator and version.

        Args:
            constraint: Version constraint string (e.g., ">=1.21.0", "==2.0.0")

        Returns:
            Tuple of (operator, version)
        """
        operators = ["==", ">=", "<=", ">", "<", "~="]
        for op in operators:
            if constraint.startswith(op):
                return op, constraint[len(op):].strip()
        # If no operator, assume exact version
        return "==", constraint

    def _check_version_range_conflict(self, conflict: Dict[str, Any]) -> Optional[str]:
        """
        Check for version range conflicts (e.g., Python version compatibility).

        Args:
            conflict: Conflict dictionary with 'min_python' and/or 'max_python'

        Returns:
            Conflict message if detected, None otherwise
        """
        if "python" not in self.package_list:
            return None

        python_version_op, python_version = self._extract_version("python")
        if not python_version:
            return None

        min_version = conflict.get("min_python")
        max_version = conflict.get("max_python")

        # For simplicity, we'll just check if python is in the list and warn
        # A more sophisticated version would parse and compare versions
        if min_version or max_version:
            packages = ", ".join(conflict["packages"])
            return conflict["message"]

        return None

    def _check_package_pair_conflict(self, conflict: Dict[str, Any]) -> Optional[str]:
        """
        Check for incompatible version pairs between packages.

        Args:
            conflict: Conflict dictionary with 'incompatible_versions'

        Returns:
            Conflict message if detected, None otherwise
        """
        packages = conflict["packages"]
        incompatible_versions = conflict.get("incompatible_versions", [])

        # Check if all packages in the conflict are in our package list
        if not all(pkg in self.package_list for pkg in packages):
            return None

        # For each incompatible version pair, check if we have those versions
        for pair in incompatible_versions:
            for pkg, version_constraint in pair.items():
                if pkg in self.package_list:
                    # Check if the version constraint matches what we have
                    # For simplicity, we'll just warn if the package is present
                    # A more sophisticated implementation would parse and compare versions
                    return conflict["message"]

        return None

    def _check_recommendation_conflict(self, conflict: Dict[str, Any]) -> Optional[str]:
        """
        Check for recommended version pairs.

        Args:
            conflict: Conflict dictionary with 'recommended_pair'

        Returns:
            Recommendation message if packages are present, None otherwise
        """
        packages = conflict["packages"]
        recommended_pair = conflict.get("recommended_pair", {})

        # Check if all packages in the conflict are in our package list
        if not all(pkg in self.package_list for pkg in packages):
            return None

        # If we have the packages, return the recommendation
        return conflict["message"]

    def _check_conda_compatibility(self, package1: str, version1: str, 
                                   package2: str, version2: str) -> bool:
        """
        Check compatibility between two package versions using Conda API (optional).

        Note: This is a placeholder for future Conda API integration.
        Currently returns True (assumes compatible) as we don't have actual API access.

        Args:
            package1: First package name
            version1: First package version
            package2: Second package name
            version2: Second package version

        Returns:
            True if compatible, False otherwise
        """
        # TODO: Implement actual Conda API call
        # For now, we'll assume compatibility
        logger.debug(f"Checking Conda compatibility between {package1}=={version1} and {package2}=={version2}")
        return True

    def check_conflicts(self) -> List[Dict[str, Any]]:
        """
        Main conflict detection logic.

        Returns:
            List of detected conflicts, each as a dictionary with:
            - 'type': conflict type
            - 'message': human-readable message
            - 'packages': list of packages involved
            - 'severity': 'warning' or 'error'
        """
        self.detected_conflicts = []

        # Check each known conflict
        for conflict in self.known_conflicts:
            conflict_type = conflict.get("conflict_type", "unknown")
            message = None

            if conflict_type == "version_range":
                message = self._check_version_range_conflict(conflict)
            elif conflict_type == "package_pair":
                message = self._check_package_pair_conflict(conflict)
            elif conflict_type == "recommendation":
                message = self._check_recommendation_conflict(conflict)

            if message:
                self.detected_conflicts.append({
                    "type": conflict_type,
                    "message": message,
                    "packages": conflict["packages"],
                    "severity": "warning" if conflict_type == "recommendation" else "error"
                })

        # Check for basic Python version conflicts
        self._check_python_version_compatibility()

        # Check for duplicate packages with different versions
        self._check_duplicate_packages()

        return self.detected_conflicts

    def _check_python_version_compatibility(self):
        """Check for Python version compatibility with common packages."""
        python_packages = ["tensorflow", "torch", "scikit-learn", "pandas", "numpy"]
        
        python_version_op, python_version = self._extract_version("python")
        if not python_version:
            return

        # Check if we have any packages that might have Python version requirements
        for pkg in python_packages:
            if pkg in self.package_list:
                # This is a simplified check - in reality we'd check actual version requirements
                self.detected_conflicts.append({
                    "type": "python_compatibility",
                    "message": f"{pkg} may have specific Python version requirements",
                    "packages": ["python", pkg],
                    "severity": "warning"
                })

    def _check_duplicate_packages(self):
        """Check for duplicate packages with different version specifications."""
        package_versions = {}
        
        for pkg_spec in self.package_list:
            # Parse package name and version
            for op in ["==", ">=", "<=", ">", "<", "~="]:
                if op in pkg_spec:
                    pkg_name = pkg_spec.split(op)[0].strip()
                    version = pkg_spec.split(op)[1].strip()
                    
                    if pkg_name in package_versions:
                        # Found duplicate with potentially different version
                        self.detected_conflicts.append({
                            "type": "duplicate_package",
                            "message": f"Package {pkg_name} specified multiple times with different versions",
                            "packages": [pkg_name],
                            "severity": "error"
                        })
                    else:
                        package_versions[pkg_name] = version
                    break
            else:
                # No version specified
                pkg_name = pkg_spec.strip()
                if pkg_name in package_versions:
                    self.detected_conflicts.append({
                        "type": "duplicate_package",
                        "message": f"Package {pkg_name} specified multiple times",
                        "packages": [pkg_name],
                        "severity": "warning"
                    })
                else:
                    package_versions[pkg_name] = None

    def get_conflict_summary(self) -> str:
        """
        Get a human-readable summary of detected conflicts.

        Returns:
            Summary string
        """
        if not self.detected_conflicts:
            return "No package conflicts detected."

        summary = f"Detected {len(self.detected_conflicts)} potential conflict(s):\n"
        for i, conflict in enumerate(self.detected_conflicts, 1):
            summary += f"\n{i}. [{conflict['severity'].upper()}] {conflict['message']}"
            summary += f"\n   Packages involved: {', '.join(conflict['packages'])}"
        
        return summary

    def has_conflicts(self) -> bool:
        """
        Check if any conflicts were detected.

        Returns:
            True if conflicts detected, False otherwise
        """
        return len(self.detected_conflicts) > 0

    def get_conflicts_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """
        Get conflicts filtered by severity.

        Args:
            severity: 'error' or 'warning'

        Returns:
            List of conflicts with the specified severity
        """
        return [c for c in self.detected_conflicts if c['severity'] == severity]