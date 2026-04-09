"""Tests for the Reciper programmatic API."""

import json
import tempfile
from pathlib import Path

import pytest

from reciper import (
    AnalysisConfig,
    AnalysisResult,
    Analyzer,
    analyze,
    analyze_single_file,
    analyze_with_custom_config,
)


class TestAnalysisConfig:
    """Tests for AnalysisConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AnalysisConfig()
        
        assert config.output_dir == "."
        assert config.generate_lockfile is True
        assert config.generate_dockerfile is True
        assert config.generate_environment_yml is True
        assert config.enable_conflict_check is True
        assert config.enable_verification is True
        assert config.enable_command_detection is True
        assert config.parallel_processing is True
        assert config.max_workers is None
        assert config.use_cache is True
        assert config.json_output is False
        assert config.verbose is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AnalysisConfig(
            output_dir="./output",
            generate_lockfile=False,
            generate_dockerfile=False,
            generate_environment_yml=False,
            enable_conflict_check=False,
            enable_verification=False,
            enable_command_detection=False,
            parallel_processing=False,
            max_workers=4,
            use_cache=False,
            json_output=True,
            verbose=True,
        )
        
        assert config.output_dir == "./output"
        assert config.generate_lockfile is False
        assert config.generate_dockerfile is False
        assert config.generate_environment_yml is False
        assert config.enable_conflict_check is False
        assert config.enable_verification is False
        assert config.enable_command_detection is False
        assert config.parallel_processing is False
        assert config.max_workers == 4
        assert config.use_cache is False
        assert config.json_output is True
        assert config.verbose is True


class TestAnalysisResult:
    """Tests for AnalysisResult class."""
    
    def test_empty_result(self):
        """Test empty analysis result."""
        result = AnalysisResult()
        
        assert result.imports == []
        assert result.conda_packages == {}
        assert result.apt_packages == []
        assert result.conflicts == []
        assert result.scanned_files == 0
        assert result.scanned_directories == 0
        assert result.python_files_found == 0
        assert result.requirements_file_found is False
        assert result.generated_files == []
        assert result.output_dir == "."
        assert result.verification_passed is False
        assert result.verification_errors == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = AnalysisResult(
            scanned_files=10,
            scanned_directories=2,
            python_files_found=5,
            requirements_file_found=True,
            output_dir="./output",
            verification_passed=True,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["scanned_files"] == 10
        assert result_dict["scanned_directories"] == 2
        assert result_dict["python_files_found"] == 5
        assert result_dict["requirements_file_found"] is True
        assert result_dict["output_dir"] == "./output"
        assert result_dict["verification_passed"] is True
        assert "imports" in result_dict
        assert "conda_packages" in result_dict
        assert "apt_packages" in result_dict
        assert "conflicts" in result_dict
        assert "generated_files" in result_dict
        assert "verification_errors" in result_dict
    
    def test_to_json(self):
        """Test conversion to JSON."""
        result = AnalysisResult(
            scanned_files=5,
            python_files_found=3,
        )
        
        json_str = result.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["scanned_files"] == 5
        assert parsed["python_files_found"] == 3
        assert isinstance(json_str, str)


class TestAnalyzer:
    """Tests for Analyzer class."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            
            # Create a simple Python file
            python_file = project_dir / "analysis.py"
            python_file.write_text("""
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

def analyze_data():
    data = np.random.randn(100, 10)
    df = pd.DataFrame(data)
    plt.plot(df.mean())
    return df
""")
            
            # Create a requirements file
            requirements_file = project_dir / "requirements.txt"
            requirements_file.write_text("""
numpy>=1.21.0
pandas>=1.3.0
""")
            
            yield project_dir
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization with default config."""
        analyzer = Analyzer()
        assert isinstance(analyzer.config, AnalysisConfig)
        
        # Test with custom config
        config = AnalysisConfig(output_dir="./custom")
        analyzer = Analyzer(config)
        assert analyzer.config.output_dir == "./custom"
    
    def test_analyze_directory(self, temp_project_dir):
        """Test analyzing a directory."""
        analyzer = Analyzer()
        result = analyzer.analyze(temp_project_dir)
        
        assert isinstance(result, AnalysisResult)
        assert result.scanned_files > 0
        assert result.python_files_found > 0
        assert result.requirements_file_found is True
        
        # Should find some imports
        assert len(result.imports) > 0
        
        # Should map to conda packages
        assert len(result.conda_packages) > 0
        
        # Check specific packages
        conda_packages = list(result.conda_packages.keys())
        assert any("numpy" in pkg.lower() for pkg in conda_packages)
        assert any("pandas" in pkg.lower() for pkg in conda_packages)
    
    def test_analyze_with_custom_config(self, temp_project_dir):
        """Test analyzing with custom configuration."""
        config = AnalysisConfig(
            output_dir=str(temp_project_dir / "output"),
            generate_dockerfile=False,
            generate_environment_yml=False,
            enable_conflict_check=False,
        )
        
        analyzer = Analyzer(config)
        result = analyzer.analyze(temp_project_dir)
        
        assert result.output_dir == str(temp_project_dir / "output")
        # No conflicts since conflict check disabled
        assert result.conflicts == []
    
    def test_analyze_to_json(self, temp_project_dir):
        """Test analyzing and getting JSON output."""
        analyzer = Analyzer()
        json_result = analyzer.analyze_to_json(temp_project_dir)
        
        # Should be valid JSON
        parsed = json.loads(json_result)
        assert isinstance(parsed, dict)
        assert "imports" in parsed
        assert "conda_packages" in parsed
    
    def test_analyze_nonexistent_path(self):
        """Test analyzing a non-existent path raises error."""
        analyzer = Analyzer()
        
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/path/12345")


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.fixture
    def temp_python_file(self):
        """Create a temporary Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            python_file = Path(tmpdir) / "test_script.py"
            python_file.write_text("""
import os
import sys
import json

def process_data():
    return {"result": "success"}
""")
            yield python_file
    
    def test_analyze_function(self, temp_project_dir):
        """Test the convenience analyze function."""
        # Test with AnalysisResult return
        result = analyze(temp_project_dir)
        assert isinstance(result, AnalysisResult)
        
        # Test with JSON return
        json_result = analyze(temp_project_dir, json_output=True)
        assert isinstance(json_result, str)
        parsed = json.loads(json_result)
        assert isinstance(parsed, dict)
    
    def test_analyze_single_file(self, temp_python_file):
        """Test analyzing a single file."""
        result = analyze_single_file(temp_python_file)
        
        assert isinstance(result, AnalysisResult)
        assert result.scanned_files == 1
        assert result.python_files_found == 1
        assert result.scanned_directories == 0
        
        # Should find standard library imports
        assert len(result.imports) > 0
        import_modules = [imp.module for imp in result.imports]
        assert "os" in import_modules or "sys" in import_modules or "json" in import_modules
    
    def test_analyze_with_custom_config_function(self, temp_project_dir):
        """Test analyze_with_custom_config function."""
        config = AnalysisConfig(
            output_dir="./custom_output",
            enable_conflict_check=False,
        )
        
        result = analyze_with_custom_config(temp_project_dir, config)
        
        assert isinstance(result, AnalysisResult)
        assert result.output_dir == "./custom_output"
        assert result.conflicts == []  # No conflict check


class TestIntegration:
    """Integration tests for the API."""
    
    def test_api_imports(self):
        """Test that all API components are importable."""
        from reciper.api import (
            AnalysisConfig,
            AnalysisResult,
            Analyzer,
            analyze,
            analyze_single_file,
            analyze_with_custom_config,
        )
        
        # Just verify imports work
        assert True
    
    def test_full_analysis_workflow(self, temp_project_dir):
        """Test complete analysis workflow."""
        # Create analyzer
        analyzer = Analyzer()
        
        # Analyze project
        result = analyzer.analyze(temp_project_dir)
        
        # Verify result structure
        assert hasattr(result, 'imports')
        assert hasattr(result, 'conda_packages')
        assert hasattr(result, 'apt_packages')
        assert hasattr(result, 'conflicts')
        assert hasattr(result, 'scanned_files')
        assert hasattr(result, 'python_files_found')
        assert hasattr(result, 'generated_files')
        
        # Convert to dict and JSON
        result_dict = result.to_dict()
        result_json = result.to_json()
        
        assert isinstance(result_dict, dict)
        assert isinstance(result_json, str)
        
        # Verify JSON can be parsed
        parsed = json.loads(result_json)
        assert parsed["scanned_files"] == result.scanned_files