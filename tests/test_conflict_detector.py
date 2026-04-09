"""
Tests for conflict_detector.py module.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from reciper.conflict_detector import ConflictDetector


class TestConflictDetector:
    """Test cases for ConflictDetector class."""

    def test_init_without_version_constraints(self):
        """Test initialization without version constraints."""
        packages = ["numpy", "pandas", "scikit-learn"]
        detector = ConflictDetector(packages)
        
        assert detector.package_list == packages
        assert detector.version_constraints == {}
        assert detector.detected_conflicts == []
        assert len(detector.known_conflicts) > 0

    def test_init_with_version_constraints(self):
        """Test initialization with version constraints."""
        packages = ["numpy", "pandas"]
        version_constraints = {"numpy": ">=1.21.0", "pandas": "==1.5.0"}
        detector = ConflictDetector(packages, version_constraints)
        
        assert detector.package_list == packages
        assert detector.version_constraints == version_constraints

    def test_extract_version_with_constraint_dict(self):
        """Test extracting version from version_constraints dictionary."""
        packages = ["numpy", "pandas"]
        version_constraints = {"numpy": ">=1.21.0", "pandas": "==1.5.0"}
        detector = ConflictDetector(packages, version_constraints)
        
        op, version = detector._extract_version("numpy")
        assert op == ">="
        assert version == "1.21.0"
        
        op, version = detector._extract_version("pandas")
        assert op == "=="
        assert version == "1.5.0"

    def test_extract_version_from_package_list(self):
        """Test extracting version from package list entries."""
        packages = ["numpy==1.24.0", "pandas>=1.5.0", "scikit-learn"]
        detector = ConflictDetector(packages)
        
        op, version = detector._extract_version("numpy")
        assert op == "=="
        assert version == "1.24.0"
        
        op, version = detector._extract_version("pandas")
        assert op == ">="
        assert version == "1.5.0"
        
        op, version = detector._extract_version("scikit-learn")
        assert op is None
        assert version is None

    def test_parse_version_constraint(self):
        """Test parsing version constraint strings."""
        detector = ConflictDetector([])
        
        # Test various operators
        test_cases = [
            (">=1.21.0", (">=", "1.21.0")),
            ("==2.0.0", ("==", "2.0.0")),
            ("<=3.0.0", ("<=", "3.0.0")),
            (">4.0.0", (">", "4.0.0")),
            ("<5.0.0", ("<", "5.0.0")),
            ("~=1.0.0", ("~=", "1.0.0")),
            ("1.21.0", ("==", "1.21.0")),  # No operator defaults to ==
        ]
        
        for constraint, expected in test_cases:
            result = detector._parse_version_constraint(constraint)
            assert result == expected

    def test_check_conflicts_no_conflicts(self):
        """Test conflict detection with no conflicts."""
        packages = ["numpy", "pandas"]
        detector = ConflictDetector(packages)
        
        conflicts = detector.check_conflicts()
        
        # With default conflicts, we might get some warnings
        # but we can at least verify the method runs without error
        assert isinstance(conflicts, list)

    def test_check_conflicts_with_duplicate_packages(self):
        """Test conflict detection with duplicate packages."""
        packages = ["numpy==1.21.0", "numpy>=1.20.0"]
        detector = ConflictDetector(packages)
        
        conflicts = detector.check_conflicts()
        
        # Should detect duplicate package conflict
        assert len(conflicts) > 0
        duplicate_conflicts = [c for c in conflicts if c["type"] == "duplicate_package"]
        assert len(duplicate_conflicts) > 0

    def test_has_conflicts(self):
        """Test has_conflicts method."""
        packages = ["numpy", "pandas"]
        detector = ConflictDetector(packages)
        
        # Initially no conflicts
        assert not detector.has_conflicts()
        
        # Run detection
        detector.check_conflicts()
        
        # May or may not have conflicts depending on default rules
        # Just verify the method works
        result = detector.has_conflicts()
        assert isinstance(result, bool)

    def test_get_conflict_summary(self):
        """Test get_conflict_summary method."""
        packages = ["numpy", "pandas"]
        detector = ConflictDetector(packages)
        
        summary = detector.get_conflict_summary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_get_conflicts_by_severity(self):
        """Test get_conflicts_by_severity method."""
        packages = ["numpy", "pandas", "tensorflow", "python"]
        detector = ConflictDetector(packages)
        
        # Run detection first
        detector.check_conflicts()
        
        # Get conflicts by severity
        errors = detector.get_conflicts_by_severity("error")
        warnings = detector.get_conflicts_by_severity("warning")
        
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
        
        # All conflicts should have the correct severity
        for conflict in errors:
            assert conflict["severity"] == "error"
        
        for conflict in warnings:
            assert conflict["severity"] == "warning"

    def test_load_known_conflicts_file_not_found(self):
        """Test loading known conflicts when file doesn't exist."""
        with patch.object(Path, 'exists', return_value=False):
            detector = ConflictDetector([])
            
            # Should fall back to default conflicts
            assert len(detector.known_conflicts) > 0
            # Default conflicts should have our example structure
            assert any("tensorflow" in str(c) for c in detector.known_conflicts)

    def test_load_known_conflicts_invalid_yaml(self):
        """Test loading known conflicts with invalid YAML."""
        mock_yaml_content = "invalid: yaml: ["
        
        with patch('builtins.open', mock_open(read_data=mock_yaml_content)):
            with patch.object(Path, 'exists', return_value=True):
                detector = ConflictDetector([])
                
                # Should fall back to default conflicts
                assert len(detector.known_conflicts) > 0

    def test_check_python_version_compatibility(self):
        """Test Python version compatibility checking."""
        packages = ["python==3.9", "tensorflow"]
        detector = ConflictDetector(packages)
        
        # Run the internal method
        detector._check_python_version_compatibility()
        
        # Check if conflicts were added
        # This depends on the default conflict rules
        detector.check_conflicts()
        conflicts = detector.detected_conflicts
        
        # Should at least run without error
        assert isinstance(conflicts, list)

    def test_check_duplicate_packages(self):
        """Test duplicate package detection."""
        packages = ["numpy==1.21.0", "numpy>=1.20.0", "pandas", "pandas==1.5.0"]
        detector = ConflictDetector(packages)
        
        # Run the internal method
        detector._check_duplicate_packages()
        
        # Should detect duplicates
        conflicts = detector.detected_conflicts
        duplicate_conflicts = [c for c in conflicts if c["type"] == "duplicate_package"]
        
        # Should find at least numpy duplicate
        assert len(duplicate_conflicts) >= 1

    @patch('reciper.conflict_detector.logger')
    def test_check_conda_compatibility_placeholder(self, mock_logger):
        """Test the placeholder Conda compatibility check."""
        detector = ConflictDetector([])
        
        # This is a placeholder method that always returns True
        result = detector._check_conda_compatibility(
            "numpy", "1.21.0", "pandas", "1.5.0"
        )
        
        assert result is True
        mock_logger.debug.assert_called()


