#!/usr/bin/env python3
"""
Results Analysis Script for JIT Optimization Experiments
Analyzes and compares performance and energy consumption across different JVM configurations
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
import warnings
warnings.filterwarnings('ignore')

class ResultsAnalyzer:
    def __init__(self, runs_dir="runs"):
        self.runs_dir = runs_dir
        self.results = {}
        self.jvm_configs = {
            'baseline': 'Baseline (Default JIT)',
            'interpret_only': 'Interpret-only (No JIT)',
            'c2_only': 'C2-only (No Tiered Compilation)',
            'c1_only': 'C1-only (No C2 JIT)',
            'lower_threshold': 'Lower Compile Threshold',
            'single_compiler': 'Single Compiler Thread',
            'heap_sized': 'Fixed Heap Size'
        }
        
        self.experiments = {
            'experiment1': 'Daily Workload Simulation',
            'experiment2': 'Yearly Workload Simulation',
            'experiment3': 'Global Workload Comparison',
            'experiment4': 'Burst Load Simulation'
        }

    def load_experiment_data(self, experiment_name, jvm_config):
        """Load data for a specific experiment and JVM configuration"""
        pattern = os.path.join(self.runs_dir, f"{experiment_name}_{jvm_config}_*")
        files = glob.glob(pattern)
        
        if not files:
            print(f"No files found for {experiment_name} with {jvm_config}")
            return None, None
        
        # Find the most recent files
        workload_file = None
        monitor_file = None
        
        for file in files:
            if '_workload.csv' in file:
                workload_file = file
            elif '_monitor.csv' in file:
                monitor_file = file
        
        if not workload_file or not monitor_file:
            print(f"Missing files for {experiment_name} with {jvm_config}")
            return None, None
        
        try:
            workload_df = pd.read_csv(workload_file)
            monitor_df = pd.read_csv(monitor_file)
            
            # Convert timestamps to relative time
            workload_df['relative_time'] = workload_df['timestamp'] - workload_df['timestamp'].min()
            monitor_df['relative_time'] = monitor_df['ts'] - monitor_df['ts'].min()
            
            return workload_df, monitor_df
        except Exception as e:
            print(f"Error loading data for {experiment_name} with {jvm_config}: {e}")
            return None, None

    def calculate_metrics(self, workload_df, monitor_df):
        """Calculate key performance and energy metrics"""
        if workload_df is None or monitor_df is None:
            return None
        
        metrics = {}
        
        # Workload metrics
        metrics['total_requests'] = len(workload_df)
        metrics['successful_requests'] = len(workload_df[workload_df['status_code'] == 200])
        metrics['failed_requests'] = len(workload_df[workload_df['status_code'] != 200])
        metrics['success_rate'] = metrics['successful_requests'] / metrics['total_requests'] if metrics['total_requests'] > 0 else 0
        
        # Latency metrics
        successful_requests = workload_df[workload_df['status_code'] == 200]
        if len(successful_requests) > 0:
            metrics['avg_latency_ms'] = successful_requests['latency_ms'].mean()
            metrics['p50_latency_ms'] = successful_requests['latency_ms'].median()
            metrics['p95_latency_ms'] = successful_requests['latency_ms'].quantile(0.95)
            metrics['p99_latency_ms'] = successful_requests['latency_ms'].quantile(0.99)
            metrics['max_latency_ms'] = successful_requests['latency_ms'].max()
        else:
            metrics['avg_latency_ms'] = 0
            metrics['p50_latency_ms'] = 0
            metrics['p95_latency_ms'] = 0
            metrics['p99_latency_ms'] = 0
            metrics['max_latency_ms'] = 0
        
        # Throughput metrics
        if len(workload_df) > 0:
            total_time = workload_df['relative_time'].max() - workload_df['relative_time'].min()
            metrics['avg_rps'] = len(workload_df) / total_time if total_time > 0 else 0
        else:
            metrics['avg_rps'] = 0
        
        # Energy metrics
        if len(monitor_df) > 0:
            metrics['avg_cpu_percent'] = monitor_df['cpu_percent'].mean()
            metrics['max_cpu_percent'] = monitor_df['cpu_percent'].max()
            metrics['avg_memory_mb'] = monitor_df['rss_mb'].mean()
            metrics['max_memory_mb'] = monitor_df['rss_mb'].max()
            metrics['avg_power_w'] = monitor_df['power_w'].mean()
            metrics['total_energy_j'] = monitor_df['energy_j_total'].iloc[-1] if len(monitor_df) > 0 else 0
            metrics['energy_per_request_j'] = metrics['total_energy_j'] / metrics['total_requests'] if metrics['total_requests'] > 0 else 0
        else:
            metrics['avg_cpu_percent'] = 0
            metrics['max_cpu_percent'] = 0
            metrics['avg_memory_mb'] = 0
            metrics['max_memory_mb'] = 0
            metrics['avg_power_w'] = 0
            metrics['total_energy_j'] = 0
            metrics['energy_per_request_j'] = 0
        
        return metrics

    def analyze_experiment(self, experiment_name):
        """Analyze all JVM configurations for a specific experiment"""
        print(f"\nAnalyzing {self.experiments[experiment_name]}...")
        
        experiment_results = {}
        
        for jvm_config in self.jvm_configs.keys():
            workload_df, monitor_df = self.load_experiment_data(experiment_name, jvm_config)
            metrics = self.calculate_metrics(workload_df, monitor_df)
            
            if metrics:
                experiment_results[jvm_config] = {
                    'metrics': metrics,
                    'workload_df': workload_df,
                    'monitor_df': monitor_df
                }
                print(f"  ✓ {self.jvm_configs[jvm_config]}: {metrics['total_requests']} requests, {metrics['avg_rps']:.2f} RPS, {metrics['total_energy_j']:.2f} J")
            else:
                print(f"  ✗ {self.jvm_configs[jvm_config]}: No data")
        
        return experiment_results

    def create_comparison_plots(self, experiment_name, experiment_results):
        """Create comparison plots for an experiment"""
        if not experiment_results:
            return
        
        # Prepare data for plotting
        configs = []
        metrics_data = []
        
        for jvm_config, data in experiment_results.items():
            if data and 'metrics' in data:
                configs.append(self.jvm_configs[jvm_config])
                metrics_data.append(data['metrics'])
        
        if not metrics_data:
            return
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(metrics_data, index=configs)
        
        # Set up the plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Create subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{self.experiments[experiment_name]} - JVM Configuration Comparison', fontsize=16)
        
        # 1. Throughput comparison
        axes[0, 0].bar(configs, comparison_df['avg_rps'])
        axes[0, 0].set_title('Average Throughput (RPS)')
        axes[0, 0].set_ylabel('Requests per Second')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. Latency comparison (P95)
        axes[0, 1].bar(configs, comparison_df['p95_latency_ms'])
        axes[0, 1].set_title('95th Percentile Latency')
        axes[0, 1].set_ylabel('Latency (ms)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Energy consumption
        axes[0, 2].bar(configs, comparison_df['total_energy_j'])
        axes[0, 2].set_title('Total Energy Consumption')
        axes[0, 2].set_ylabel('Energy (Joules)')
        axes[0, 2].tick_params(axis='x', rotation=45)
        
        # 4. Energy per request
        axes[1, 0].bar(configs, comparison_df['energy_per_request_j'])
        axes[1, 0].set_title('Energy per Request')
        axes[1, 0].set_ylabel('Energy (Joules/Request)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 5. CPU usage
        axes[1, 1].bar(configs, comparison_df['avg_cpu_percent'])
        axes[1, 1].set_title('Average CPU Usage')
        axes[1, 1].set_ylabel('CPU %')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        # 6. Memory usage
        axes[1, 2].bar(configs, comparison_df['avg_memory_mb'])
        axes[1, 2].set_title('Average Memory Usage')
        axes[1, 2].set_ylabel('Memory (MB)')
        axes[1, 2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        output_file = f"analysis_{experiment_name}_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Comparison plot saved: {output_file}")
        plt.close()

    def create_timeline_plots(self, experiment_name, experiment_results):
        """Create timeline plots showing performance over time"""
        if not experiment_results:
            return
        
        # Create timeline plots for key metrics
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{self.experiments[experiment_name]} - Performance Timeline', fontsize=16)
        
        # Plot 1: Throughput over time
        axes[0, 0].set_title('Throughput Over Time')
        axes[0, 0].set_xlabel('Time (seconds)')
        axes[0, 0].set_ylabel('Requests per Second')
        
        # Plot 2: Latency over time
        axes[0, 1].set_title('Latency Over Time')
        axes[0, 1].set_xlabel('Time (seconds)')
        axes[0, 1].set_ylabel('Latency (ms)')
        
        # Plot 3: CPU usage over time
        axes[1, 0].set_title('CPU Usage Over Time')
        axes[1, 0].set_xlabel('Time (seconds)')
        axes[1, 0].set_ylabel('CPU %')
        
        # Plot 4: Power consumption over time
        axes[1, 1].set_title('Power Consumption Over Time')
        axes[1, 1].set_xlabel('Time (seconds)')
        axes[1, 1].set_ylabel('Power (Watts)')
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(experiment_results)))
        
        for i, (jvm_config, data) in enumerate(experiment_results.items()):
            if not data or 'workload_df' not in data or 'monitor_df' not in data:
                continue
            
            workload_df = data['workload_df']
            monitor_df = data['monitor_df']
            
            if len(workload_df) == 0 or len(monitor_df) == 0:
                continue
            
            # Calculate RPS over time (1-second windows)
            workload_df['time_bucket'] = (workload_df['relative_time'] // 1).astype(int)
            rps_over_time = workload_df.groupby('time_bucket').size()
            
            # Plot throughput
            axes[0, 0].plot(rps_over_time.index, rps_over_time.values, 
                           label=self.jvm_configs[jvm_config], color=colors[i], alpha=0.7)
            
            # Plot latency (P95 over time)
            latency_over_time = workload_df.groupby('time_bucket')['latency_ms'].quantile(0.95)
            axes[0, 1].plot(latency_over_time.index, latency_over_time.values, 
                           label=self.jvm_configs[jvm_config], color=colors[i], alpha=0.7)
            
            # Plot CPU usage
            axes[1, 0].plot(monitor_df['relative_time'], monitor_df['cpu_percent'], 
                           label=self.jvm_configs[jvm_config], color=colors[i], alpha=0.7)
            
            # Plot power consumption
            axes[1, 1].plot(monitor_df['relative_time'], monitor_df['power_w'], 
                           label=self.jvm_configs[jvm_config], color=colors[i], alpha=0.7)
        
        # Add legends
        for ax in axes.flat:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        output_file = f"analysis_{experiment_name}_timeline.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Timeline plot saved: {output_file}")
        plt.close()

    def generate_summary_report(self, all_results):
        """Generate a comprehensive summary report"""
        report = []
        report.append("# JIT Optimization Experiment Results Summary")
        report.append("=" * 50)
        report.append("")
        
        for experiment_name, experiment_results in all_results.items():
            if not experiment_results:
                continue
            
            report.append(f"## {self.experiments[experiment_name]}")
            report.append("")
            
            # Create summary table
            summary_data = []
            for jvm_config, data in experiment_results.items():
                if data and 'metrics' in data:
                    metrics = data['metrics']
                    summary_data.append({
                        'Configuration': self.jvm_configs[jvm_config],
                        'Total Requests': metrics['total_requests'],
                        'Success Rate': f"{metrics['success_rate']:.2%}",
                        'Avg RPS': f"{metrics['avg_rps']:.2f}",
                        'P95 Latency (ms)': f"{metrics['p95_latency_ms']:.2f}",
                        'Total Energy (J)': f"{metrics['total_energy_j']:.2f}",
                        'Energy/Request (J)': f"{metrics['energy_per_request_j']:.4f}",
                        'Avg CPU %': f"{metrics['avg_cpu_percent']:.1f}",
                        'Avg Memory (MB)': f"{metrics['avg_memory_mb']:.1f}"
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                report.append(summary_df.to_string(index=False))
                report.append("")
                
                # Find best performers
                baseline_data = None
                for data in summary_data:
                    if 'Baseline' in data['Configuration']:
                        baseline_data = data
                        break
                
                if baseline_data:
                    report.append("### Key Findings:")
                    report.append("")
                    
                    # Find best RPS
                    best_rps = max(summary_data, key=lambda x: float(x['Avg RPS']))
                    report.append(f"- **Highest Throughput**: {best_rps['Configuration']} ({best_rps['Avg RPS']} RPS)")
                    
                    # Find lowest latency
                    best_latency = min(summary_data, key=lambda x: float(x['P95 Latency (ms)']))
                    report.append(f"- **Lowest Latency**: {best_latency['Configuration']} ({best_latency['P95 Latency (ms)']} ms)")
                    
                    # Find most energy efficient
                    best_energy = min(summary_data, key=lambda x: float(x['Energy/Request (J)']))
                    report.append(f"- **Most Energy Efficient**: {best_energy['Configuration']} ({best_energy['Energy/Request (J)']} J/request)")
                    
                    report.append("")
            
            report.append("---")
            report.append("")
        
        # Save report
        report_text = "\n".join(report)
        with open("experiment_results_summary.md", "w") as f:
            f.write(report_text)
        
        print("Summary report saved: experiment_results_summary.md")
        return report_text

    def run_analysis(self, selected_experiments=None):
        """Run complete analysis for all experiments"""
        if selected_experiments is None:
            selected_experiments = list(self.experiments.keys())
        
        print("Starting JIT Optimization Analysis...")
        print("=" * 50)
        
        all_results = {}
        
        for experiment_name in selected_experiments:
            if experiment_name not in self.experiments:
                print(f"Unknown experiment: {experiment_name}")
                continue
            
            # Analyze experiment
            experiment_results = self.analyze_experiment(experiment_name)
            all_results[experiment_name] = experiment_results
            
            # Create plots
            self.create_comparison_plots(experiment_name, experiment_results)
            self.create_timeline_plots(experiment_name, experiment_results)
        
        # Generate summary report
        self.generate_summary_report(all_results)
        
        print("\nAnalysis completed!")
        print("Generated files:")
        print("- experiment_results_summary.md")
        for experiment_name in selected_experiments:
            print(f"- analysis_{experiment_name}_comparison.png")
            print(f"- analysis_{experiment_name}_timeline.png")

def main():
    parser = argparse.ArgumentParser(description='Analyze JIT optimization experiment results')
    parser.add_argument('--runs-dir', default='runs', help='Directory containing experiment results')
    parser.add_argument('--experiments', nargs='+', 
                       choices=['experiment1', 'experiment2', 'experiment3', 'experiment4'],
                       help='Specific experiments to analyze (default: all)')
    
    args = parser.parse_args()
    
    analyzer = ResultsAnalyzer(args.runs_dir)
    analyzer.run_analysis(args.experiments)

if __name__ == "__main__":
    main()
