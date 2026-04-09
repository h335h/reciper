"""
Command detector for Reciper.

This module detects external command calls in Python code (subprocess.run, os.system, etc.)
and maps them to apt packages for inclusion in Dockerfile.

Phase 9: Added parallel processing and performance improvements.
"""

import ast
import concurrent.futures
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from reciper.cache import ASTCache, get_global_cache


@dataclass
class CommandCall:
    """Represents a detected external command call."""
    
    command: str
    file_path: Path
    line_number: int
    call_type: str  # "subprocess.run", "os.system", "os.popen", "subprocess.Popen"
    context: str | None = None  # Optional context/arguments
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "command": self.command,
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "call_type": self.call_type,
            "context": self.context,
        }


@dataclass
class AptPackage:
    """Represents an apt package derived from a command."""
    
    package_name: str
    command: str
    source_files: list[tuple[Path, int]]  # List of (file_path, line_number)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "package_name": self.package_name,
            "command": self.command,
            "source_files": [
                {"file_path": str(fp), "line_number": ln} 
                for fp, ln in self.source_files
            ],
        }


class CommandDetector(ast.NodeVisitor):
    """AST visitor for detecting external command calls.
    
    Can be initialized without file_path for use in Analyzer,
    file_path is set when processing individual files.
    """
    
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path
        self.command_calls: list[CommandCall] = []
    
    def visit_Call(self, node: ast.Call) -> Any:
        """Visit function calls to detect external command invocations."""
        try:
            # Check for subprocess.run(), subprocess.Popen(), subprocess.call(), etc.
            if isinstance(node.func, ast.Attribute):
                # Handle subprocess.run(), subprocess.Popen(), etc.
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                    self._handle_subprocess_call(node)
                
                # Handle os.system(), os.popen()
                elif isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    self._handle_os_call(node)
            
            # Check for direct calls like run() if subprocess was imported as "from subprocess import run"
            elif isinstance(node.func, ast.Name):
                self._handle_direct_call(node)
        
        except (AttributeError, TypeError):
            pass
        
        self.generic_visit(node)
    
    def _handle_subprocess_call(self, node: ast.Call) -> None:
        """Handle subprocess module calls."""
        call_type = node.func.attr  # "run", "Popen", "call", "check_call", "check_output"
        
        # Only process certain subprocess functions
        if call_type not in ["run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"]:
            return
        
        # Extract command from arguments
        command = self._extract_command_from_args(node.args)
        if command:
            self.command_calls.append(CommandCall(
                command=command,
                file_path=self.file_path,
                line_number=node.lineno,
                call_type=f"subprocess.{call_type}",
                context=self._get_context_string(node),
            ))
    
    def _handle_os_call(self, node: ast.Call) -> None:
        """Handle os module calls."""
        call_type = node.func.attr  # "system", "popen"
        
        if call_type not in ["system", "popen"]:
            return
        
        # Extract command from arguments
        command = self._extract_command_from_args(node.args)
        if command:
            self.command_calls.append(CommandCall(
                command=command,
                file_path=self.file_path,
                line_number=node.lineno,
                call_type=f"os.{call_type}",
                context=self._get_context_string(node),
            ))
    
    def _handle_direct_call(self, node: ast.Call) -> None:
        """Handle direct function calls (e.g., from subprocess import run)."""
        func_name = node.func.id
        
        # Check if it's a subprocess function that was imported directly
        subprocess_funcs = ["run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"]
        if func_name in subprocess_funcs:
            command = self._extract_command_from_args(node.args)
            if command:
                self.command_calls.append(CommandCall(
                    command=command,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    call_type=f"subprocess.{func_name}",
                    context=self._get_context_string(node),
                ))
    
    def _extract_command_from_args(self, args: list[ast.expr]) -> str | None:
        """Extract command name from function arguments."""
        if not args:
            return None
        
        # First argument is usually the command
        first_arg = args[0]
        
        # If it's a string literal
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            # Extract first word from the command string
            # e.g., "ls -la" -> "ls", "grep pattern file.txt" -> "grep"
            command_str = first_arg.value.strip()
            if command_str:
                return command_str.split()[0]
        
        # If it's a list (common in subprocess.run(["ls", "-la"]))
        elif isinstance(first_arg, ast.List):
            if first_arg.elts and isinstance(first_arg.elts[0], ast.Constant):
                if isinstance(first_arg.elts[0].value, str):
                    return first_arg.elts[0].value.strip()
        
        # TODO: Handle more complex cases (variables, list comprehensions, etc.)
        
        return None
    
    def _get_context_string(self, node: ast.Call) -> str:
        """Get a string representation of the call context."""
        try:
            # Get a few lines of source code around the call
            # This is a simplified version - in practice you'd need the source code
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        except:
            return str(node)