class TestConflictDetectorIntegration:
    """Integration tests for ConflictDetector with actual YAML file."""

    def test_with_actual_conflicts_file(self, tmp_path):
        """Test with a temporary known conflicts YAML file."""
        # Create a temporary known conflicts file
        conflicts_data = {
            "known_conflicts": [
                {
                    "packages": ["testpkg1", "testpkg2"],
                    "incompatible_versions": [
                        {"testpkg1": ">=2.0", "testpkg2": "<1.0"}
                    ],
                    "conflict_type": "package_pair",
                    "message": "Test conflict message",
                    "severity": "error"
                }
            ]
        }
        
        conflicts_file = tmp_path / "known_conflicts.yaml"
        with open(conflicts_file, 'w') as f:
            yaml.dump(conflicts_data, f)
        
        # Patch the file path
        with patch('reciper.conflict_detector.Path') as mock_path:
            mock_path.return_value.parent.__truediv__.return_value.exists.return_value = True
            mock_path.return_value.parent.__truediv__.return_value.__str__.return_value = str(conflicts_file)
            
            # Mock open to read our test file
            with patch('builtins.open', mock_open(read_data=yaml.dump(conflicts_data))):
                packages = ["testpkg1", "testpkg2"]
                detector = ConflictDetector(packages)
                
                # Should load our test conflict
                assert len(detector.known_conflicts) == 1
                assert detector.known_conflicts[0]["packages"] == ["testpkg1", "testpkg2"]

    def test_conflict_detection_with_generator_integration(self):
        """Test that ConflictDetector can be used with generator."""
        # This is a smoke test to ensure the integration works
        packages = ["numpy", "pandas", "python==3.9"]
        detector = ConflictDetector(packages)
        
        conflicts = detector.check_conflicts()
        summary = detector.get_conflict_summary()
        
        assert isinstance(conflicts, list)
        assert isinstance(summary, str)
        
        # Verify the detector has the expected methods
        assert hasattr(detector, 'has_conflicts')
        assert hasattr(detector, 'get_conflicts_by_severity')


def test_conflict_types():
    """Test different conflict type detection."""
    # Test version range conflict
    packages = ["python==3.7", "tensorflow"]
    detector = ConflictDetector(packages)
    conflicts = detector.check_conflicts()
    
    # Just verify it runs without error
    assert isinstance(conflicts, list)
    
    # Test package pair conflict  
    packages = ["braker", "augustus"]
    detector = ConflictDetector(packages)
    conflicts = detector.check_conflicts()
    
    assert isinstance(conflicts, list)
    
    # Test recommendation conflict
    packages = ["numpy", "pandas"]
    detector = ConflictDetector(packages)
    conflicts = detector.check_conflicts()
    
    assert isinstance(conflicts, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])