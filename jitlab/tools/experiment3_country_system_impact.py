#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_country_system_analysis(country, workload_df, monitor_df, output_dir, prefix):
    """Create a system analysis graph showing how each country's requests impact system metrics"""
    
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
    fig.suptitle(f'System Analysis During {country} Workload', fontsize=16, fontweight='bold')
    
    # CPU usage with country request overlay
    ax1.plot(monitor_df['simulated_time_hours'], monitor_df['cpu_percent'], 'b-', linewidth=2, label='CPU Usage')
    
    # Overlay country request intensity
    country_requests_per_bin = country_workload.groupby('simulated_time_min').size()
    hours_index = country_requests_per_bin.index / 60.0
    ax1_twin = ax1.twinx()
    ax1_twin.bar(hours_index, country_requests_per_bin.values, alpha=0.3, color='red', width=0.4, label=f'{country} Requests')
    ax1_twin.set_ylabel(f'{country} Requests per 30-min bin', color='red')
    ax1_twin.tick_params(axis='y', labelcolor='red')
    
    ax1.set_xlabel('Simulated Time (hours)')
    ax1.set_ylabel('CPU Usage (%)', color='blue')
    ax1.set_title(f'CPU Usage During {country} Workload')
    ax1.set_xticks(range(0, 24))
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Memory usage with country request overlay
    ax2.plot(monitor_df['simulated_time_hours'], monitor_df['rss_mb'], 'g-', linewidth=2, label='Memory Usage')
    
    # Overlay country request intensity
    ax2_twin = ax2.twinx()
    ax2_twin.bar(hours_index, country_requests_per_bin.values, alpha=0.3, color='orange', width=0.4, label=f'{country} Requests')
    ax2_twin.set_ylabel(f'{country} Requests per 30-min bin', color='orange')
    ax2_twin.tick_params(axis='y', labelcolor='orange')
    
    ax2.set_xlabel('Simulated Time (hours)')
    ax2.set_ylabel('Memory Usage (MB)', color='green')
    ax2.set_title(f'Memory Usage During {country} Workload')
    ax2.set_xticks(range(0, 24))
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='y', labelcolor='green')
    
    # Power consumption with country request overlay
    ax3.plot(monitor_df['simulated_time_hours'], monitor_df['power_w'], 'r-', linewidth=2, label='Power Usage')
    
    # Overlay country request intensity
    ax3_twin = ax3.twinx()
    ax3_twin.bar(hours_index, country_requests_per_bin.values, alpha=0.3, color='purple', width=0.4, label=f'{country} Requests')
    ax3_twin.set_ylabel(f'{country} Requests per 30-min bin', color='purple')
    ax3_twin.tick_params(axis='y', labelcolor='purple')
    
    ax3.set_xlabel('Simulated Time (hours)')
    ax3.set_ylabel('Power (W)', color='red')
    ax3.set_title(f'Power Consumption During {country} Workload')
    ax3.set_xticks(range(0, 24))
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='y', labelcolor='red')
    
    # Energy consumption with country request overlay
    ax4.plot(monitor_df['simulated_time_hours'], monitor_df['energy_j_total'], 'm-', linewidth=2, label='Cumulative Energy')
    
    # Overlay country request intensity
    ax4_twin = ax4.twinx()
    ax4_twin.bar(hours_index, country_requests_per_bin.values, alpha=0.3, color='brown', width=0.4, label=f'{country} Requests')
    ax4_twin.set_ylabel(f'{country} Requests per 30-min bin', color='brown')
    ax4_twin.tick_params(axis='y', labelcolor='brown')
    
    ax4.set_xlabel('Simulated Time (hours)')
    ax4.set_ylabel('Cumulative Energy (J)', color='magenta')
    ax4.set_title(f'Energy Consumption During {country} Workload')
    ax4.set_xticks(range(0, 24))
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='y', labelcolor='magenta')
    
    plt.tight_layout()
    
    # Save the figure
    output_file = os.path.join(output_dir, f'{prefix}_system_during_{country.replace(" ", "_")}.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Generated system analysis during {country} workload: {output_file}")
    
    # Calculate correlation between country requests and system metrics
    # Simple correlation calculation without resampling
    try:
        # Get monitor data for the time period when this country was active
        country_start_time = country_workload['simulated_time_hours'].min()
        country_end_time = country_workload['simulated_time_hours'].max()
        
        # Filter monitor data to this country's active period
        monitor_during_country = monitor_df[
            (monitor_df['simulated_time_hours'] >= country_start_time) & 
            (monitor_df['simulated_time_hours'] <= country_end_time)
        ]
        
        if len(monitor_during_country) > 1 and len(country_requests_per_bin) > 1:
            # Simple correlation using available data points
            cpu_corr = np.corrcoef(monitor_during_country['cpu_percent'].values[:len(country_requests_per_bin)], 
                                  country_requests_per_bin.values)[0,1] if len(monitor_during_country) >= len(country_requests_per_bin) else 0
            memory_corr = np.corrcoef(monitor_during_country['rss_mb'].values[:len(country_requests_per_bin)], 
                                     country_requests_per_bin.values)[0,1] if len(monitor_during_country) >= len(country_requests_per_bin) else 0
        else:
            cpu_corr = memory_corr = 0
    except:
        cpu_corr = memory_corr = 0
    
    # Print summary statistics for this country
    print(f"\n=== {country.upper()} SYSTEM IMPACT SUMMARY ===")
    print(f"Total Requests: {len(country_workload)}")
    print(f"Average Latency: {country_workload['latency_ms'].mean():.1f} ms")
    print(f"Peak Latency: {country_workload['latency_ms'].max():.1f} ms")
    print(f"Average Workload Factor: {country_workload['workload_factor'].mean():.3f}")
    print(f"Peak Workload Factor: {country_workload['workload_factor'].max():.3f}")
    print(f"CPU Correlation with Requests: {cpu_corr:.3f}")
    print(f"Memory Correlation with Requests: {memory_corr:.3f}")
    print(f"System CPU Average: {monitor_df['cpu_percent'].mean():.1f}%")
    print(f"System CPU Peak: {monitor_df['cpu_percent'].max():.1f}%")
    print(f"System Memory Average: {monitor_df['rss_mb'].mean():.1f} MB")
    print(f"System Memory Peak: {monitor_df['rss_mb'].max():.1f} MB")


def main():
    ap = argparse.ArgumentParser(description="Create system analysis graphs showing how each country impacts system metrics")
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
        create_country_system_analysis(country, workload_df, monitor_df, args.output_dir, args.out_prefix)
    
    print(f"\n=== ANALYSIS COMPLETE ===")
    print(f"Generated {len(countries)} country-specific system impact analysis graphs")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
