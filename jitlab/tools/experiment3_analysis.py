#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser(description="Analyze Experiment 3 results - throughput, latency, CPU, memory, power")
    ap.add_argument("--workload_csv", required=True, help="CSV output from experiment3_global_workload.py (single file) or comma-separated list of country files")
    ap.add_argument("--monitor_csv", required=True, help="CSV output from monitor.py")
    ap.add_argument("--out_prefix", default="experiment3_analysis", help="Output file prefix")
    args = ap.parse_args()

    # Load data
    # Check if multiple files are provided (comma-separated)
    if ',' in args.workload_csv:
        # Multiple files - one per country
        csv_files = [f.strip() for f in args.workload_csv.split(',')]
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        workload_df = pd.concat(dfs, ignore_index=True)
    else:
        # Single file
        workload_df = pd.read_csv(args.workload_csv)
    monitor_df = pd.read_csv(args.monitor_csv)
    
    # Align timestamps (both should start from 0)
    workload_df['time_s'] = workload_df['timestamp'] - workload_df['timestamp'].min()
    monitor_df['time_s'] = monitor_df['ts'] - monitor_df['ts'].min()
    
    # Convert to simulated time bins (30-minute intervals)
    # Each request represents a 30-minute time bin in the simulation
    workload_df['simulated_time_min'] = workload_df.groupby(['country', 'worker_id']).cumcount() * 30
    # Convert minutes to hours for x-axis display (0, 30, 60, 90... -> 0.0, 0.5, 1.0, 1.5...)
    workload_df['simulated_time_hours'] = workload_df['simulated_time_min'] / 60.0
    
    # 1. Throughput (workload-weighted requests per 30-min bin) by country
    plt.figure(figsize=(12, 8))
    
    # Calculate workload-weighted throughput per 30-minute bin by country
    for country in workload_df['country'].unique():
        country_data = workload_df[workload_df['country'] == country].copy()
        
        # Group by simulated time bins and calculate workload-weighted throughput
        # This represents the effective throughput considering workload intensity
        throughput_per_bin = country_data.groupby('simulated_time_min')['workload_factor'].sum()
        
        # Convert the index from minutes to hours for display
        hours_index = throughput_per_bin.index / 60.0
        
        plt.plot(hours_index, throughput_per_bin.values, label=f'{country}', marker='o', markersize=3)
    
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Workload-Weighted Throughput')
    plt.title('Workload-Weighted Throughput by Country (30-minute simulation bins)')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{args.out_prefix}_throughput.png', dpi=150)
    plt.close()
    
    # 2. Latency mean by country
    plt.figure(figsize=(12, 8))
    
    for country in workload_df['country'].unique():
        country_data = workload_df[workload_df['country'] == country].copy()
        
        # Group by simulated time bins (30-minute intervals) using minutes, then convert to hours for display
        latency_mean = country_data.groupby('simulated_time_min')['latency_ms'].mean()
        # Convert the index from minutes to hours for display
        hours_index = latency_mean.index / 60.0
        
        plt.plot(hours_index, latency_mean.values, label=f'{country}', linestyle='-', marker='o', markersize=3)
    
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Mean Latency (ms)')
    plt.title('Mean Latency by Country (30-minute simulation bins)')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{args.out_prefix}_latency.png', dpi=150)
    plt.close()
    
    # 3. System metrics (CPU, Memory, Power)
    plt.figure(figsize=(15, 10))
    
    # Map real-time to simulated time for consistency
    # Calculate the maximum simulated time from workload data
    max_simulated_time = workload_df['simulated_time_hours'].max()
    max_real_time = monitor_df['time_s'].max()
    
    # Create a mapping from real-time to simulated time
    monitor_df['simulated_time_hours'] = (monitor_df['time_s'] / max_real_time) * max_simulated_time
    
    # CPU usage
    plt.subplot(2, 2, 1)
    plt.plot(monitor_df['simulated_time_hours'], monitor_df['cpu_percent'], 'b-', linewidth=1)
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('CPU Usage (%)')
    plt.title('CPU Usage Over Time')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.grid(True, alpha=0.3)
    
    # Memory usage
    plt.subplot(2, 2, 2)
    plt.plot(monitor_df['simulated_time_hours'], monitor_df['rss_mb'], 'g-', linewidth=1)
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Memory Usage Over Time')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.grid(True, alpha=0.3)
    
    # Power consumption
    plt.subplot(2, 2, 3)
    plt.plot(monitor_df['simulated_time_hours'], monitor_df['power_w'], 'r-', linewidth=1)
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Power (W)')
    plt.title('Power Consumption Over Time')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.grid(True, alpha=0.3)
    
    # Energy consumption
    plt.subplot(2, 2, 4)
    plt.plot(monitor_df['simulated_time_hours'], monitor_df['energy_j_total'], 'm-', linewidth=1)
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Cumulative Energy (J)')
    plt.title('Cumulative Energy Consumption')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{args.out_prefix}_system.png', dpi=150)
    plt.close()
    
    # 4. Workload factor by country over time
    plt.figure(figsize=(12, 8))
    
    for country in workload_df['country'].unique():
        country_data = workload_df[workload_df['country'] == country].copy()
        
        # Group by simulated time bins (30-minute intervals) using minutes, then convert to hours for display
        workload_avg = country_data.groupby('simulated_time_min')['workload_factor'].mean()
        # Convert the index from minutes to hours for display
        hours_index = workload_avg.index / 60.0
        plt.plot(hours_index, workload_avg.values, label=f'{country}', marker='o', markersize=3)
    
    plt.xlabel('Simulated Time (hours)')
    plt.ylabel('Average Workload Factor')
    plt.title('Workload Factor by Country (30-minute simulation bins)')
    plt.xticks(range(0, 24))  # Show all hours from 0 to 23
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{args.out_prefix}_workload.png', dpi=150)
    plt.close()
    
    # 5. Summary statistics
    print(f"\n=== EXPERIMENT 3 ANALYSIS SUMMARY ===")
    print(f"Duration: {workload_df['time_s'].max():.1f} seconds")
    print(f"Total requests: {len(workload_df)}")
    print(f"Countries tested: {', '.join(workload_df['country'].unique())}")
    
    print(f"\n=== THROUGHPUT SUMMARY ===")
    for country in workload_df['country'].unique():
        country_data = workload_df[workload_df['country'] == country]
        total_requests = len(country_data)
        duration = country_data['time_s'].max() - country_data['time_s'].min()
        avg_rps = total_requests / duration if duration > 0 else 0
        print(f"{country}: {avg_rps:.2f} RPS average")
    
    print(f"\n=== LATENCY SUMMARY ===")
    for country in workload_df['country'].unique():
        country_data = workload_df[workload_df['country'] == country]
        print(f"{country}: Mean {country_data['latency_ms'].mean():.1f}ms")
    
    print(f"\n=== SYSTEM SUMMARY ===")
    print(f"Average CPU: {monitor_df['cpu_percent'].mean():.1f}%")
    print(f"Peak CPU: {monitor_df['cpu_percent'].max():.1f}%")
    print(f"Average Memory: {monitor_df['rss_mb'].mean():.1f} MB")
    print(f"Peak Memory: {monitor_df['rss_mb'].max():.1f} MB")
    print(f"Average Power: {monitor_df['power_w'].mean():.1f} W")
    print(f"Total Energy: {monitor_df['energy_j_total'].iloc[-1]:.1f} J")
    
    print(f"\n=== FILES GENERATED ===")
    print(f"  {args.out_prefix}_throughput.png - Throughput by country")
    print(f"  {args.out_prefix}_latency.png - Mean latency by country")
    print(f"  {args.out_prefix}_system.png - CPU, memory, power metrics")
    print(f"  {args.out_prefix}_workload.png - Workload factors by country")


if __name__ == "__main__":
    main()
