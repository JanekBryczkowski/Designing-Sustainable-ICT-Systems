#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_country_workload_analysis(country, workload_df, output_dir, prefix):
    """Create a workload-focused analysis graph for a specific country"""
    
    # Filter workload data for this country
    country_workload = workload_df[workload_df['country'] == country].copy()
    
    if len(country_workload) == 0:
        print(f"No data found for country: {country}")
        return
    
    # Align timestamps (both should start from 0)
    country_workload['time_s'] = country_workload['timestamp'] - country_workload['timestamp'].min()
    
    # Convert to simulated time bins (30-minute intervals)
    country_workload['simulated_time_min'] = country_workload.groupby(['country', 'worker_id']).cumcount() * 30
    country_workload['simulated_time_hours'] = country_workload['simulated_time_min'] / 60.0
    
    # Create the figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Workload Analysis - {country}', fontsize=16, fontweight='bold')
    
    # 1. Workload Factor over time
    workload_per_bin = country_workload.groupby('simulated_time_min')['workload_factor'].mean()
    hours_index = workload_per_bin.index / 60.0
    ax1.plot(hours_index, workload_per_bin.values, 'b-', marker='o', markersize=4, linewidth=2)
    ax1.set_xlabel('Simulated Time (hours)')
    ax1.set_ylabel('Average Workload Factor')
    ax1.set_title('Workload Intensity Over Time')
    ax1.set_xticks(range(0, 24))
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1.1)
    
    # 2. Latency over time
    latency_per_bin = country_workload.groupby('simulated_time_min')['latency_ms'].mean()
    hours_index = latency_per_bin.index / 60.0
    ax2.plot(hours_index, latency_per_bin.values, 'r-', marker='s', markersize=4, linewidth=2)
    ax2.set_xlabel('Simulated Time (hours)')
    ax2.set_ylabel('Average Latency (ms)')
    ax2.set_title('Response Latency Over Time')
    ax2.set_xticks(range(0, 24))
    ax2.grid(True, alpha=0.3)
    
    # 3. Request throughput over time
    throughput_per_bin = country_workload.groupby('simulated_time_min').size()
    hours_index = throughput_per_bin.index / 60.0
    ax3.plot(hours_index, throughput_per_bin.values, 'g-', marker='^', markersize=4, linewidth=2)
    ax3.set_xlabel('Simulated Time (hours)')
    ax3.set_ylabel('Requests per 30-min bin')
    ax3.set_title('Request Throughput Over Time')
    ax3.set_xticks(range(0, 24))
    ax3.grid(True, alpha=0.3)
    
    # 4. Status codes distribution
    status_counts = country_workload['status_code'].value_counts()
    colors = ['green' if code == 200 else 'red' for code in status_counts.index]
    ax4.bar(status_counts.index.astype(str), status_counts.values, color=colors, alpha=0.7)
    ax4.set_xlabel('HTTP Status Code')
    ax4.set_ylabel('Number of Requests')
    ax4.set_title('Request Success Rate')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the figure
    output_file = os.path.join(output_dir, f'{prefix}_workload_analysis_{country.replace(" ", "_")}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Generated workload analysis graph for {country}: {output_file}")
    
    # Print summary statistics for this country
    print(f"\n=== {country.upper()} WORKLOAD SUMMARY ===")
    print(f"Total Requests: {len(country_workload)}")
    print(f"Average Latency: {country_workload['latency_ms'].mean():.1f} ms")
    print(f"Min Latency: {country_workload['latency_ms'].min():.1f} ms")
    print(f"Max Latency: {country_workload['latency_ms'].max():.1f} ms")
    print(f"Average Workload Factor: {country_workload['workload_factor'].mean():.3f}")
    print(f"Peak Workload Factor: {country_workload['workload_factor'].max():.3f}")
    print(f"Success Rate: {(country_workload['status_code'] == 200).mean()*100:.1f}%")
    print(f"Unique Endpoints: {country_workload['endpoint'].nunique()}")
    print(f"Workers Used: {country_workload['worker_id'].nunique()}")


def main():
    ap = argparse.ArgumentParser(description="Create separate workload analysis graphs for each country")
    ap.add_argument("--workload_csv", required=True, help="Comma-separated list of country workload CSV files")
    ap.add_argument("--out_prefix", default="experiment3_analysis", help="Output file prefix")
    ap.add_argument("--output_dir", default=".", help="Output directory for generated graphs")
    args = ap.parse_args()

    # Load data
    csv_files = [f.strip() for f in args.workload_csv.split(',')]
    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        dfs.append(df)
    workload_df = pd.concat(dfs, ignore_index=True)
    
    # Get unique countries
    countries = workload_df['country'].unique()
    print(f"Found countries: {', '.join(countries)}")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate workload analysis graph for each country
    for country in countries:
        create_country_workload_analysis(country, workload_df, args.output_dir, args.out_prefix)
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Generated {len(countries)} country-specific workload analysis graphs")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