def detect_commands_in_file(
    file_path: Path,
    cache: Optional[ASTCache] = None,
    use_cache: bool = True
) -> list[CommandCall]:
    """
    Detect external command calls in a Python file.
    
    Args:
        file_path: Path to Python file
        cache: ASTCache instance (uses global cache if None)
        use_cache: Whether to use AST caching
        
    Returns:
        List of CommandCall objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Use cache if available
    ast_data = None
    if use_cache:
        if cache is None:
            cache = get_global_cache()
        ast_data = cache.get_ast(file_path)
    
    if ast_data is None:
        # Read file and parse
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except (OSError, PermissionError, UnicodeDecodeError):
            return []
        
        try:
            ast_data = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return []
    
    detector = CommandDetector(file_path)
    detector.visit(ast_data)
    
    return detector.command_calls


def detect_commands_in_files_parallel(
    file_paths: list[Path],
    max_workers: Optional[int] = None,
    use_cache: bool = True,
    cache: Optional[ASTCache] = None
) -> list[CommandCall]:
    """
    Detect commands in multiple files in parallel.
    
    Args:
        file_paths: List of file paths to process
        max_workers: Maximum number of worker threads/processes
        use_cache: Whether to use AST caching
        cache: ASTCache instance (uses global cache if None)
        
    Returns:
        List of CommandCall objects from all files
    """
    all_commands: list[CommandCall] = []
    
    # Determine optimal number of workers
    if max_workers is None:
        # Use min(32, number_of_files + 4) as per concurrent.futures recommendation
        max_workers = min(32, len(file_paths) + 4)
    
    # Use ThreadPoolExecutor for I/O bound tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(detect_commands_in_file, file_path, cache, use_cache): file_path
            for file_path in file_paths
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                commands = future.result()
                all_commands.extend(commands)
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)
                # Continue with other files
    
    return all_commands


def load_command_mappings() -> dict[str, str]:
    """
    Load command-to-apt-package mappings from YAML file.
    
    Returns:
        Dictionary mapping command names to apt package names
    """
    # Default mappings for common bioinformatics and system tools
    default_mappings = {
        # System tools
        "ls": "coreutils",
        "grep": "grep",
        "awk": "gawk",
        "sed": "sed",
        "curl": "curl",
        "wget": "wget",
        "tar": "tar",
        "gzip": "gzip",
        "bzip2": "bzip2",
        "xz": "xz-utils",
        "unzip": "unzip",
        "ssh": "openssh-client",
        "scp": "openssh-client",
        "rsync": "rsync",
        "git": "git",
        
        # Bioinformatics tools
        "samtools": "samtools",
        "bcftools": "bcftools",
        "bwa": "bwa",
        "bowtie2": "bowtie2",
        "star": "star",
        "hisat2": "hisat2",
        "bedtools": "bedtools",
        "vcftools": "vcftools",
        "plink": "plink",
        "gatk": "gatk",
        "picard": "picard",
        "fastqc": "fastqc",
        "multiqc": "multiqc",
        "trimmomatic": "trimmomatic",
        "cutadapt": "cutadapt",
        "seqtk": "seqtk",
        "blastn": "ncbi-blast+",
        "blastp": "ncbi-blast+",
        "blastx": "ncbi-blast+",
        "tblastn": "ncbi-blast+",
        "tblastx": "ncbi-blast+",
        "makeblastdb": "ncbi-blast+",
        "hmmscan": "hmmer",
        "hmmsearch": "hmmer",
        "muscle": "muscle",
        "mafft": "mafft",
        "raxml": "raxml",
        "iqtree": "iqtree",
        "snpEff": "snpeff",
        "SnpSift": "snpsift",
        "vep": "ensembl-vep",
        
        # Python/development
        "python": "python3",
        "python3": "python3",
        "pip": "python3-pip",
        "conda": "conda",
        "docker": "docker.io",
        "jupyter": "jupyter",
        
        # R/Bioconductor
        "R": "r-base",
        "Rscript": "r-base",
    }
    
    # Try to load from YAML file if it exists
    mappings_file = Path(__file__).parent / "data" / "command_mappings.yaml"
    if mappings_file.exists() and yaml is not None:
        try:
            with open(mappings_file, encoding="utf-8") as f:
                user_mappings = yaml.safe_load(f)
                if isinstance(user_mappings, dict):
                    # Update defaults with user mappings
                    default_mappings.update(user_mappings)
        except Exception:
            pass  # Use defaults if YAML parsing fails
    
    return default_mappings


def map_commands_to_apt_packages(command_calls: list[CommandCall]) -> list[AptPackage]:
    """
    Map detected command calls to apt packages.
    
    Args:
        command_calls: List of CommandCall objects
        
    Returns:
        List of AptPackage objects
    """
    mappings = load_command_mappings()
    
    # Group command calls by command name
    command_groups: dict[str, list[tuple[Path, int]]] = {}
    for call in command_calls:
        if call.command not in command_groups:
            command_groups[call.command] = []
        command_groups[call.command].append((call.file_path, call.line_number))
    
    # Create AptPackage objects
    apt_packages: list[AptPackage] = []
    for command, sources in command_groups.items():
        # Look up apt package for this command
        package_name = mappings.get(command)
        
        # If not found, use the command name as package name (common convention)
        if not package_name:
            package_name = command
        
        apt_packages.append(AptPackage(
            package_name=package_name,
            command=command,
            source_files=sources,
        ))
    
    return apt_packages


def generate_apt_install_commands(apt_packages: list[AptPackage]) -> list[str]:
    """
    Generate apt-get install commands for Dockerfile.
    
    Args:
        apt_packages: List of AptPackage objects
        
    Returns:
        List of apt-get install commands
    """
    # Deduplicate package names
    package_names = sorted({pkg.package_name for pkg in apt_packages})
    
    if not package_names:
        return []
    
    # Generate apt-get install command
    # Split into multiple commands if there are many packages
    commands = []
    
    # First update package list
    commands.append("apt-get update")
    
    # Install packages (grouped to avoid command line length issues)
    max_packages_per_line = 10
    for i in range(0, len(package_names), max_packages_per_line):
        chunk = package_names[i:i + max_packages_per_line]
        install_cmd = f"apt-get install -y --no-install-recommends {' '.join(chunk)}"
        commands.append(install_cmd)
    
    # Clean up to reduce image size
    commands.append("apt-get clean")
    commands.append("rm -rf /var/lib/apt/lists/*")
    
    return commands


if __name__ == "__main__":
    """Test the command detector module."""
    import tempfile
    
    # Create a test Python file
    test_code = '''
import os
import subprocess
from subprocess import run

# Various command calls
os.system("ls -la")
subprocess.run(["grep", "pattern", "file.txt"])
subprocess.Popen(["samtools", "view", "file.bam"])
run(["bwa", "mem", "ref.fa", "reads.fastq"])
os.popen("wc -l file.txt")
subprocess.call("fastqc sample.fastq", shell=True)
'''
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        test_file = Path(f.name)
    
    try:
        print(f"Testing command detector with file: {test_file}")
        
        # Detect commands
        commands = detect_commands_in_file(test_file)
        
        print(f"\nDetected {len(commands)} command calls:")
        for cmd in commands:
            print(f"  - {cmd.command} at line {cmd.line_number} ({cmd.call_type})")
        
        # Map to apt packages
        apt_packages = map_commands_to_apt_packages(commands)
        
        print(f"\nMapped to {len(apt_packages)} apt packages:")
        for pkg in apt_packages:
            print(f"  - {pkg.command} -> {pkg.package_name}")
        
        # Generate apt install commands
        apt_commands = generate_apt_install_commands(apt_packages)
        
        print(f"\nGenerated apt install commands:")
        for cmd in apt_commands:
            print(f"  {cmd}")
        
    finally:
        # Clean up
        test_file.unlink()