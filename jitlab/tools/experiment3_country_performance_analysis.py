#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_country_performance_analysis(country, workload_df, output_dir, prefix):
    """Create a performance analysis graph showing country-specific differences"""
    
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
    fig.suptitle(f'Performance Analysis - {country}', fontsize=16, fontweight='bold')
    
    # 1. Latency distribution over time
    latency_per_bin = country_workload.groupby('simulated_time_min')['latency_ms'].agg(['mean', 'std', 'min', 'max'])
    hours_index = latency_per_bin.index / 60.0
    
    ax1.plot(hours_index, latency_per_bin['mean'], 'b-', marker='o', markersize=4, linewidth=2, label='Mean Latency')
    ax1.fill_between(hours_index, 
                     latency_per_bin['mean'] - latency_per_bin['std'], 
                     latency_per_bin['mean'] + latency_per_bin['std'], 
                     alpha=0.3, color='blue', label='±1 Std Dev')
    ax1.plot(hours_index, latency_per_bin['min'], 'g--', alpha=0.7, label='Min Latency')
    ax1.plot(hours_index, latency_per_bin['max'], 'r--', alpha=0.7, label='Max Latency')
    
    ax1.set_xlabel('Simulated Time (hours)')
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title(f'{country} - Latency Performance Over Time')
    ax1.set_xticks(range(0, 24))
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. Workload intensity vs latency scatter
    ax2.scatter(country_workload['workload_factor'], country_workload['latency_ms'], 
               alpha=0.6, s=20, c=country_workload['simulated_time_hours'], cmap='viridis')
    ax2.set_xlabel('Workload Factor')
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title(f'{country} - Workload vs Latency Relationship')
    ax2.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(ax2.collections[0], ax=ax2)
    cbar.set_label('Time (hours)')
    
    # 3. Request pattern by endpoint
    endpoint_stats = country_workload.groupby('endpoint').agg({
        'latency_ms': ['mean', 'std', 'count'],
        'workload_factor': 'mean'
    }).round(2)
    
    endpoints = endpoint_stats.index
    latency_means = endpoint_stats[('latency_ms', 'mean')]
    latency_stds = endpoint_stats[('latency_ms', 'std')]
    request_counts = endpoint_stats[('latency_ms', 'count')]
    
    x_pos = np.arange(len(endpoints))
    bars = ax3.bar(x_pos, latency_means, yerr=latency_stds, capsize=5, alpha=0.7, 
                   color=['skyblue', 'lightcoral'][:len(endpoints)])
    ax3.set_xlabel('Endpoint')
    ax3.set_ylabel('Average Latency (ms)')
    ax3.set_title(f'{country} - Latency by Endpoint')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(endpoints)
    ax3.grid(True, alpha=0.3)
    
    # Add request count labels on bars
    for i, (bar, count) in enumerate(zip(bars, request_counts)):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + latency_stds.iloc[i] + 5,
                f'n={count}', ha='center', va='bottom', fontsize=9)
    
    # 4. Latency histogram
    ax4.hist(country_workload['latency_ms'], bins=20, alpha=0.7, color='purple', edgecolor='black')
    ax4.axvline(country_workload['latency_ms'].mean(), color='red', linestyle='--', linewidth=2, 
                label=f'Mean: {country_workload["latency_ms"].mean():.1f}ms')
    ax4.axvline(country_workload['latency_ms'].median(), color='orange', linestyle='--', linewidth=2,
                label=f'Median: {country_workload["latency_ms"].median():.1f}ms')
    ax4.set_xlabel('Latency (ms)')
    ax4.set_ylabel('Frequency')
    ax4.set_title(f'{country} - Latency Distribution')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the figure
    output_file = os.path.join(output_dir, f'{prefix}_performance_analysis_{country.replace(" ", "_")}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Generated performance analysis graph for {country}: {output_file}")
    
    # Print detailed statistics for this country
    print(f"\n=== {country.upper()} PERFORMANCE SUMMARY ===")
    print(f"Total Requests: {len(country_workload)}")
    print(f"Average Latency: {country_workload['latency_ms'].mean():.1f} ms")
    print(f"Median Latency: {country_workload['latency_ms'].median():.1f} ms")
    print(f"Min Latency: {country_workload['latency_ms'].min():.1f} ms")
    print(f"Max Latency: {country_workload['latency_ms'].max():.1f} ms")
    print(f"Latency Std Dev: {country_workload['latency_ms'].std():.1f} ms")
    print(f"95th Percentile: {country_workload['latency_ms'].quantile(0.95):.1f} ms")
    print(f"Average Workload Factor: {country_workload['workload_factor'].mean():.3f}")
    print(f"Peak Workload Factor: {country_workload['workload_factor'].max():.3f}")
    print(f"Success Rate: {(country_workload['status_code'] == 200).mean()*100:.1f}%")
    
    # Endpoint breakdown
    print(f"\nEndpoint Performance:")
    for endpoint in country_workload['endpoint'].unique():
        endpoint_data = country_workload[country_workload['endpoint'] == endpoint]
        print(f"  {endpoint}: {len(endpoint_data)} requests, avg {endpoint_data['latency_ms'].mean():.1f}ms")
    
    # Time-based analysis
    print(f"\nTime-based Performance:")
    for hour in sorted(country_workload['hour_local'].unique()):
        hour_data = country_workload[country_workload['hour_local'] == hour]
        print(f"  Hour {hour}: {len(hour_data)} requests, avg {hour_data['latency_ms'].mean():.1f}ms")


def main():
    ap = argparse.ArgumentParser(description="Create separate performance analysis graphs for each country")
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
    
    # Generate performance analysis graph for each country
    for country in countries:
        create_country_performance_analysis(country, workload_df, args.output_dir, args.out_prefix)
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Generated {len(countries)} country-specific performance analysis graphs")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
