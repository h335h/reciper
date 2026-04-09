#!/usr/bin/env python3
"""
Simple bioinformatics analysis script demonstrating common imports.
"""

import numpy as np
import pandas as pd
from Bio import SeqIO
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path


def read_fasta(file_path):
    """Read FASTA file using Biopython."""
    records = list(SeqIO.parse(file_path, "fasta"))
    print(f"Read {len(records)} sequences from {file_path}")
    return records


def analyze_sequences(records):
    """Perform simple sequence analysis."""
    lengths = [len(rec.seq) for rec in records]
    
    # Use numpy for statistics
    mean_len = np.mean(lengths)
    std_len = np.std(lengths)
    
    # Use pandas for data manipulation
    df = pd.DataFrame({
        'id': [rec.id for rec in records],
        'length': lengths,
        'description': [rec.description for rec in records]
    })
    
    return df, mean_len, std_len


def plot_length_distribution(lengths):
    """Plot sequence length distribution."""
    plt.figure(figsize=(10, 6))
    sns.histplot(lengths, bins=20, kde=True)
    plt.title('Sequence Length Distribution')
    plt.xlabel('Length (bp)')
    plt.ylabel('Frequency')
    plt.savefig('length_distribution.png')
    plt.close()


if __name__ == "__main__":
    print("Bioinformatics analysis example")
    
    # Check if input file exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Create a dummy FASTA file if needed
    fasta_file = data_dir / "sequences.fasta"
    if not fasta_file.exists():
        with open(fasta_file, "w") as f:
            f.write(">seq1\nATCGATCGATCG\n>seq2\nGCTAGCTAGCTA\n>seq3\nTTTTAAAACCCCGGGG\n")
    
    # Read and analyze sequences
    records = read_fasta(fasta_file)
    df, mean_len, std_len = analyze_sequences(records)
    
    print(f"Mean sequence length: {mean_len:.2f}")
    print(f"Standard deviation: {std_len:.2f}")
    print(f"DataFrame shape: {df.shape}")
    
    # Plot distribution
    lengths = df['length'].tolist()
    plot_length_distribution(lengths)
    
    print("Analysis complete!")