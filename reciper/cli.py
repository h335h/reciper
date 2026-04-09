"""CLI interface for Reciper using Click."""

import argparse
import sys
from pathlib import Path

import click

from reciper.utils import print_error


@click.group()
def cli() -> None:
    """Reciper - Workflow Assumption Compiler (Minimal Viable Product)

    Generate reproducible environments for bioinformatics pipelines.
    """
    pass


def cli_progress_callback(
    scanned_dirs: int, scanned_files: int, found_files: int, current_dir: Path
) -> None:
    """
    CLI progress callback for directory scanning.

    Shows progress during directory scanning with incremental updates.
    Updates in place using carriage returns for a clean progress display.

    Args:
        scanned_dirs: Number of directories scanned so far
        scanned_files: Number of files examined so far
        found_files: Number of Python files found so far
        current_dir: Current directory being scanned
    """
    # Update progress in place with carriage return
    click.echo(
        f"\r  Scanning... Directories: {scanned_dirs}, "
        f"Files: {scanned_files}, "
        f"Python files: {found_files}",
        nl=False,
    )

    # Every 20 directories, show current directory on a new line
    if scanned_dirs % 20 == 0:
        click.echo(f"\n    Current directory: {current_dir}", nl=False)


def analyze_directory(
    directory_path: str,
    output_dir: str = ".",
    json_output: bool = False,
    report_file: str | None = None,
    no_lock: bool = False,
    no_verify: bool = False,
    verbose: bool = False,
    conflict_check: bool = True,
    parallel: bool = True,
    max_workers: int | None = None,
    no_cache: bool = False,
) -> bool:
    """
    Analyze all Python files in a directory and generate environment files.

    Args:
        directory_path: Path to directory to analyze
        output_dir: Directory where generated files should be placed
        json_output: Whether to output JSON report
        report_file: Optional path to save JSON report to file
        no_lock: Disable lock file generation
        no_verify: Skip verification step
        verbose: Detailed output with debug information
        conflict_check: Enable/disable conflict detection (default: enabled)
        parallel: Enable parallel processing (default: True)
        max_workers: Maximum number of worker threads (default: auto)
        no_cache: Disable AST caching (default: False, caching enabled)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import modules here to avoid circular imports
        from reciper.generator import generate_files
        from reciper.import_aggregator import aggregate_imports_from_files
        from reciper.mapper import map_to_conda, map_to_conda_with_details
        from reciper.parser import parse_imports
        from reciper.reporter import create_report_from_analysis
        from reciper.requirements_parser import (
            PackageRequirement,
            parse_dependency_file,
            requirements_to_dict,
        )
        from reciper.scanner import find_requirements_file, scan_directory
        
        # Show performance settings
        if verbose:
            click.echo(f"Performance settings: parallel={parallel}, max_workers={max_workers}, cache={not no_cache}")

        directory = Path(directory_path)

        # Step 1: Scan directory for Python files
        click.echo(f"Scanning directory: {directory}")
        click.echo("Looking for Python files...")

        file_infos = scan_directory(directory, progress_callback=cli_progress_callback)

        if not file_infos:
            print_error(f"No Python files found in {directory}")
            return False

        click.echo(f"\nFound {len(file_infos)} Python files in {directory}")

        # Step 2: Parse imports from all files
        click.echo("\nParsing imports from all files...")
        file_paths = [info.path for info in file_infos]
        
        # Use parallel processing and caching based on settings
        use_cache = not no_cache
        aggregator = aggregate_imports_from_files(
            file_paths,
            parse_imports,
            parallel=parallel,
            max_workers=max_workers,
            use_cache=use_cache
        )

        # Get aggregated packages
        all_packages = aggregator.get_all_packages()
        click.echo(
            f"Aggregated {len(all_packages)} unique packages from {len(file_paths)} files"
        )

        # Step 3: Look for requirements.txt
        click.echo("\nLooking for dependency files...")
        requirements_file = find_requirements_file(directory)

        requirements: list[PackageRequirement] = []
        requirements_dict = {}
        comparison = None
        if requirements_file:
            click.echo(f"Found dependency file: {requirements_file}")
            try:
                requirements = parse_dependency_file(requirements_file)
                requirements_dict = requirements_to_dict(requirements)
                click.echo(f"Parsed {len(requirements_dict)} package requirements")

                # Compare with imports
                from reciper.requirements_parser import compare_with_imports

                comparison = compare_with_imports(requirements_dict, all_packages)

                if comparison["missing"]:
                    click.echo(
                        f"Warning: {len(comparison['missing'])} imported packages missing from requirements:"
                    )
                    for pkg in comparison["missing"][:5]:  # Show first 5
                        click.echo(f"  - {pkg}")
                    if len(comparison["missing"]) > 5:
                        click.echo(f"  ... and {len(comparison['missing']) - 5} more")

                if comparison["extra"]:
                    click.echo(
                        f"Note: {len(comparison['extra'])} packages in requirements not imported:"
                    )
                    for pkg in comparison["extra"][:3]:
                        click.echo(f"  - {pkg}")
                    if len(comparison["extra"]) > 3:
                        click.echo(f"  ... and {len(comparison['extra']) - 3} more")

            except Exception as e:
                print_error(f"Could not parse {requirements_file}: {e}")
                click.echo("Continuing without requirements analysis...")

        # Step 4: Map Python packages to conda specifications with version info
        click.echo("\nMapping Python packages to conda specifications...")

        # Use version info from requirements for mapping
        conda_specs = map_to_conda(all_packages, requirements_dict)
        click.echo(f"Mapped to {len(conda_specs)} conda specifications")

        # Get detailed mapping for reporting
        mapped_packages_details = map_to_conda_with_details(
            all_packages, requirements_dict
        )

        # Step 5: Generate Dockerfile and environment.yml with subprocess command detection
        click.echo(f"\nGenerating files in {output_dir}...")
        click.echo("Scanning for subprocess calls to external tools (samtools, bwa, fastqc, etc.)...")
        
        # Pass Python files for command detection
        python_file_paths = [info.path for info in file_infos]
        generate_files(
            conda_specs,
            output_dir,
            python_files=python_file_paths,
            include_apt_detection=True,
            no_lock=no_lock,
            conflict_check=conflict_check
        )

        # Step 6: Run verification (if not disabled)
        verification_results = None
        if not no_verify:
            try:
                from reciper.verifier import verify_environment
                click.echo("\n" + "="*60)
                click.echo("VERIFICATION")
                click.echo("="*60)
                
                # Get package list for verification
                package_list = all_packages
                
                # Run verification
                verification_results = verify_environment(
                    package_list=package_list,
                    output_dir=output_dir,
                    verbose=verbose
                )
                
                # Print verification summary
                if verification_results.get("overall_success", False):
                    click.echo("✅ Verification passed")
                else:
                    click.echo("⚠️  Verification completed with issues")
                    
            except ImportError as e:
                click.echo(f"⚠️  Verification module not available: {e}")
            except Exception as e:
                click.echo(f"⚠️  Verification failed: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
        else:
            if verbose:
                click.echo("ℹ️  Verification skipped via --no-verify flag")

        # Step 7: Generate JSON report if requested
        warnings = []
        if comparison and comparison["missing"]:
            warnings.append(
                f"{len(comparison['missing'])} imported packages missing from requirements"
            )

        # Create JSON reporter
        if json_output or report_file:
            reporter = create_report_from_analysis(
                scan_directory=directory,
                file_infos=file_infos,
                imports=all_packages,
                requirements=requirements,
                mapped_packages=mapped_packages_details,
                unmapped_imports=[],  # TODO: Extract unmapped imports with file/line info
                warnings=warnings,
                dockerfile_generated=True,
                environment_yml_generated=True,
                lock_files_generated=not no_lock,
                verification_results=verification_results,
            )

            if report_file:
                try:
                    reporter.save_report(report_file)
                    click.echo(f"JSON report saved to: {report_file}")
                except Exception as e:
                    print_error(f"Failed to save JSON report: {e}")

            if json_output:
                click.echo("\n" + "=" * 60)
                click.echo("JSON REPORT")
                click.echo("=" * 60)
                reporter.print_report()

        # Print summary
        click.echo("\n" + "=" * 60)
        click.echo("ANALYSIS SUMMARY")
        click.echo("=" * 60)
        click.echo(f"Directory analyzed: {directory}")
        click.echo(f"Python files scanned: {len(file_paths)}")
        click.echo(f"Unique packages found: {len(all_packages)}")
        if requirements_dict:
            click.echo(f"Requirements parsed: {len(requirements_dict)} packages")
        click.echo(f"Conda specifications generated: {len(conda_specs)}")
        if json_output or report_file:
            click.echo(
                f"JSON report: {'printed to stdout' if json_output else ''}{' and saved to file' if report_file else ''}"
            )
        click.echo("=" * 60)

        return True

    except FileNotFoundError as e:
        print_error(f"Directory not found: {e}")
        return False
    except PermissionError as e:
        print_error(f"Permission denied: {e}")
        return False
    except ValueError as e:
        print_error(f"Invalid input: {e}")
        return False
    except OSError as e:
        print_error(f"File system error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def analyze_static(
    file_path: str,
    output_dir: str = ".",
    json_output: bool = False,
    report_file: str | None = None,
    no_lock: bool = False,
    no_verify: bool = False,
    verbose: bool = False,
    conflict_check: bool = True,
    parallel: bool = True,
    max_workers: int | None = None,
    no_cache: bool = False,
) -> bool:
    """
    Orchestrate the static analyzer MVP flow: parse → map → generate.

    Supports both single files and directories.

    Args:
        file_path: Path to Python source file or directory to analyze
        output_dir: Directory where generated files should be placed
        json_output: Whether to output JSON report
        report_file: Optional path to save JSON report to file
        no_lock: Disable lock file generation
        no_verify: Skip verification step
        verbose: Detailed output with debug information
        conflict_check: Enable/disable conflict detection (default: enabled)
        parallel: Enable parallel processing (default: True)
        max_workers: Maximum number of worker threads (default: auto)
        no_cache: Disable AST caching (default: False, caching enabled)

    Returns:
        True if successful, False otherwise
    """
    path = Path(file_path)

    if path.is_dir():
        return analyze_directory(
            file_path,
            output_dir,
            json_output,
            report_file,
            no_lock,
            no_verify,
            verbose,
            conflict_check,
            parallel,
            max_workers,
            no_cache
        )
    else:
        # Original single file analysis (simplified, no JSON support for single file)
        try:
            # Import modules here to avoid circular imports
            from reciper.generator import generate_files
            from reciper.mapper import map_to_conda
            from reciper.parser import parse_imports

            # Step 1: Parse imports from the Python file
            click.echo(f"Parsing imports from {file_path}...")
            python_packages = parse_imports(file_path)
            click.echo(
                f"Found {len(python_packages)} Python packages: {python_packages}"
            )

            # Step 2: Map Python packages to conda specifications
            click.echo("Mapping Python packages to conda specifications...")
            conda_specs = map_to_conda(python_packages)
            click.echo(
                f"Mapped to {len(conda_specs)} conda specifications: {conda_specs}"
            )

            # Step 3: Generate Dockerfile and environment.yml
            click.echo(f"Generating files in {output_dir}...")
            generate_files(
                conda_specs,
                output_dir,
                python_files=None,
                include_apt_detection=True,
                no_lock=no_lock,
                conflict_check=conflict_check
            )

            # Note: JSON reporting not fully supported for single file analysis in Week 2
            if json_output or report_file:
                click.echo(
                    "Note: JSON reporting is currently only fully supported for directory analysis"
                )

            return True

        except FileNotFoundError as e:
            print_error(f"File not found: {e}")
            return False
        except SyntaxError as e:
            print_error(f"Syntax error in Python file: {e}")
            return False
        except PermissionError as e:
            print_error(f"Permission denied: {e}")
            return False
        except ValueError as e:
            print_error(f"Invalid input: {e}")
            return False
        except OSError as e:
            print_error(f"File system error: {e}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            return False


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help="Output directory for generated files (default: current directory)",
)
@click.option("--json", "-j", is_flag=True, help="Output JSON report to stdout")
@click.option(
    "--report-file",
    "-r",
    type=click.Path(dir_okay=False, writable=True),
    help="Save JSON report to file",
)
@click.option(
    "--no-lock",
    is_flag=True,
    default=False,
    help="Disable lock file generation",
)
@click.option(
    "--no-verify",
    is_flag=True,
    default=False,
    help="Skip verification step",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Detailed output with debug information",
)
@click.option(
    "--conflict-check/--no-conflict-check",
    default=True,
    help="Enable/disable conflict detection (default: enabled)",
)
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Enable/disable parallel processing (default: enabled, auto-disabled for <50 files)",
)
@click.option(
    "--max-workers",
    type=int,
    default=None,
    help="Maximum number of worker threads (default: auto-calculated based on file count)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable AST caching (default: caching enabled)",
)
def analyze(
    path: str,
    output: str,
    json: bool,
    report_file: str,
    no_lock: bool,
    no_verify: bool,
    verbose: bool,
    conflict_check: bool,
    parallel: bool,
    max_workers: int | None,
    no_cache: bool,
) -> None:
    """
    Static analyzer MVP: Parse Python imports and generate Docker/conda files.

    PATH: Path to Python source file or directory to analyze
    """
    success = analyze_static(
        path,
        output,
        json,
        report_file,
        no_lock,
        no_verify,
        verbose,
        conflict_check,
        parallel,
        max_workers,
        no_cache
    )
    if success:
        click.echo("Success")
        sys.exit(0)
    else:
        sys.exit(1)


def main() -> None:
    """
    Main entry point that supports both argparse for static analyzer
    and Click for the full CLI.
    """
    # Check if we're being called with the static analyzer syntax
    # (simple file path argument without subcommand)
    if (
        len(sys.argv) > 1
        and not sys.argv[1].startswith("-")
        and sys.argv[1] != "analyze"
    ):
        # Parse with argparse for standalone static analyzer usage
        parser = argparse.ArgumentParser(
            description="Static analyzer MVP: Parse Python imports and generate Docker/conda files"
        )
        parser.add_argument(
            "path", help="Path to Python source file or directory to analyze"
        )
        parser.add_argument(
            "-o",
            "--output",
            default=".",
            help="Output directory for generated files (default: current directory)",
        )
        parser.add_argument(
            "-j", "--json", action="store_true", help="Output JSON report to stdout"
        )
        parser.add_argument("-r", "--report-file", help="Save JSON report to file")
        parser.add_argument(
            "--no-lock",
            action="store_true",
            default=False,
            help="Disable lock file generation",
        )
        parser.add_argument(
            "--no-verify",
            action="store_true",
            default=False,
            help="Skip verification step",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            default=False,
            help="Detailed output with debug information",
        )
        parser.add_argument(
            "--no-conflict-check",
            action="store_false",
            dest="conflict_check",
            default=True,
            help="Disable conflict detection",
        )
        parser.add_argument(
            "--conflict-check",
            action="store_true",
            dest="conflict_check",
            default=True,
            help="Enable conflict detection (default)",
        )
        parser.add_argument(
            "--no-parallel",
            action="store_false",
            dest="parallel",
            default=True,
            help="Disable parallel processing (default: enabled)",
        )
        parser.add_argument(
            "--max-workers",
            type=int,
            default=None,
            help="Maximum number of worker threads (default: auto-calculated)",
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            default=False,
            help="Disable AST caching (default: caching enabled)",
        )

        args = parser.parse_args()

        # Run the static analyzer
        success = analyze_static(
            args.path,
            args.output,
            args.json,
            args.report_file,
            args.no_lock,
            args.no_verify,
            args.verbose,
            args.conflict_check,
            args.parallel,
            args.max_workers,
            args.no_cache
        )
        if success:
            print("Success")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # Use Click CLI for all other commands
        cli()


if __name__ == "__main__":
    main()
