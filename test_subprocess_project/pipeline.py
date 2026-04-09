#!/usr/bin/env python3
"""
Bioinformatics pipeline with subprocess calls to external tools.
"""

import subprocess
import os
from pathlib import Path

def run_fastqc(input_file: str, output_dir: str):
    """Run FastQC quality control."""
    cmd = ["fastqc", input_file, "-o", output_dir]
    subprocess.run(cmd, check=True)

def align_reads(ref_fa: str, reads_fq: str, output_sam: str):
    """Align reads using BWA."""
    cmd = f"bwa mem {ref_fa} {reads_fq} > {output_sam}"
    os.system(cmd)

def sort_bam(input_bam: str, output_bam: str):
    """Sort BAM file using samtools."""
    subprocess.call(["samtools", "sort", input_bam, "-o", output_bam])

def call_variants(bam_file: str, ref_fa: str, output_vcf: str):
    """Call variants using bcftools."""
    subprocess.run(f"samtools mpileup -f {ref_fa} {bam_file} | bcftools call -mv -Ov -o {output_vcf}", 
                   shell=True, check=True)

def run_multiqc(input_dir: str, output_dir: str):
    """Run MultiQC report generation."""
    from subprocess import Popen
    process = Popen(["multiqc", input_dir, "-o", output_dir])
    process.wait()

if __name__ == "__main__":
    print("Running bioinformatics pipeline...")
    # Example usage would go here
    pass
