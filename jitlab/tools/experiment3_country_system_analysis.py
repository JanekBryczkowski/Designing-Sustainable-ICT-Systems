#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_system_graph_for_country(country, workload_df, monitor_df, output_dir, prefix):
    """Create a system analysis graph for a specific country"""
    
    # Filter workload data for this country
    country_workload = workload_df[workload_df['country'] == country].copy()
    
    if len(country_workload) == 0:
        print(f"No data found for country: {country}")
        return
    
    # Align timestamps (both should start from 0)
    country_workload['time_s'] = country_workload['timestamp'] - country_workload['timestamp'].min()
    monitor_df['time_s'] = monitor_df['ts'] - monitor_df['ts'].min()
    
    # Convert to simulated time bins (30-minute intervals)
    country_workload['simulated_time_min'] = country_workload.groupby(['country', 'worker_id']).cumcount() * 30
    country_workload['simulated_time_hours'] = country_workload['simulated_time_min'] / 60.0
    
    # Map real-time to simulated time for consistency
    max_simulated_time = country_workload['simulated_time_hours'].max()
    max_real_time = monitor_df['time_s'].max()
    
    # Create a mapping from real-time to simulated time
    monitor_df['simulated_time_hours'] = (monitor_df['time_s'] / max_real_time) * max_simulated_time
    
    # Create the figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'System Analysis - {country}', fontsize=16, fontweight='bold')
    
    # CPU usage
    ax1.plot(monitor_df['simulated_time_hours'], monitor_df['cpu_percent'], 'b-', linewidth=1)
    ax1.set_xlabel('Simulated Time (hours)')
    ax1.set_ylabel('CPU Usage (%)')
    ax1.set_title('CPU Usage Over Time')
    ax1.set_xticks(range(0, 24))  # Show all hours from 0 to 23
    ax1.grid(True, alpha=0.3)
    
    # Memory usage
    ax2.plot(monitor_df['simulated_time_hours'], monitor_df['rss_mb'], 'g-', linewidth=1)
    ax2.set_xlabel('Simulated Time (hours)')
    ax2.set_ylabel('Memory Usage (MB)')
    ax2.set_title('Memory Usage Over Time')
    ax2.set_xticks(range(0, 24))  # Show all hours from 0 to 23
    ax2.grid(True, alpha=0.3)
    
    # Power consumption
    ax3.plot(monitor_df['simulated_time_hours'], monitor_df['power_w'], 'r-', linewidth=1)
    ax3.set_xlabel('Simulated Time (hours)')
    ax3.set_ylabel('Power (W)')
    ax3.set_title('Power Consumption Over Time')
    ax3.set_xticks(range(0, 24))  # Show all hours from 0 to 23
    ax3.grid(True, alpha=0.3)
    
    # Energy consumption
    ax4.plot(monitor_df['simulated_time_hours'], monitor_df['energy_j_total'], 'm-', linewidth=1)
    ax4.set_xlabel('Simulated Time (hours)')
    ax4.set_ylabel('Cumulative Energy (J)')
    ax4.set_title('Cumulative Energy Consumption')
    ax4.set_xticks(range(0, 24))  # Show all hours from 0 to 23
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the figure
    output_file = os.path.join(output_dir, f'{prefix}_system_{country.replace(" ", "_")}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Generated system analysis graph for {country}: {output_file}")
    
    # Print summary statistics for this country
    print(f"\n=== {country.upper()} SYSTEM SUMMARY ===")
    print(f"Average CPU: {monitor_df['cpu_percent'].mean():.1f}%")
    print(f"Peak CPU: {monitor_df['cpu_percent'].max():.1f}%")
    print(f"Average Memory: {monitor_df['rss_mb'].mean():.1f} MB")
    print(f"Peak Memory: {monitor_df['rss_mb'].max():.1f} MB")
    print(f"Average Power: {monitor_df['power_w'].mean():.1f} W")
    print(f"Total Energy: {monitor_df['energy_j_total'].iloc[-1]:.1f} J")
    print(f"Total Requests: {len(country_workload)}")
    print(f"Average Latency: {country_workload['latency_ms'].mean():.1f} ms")


def main():
    ap = argparse.ArgumentParser(description="Create separate system analysis graphs for each country")
    ap.add_argument("--workload_csv", required=True, help="Comma-separated list of country workload CSV files")
    ap.add_argument("--monitor_csv", required=True, help="CSV output from monitor.py")
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
    
    monitor_df = pd.read_csv(args.monitor_csv)
    
    # Get unique countries
    countries = workload_df['country'].unique()
    print(f"Found countries: {', '.join(countries)}")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate system analysis graph for each country
    for country in countries:
        create_system_graph_for_country(country, workload_df, monitor_df, args.output_dir, args.out_prefix)
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Generated {len(countries)} country-specific system analysis graphs")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
