#!/usr/bin/env python3
"""
Experiment Runner for JIT Optimization Study
Runs all three experiments with different JVM configurations to compare:
1. Baseline (default JIT)
2. Interpret-only (no JIT)
3. C2-only (disable tiered compilation)
4. C1-only (no C2 JIT)
5. Lower compile threshold
6. Single compiler thread
"""

import argparse
import subprocess
import time
import os
import sys
from datetime import datetime
from codecarbon import EmissionsTracker
import psutil
import re

# PROJECT_DIR = "/Users/jakubpataluch/IdeaProjects/Designing-Sustainable-ICT-Systems/jitlab"
# JAVA_HOME = "/Users/jakubpataluch/Library/Java/JavaVirtualMachines/openjdk-21.0.2/Contents/Home"
PROJECT_DIR = "/Users/janbryczkowski/IdeaProjects/Designing Sustainable ICT Systems/jitlab"
JAVA_HOME = "/Users/janbryczkowski/Library/Java/JavaVirtualMachines/openjdk-23.0.1/Contents/Home"

# Countries to investigate in Experiment
COUNTRIES_TO_TEST = [
    "Germany",
    "United States (Eastern)",
    "Japan",
    "France",
]

class ExperimentRunner:
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir = project_dir
        self.runs_dir = os.path.join(project_dir, "runs")
        self.tools_dir = os.path.join(project_dir, "tools")
        self.target_dir = os.path.join(project_dir, "target")
        
        # Ensure runs directory exists
        os.makedirs(self.runs_dir, exist_ok=True)
        
        # JVM configurations to test
        self.jvm_configs = {
            'baseline': {
                'name': 'Baseline (Default JIT)',
                'flags': [],
                'description': 'Standard JVM with default JIT compilation'
            },
            'interpret_only': {
                'name': 'Interpret-only (No JIT)',
                'flags': ['-Xint'],
                'description': 'No JIT compilation, pure interpretation'
            },
            'c2_only': {
                'name': 'C2-only (No Tiered Compilation)',
                'flags': ['-XX:-TieredCompilation'],
                'description': 'Skip C1, compile directly to C2'
            },
            'c1_only': {
                'name': 'C1-only (No C2 JIT)',
                'flags': ['-XX:+TieredCompilation', '-XX:TieredStopAtLevel=1'],
                'description': 'Stop compilation at C1 level'
            },
            'lower_threshold': {
                'name': 'Lower Compile Threshold',
                'flags': ['-XX:CompileThreshold=1000'],
                'description': 'Compile methods sooner (lower threshold)'
            },
            'single_compiler': {
                'name': 'Single Compiler Thread',
                'flags': ['-XX:CICompilerCount=1'],
                'description': 'Use only one compiler thread (slower warmup)'
            },
            'heap_sized': {
                'name': 'Fixed Heap Size',
                'flags': ['-Xms1g', '-Xmx1g'],
                'description': 'Fixed heap size to stabilize GC effects'
            }
        }
        
        # Experiment configurations
        self.experiments = {
            'experiment3': {
                'name': 'Global Workload Comparison',
                'script': 'experiment3_global_workload.py',
                'duration': 48,  # 48 seconds
                'workers': 5,  # per country
                'description': 'Compares 24-hour workload patterns across countries'
            }
        }

    def build_project(self):
        """Build the Java project"""
        print("Building Java project...")
        try:
            # Set JAVA_HOME to Java 23
            java_home = JAVA_HOME
            env = os.environ.copy()
            env['JAVA_HOME'] = java_home
            
            result = subprocess.run(
                ['mvn', 'clean', 'package', '-DskipTests'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            print("Build successful!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False

    def start_server(self, jvm_config_name, jvm_config):
        """Start the server with specified JVM configuration"""
        jar_path = os.path.join(self.target_dir, "jitlab-0.0.1-SNAPSHOT.jar")
        
        if not os.path.exists(jar_path):
            print(f"JAR file not found: {jar_path}")
            return None
        
        # Use Java 21+ explicitly
        java_home = JAVA_HOME
        java_executable = os.path.join(java_home, "bin", "java")
        
        # Build command
        cmd = [java_executable] + jvm_config['flags'] + ['-jar', jar_path]
        
        print(f"Starting server with {jvm_config['name']}...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            time.sleep(10)
            
            # Check if server is running
            if process.poll() is None:
                print(f"Server started successfully (PID: {process.pid})")
                return process
            else:
                print("Server failed to start")
                stdout, stderr = process.communicate()
                print(f"stdout: {stdout}")
                print(f"stderr: {stderr}")
                return None
                
        except Exception as e:
            print(f"Failed to start server: {e}")
            return None

    def stop_server(self, process):
        """Stop the server process"""
        if process and process.poll() is None:
            print("Stopping server...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing server...")
                process.kill()
                process.wait()
            print("Server stopped")

    def run_monitoring(self, duration_seconds, output_file):
        """Run system monitoring"""
        print(f"Starting monitoring for {duration_seconds} seconds...")
        
        # Find server process
        server_pid = None
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'jitlab-0.0.1-SNAPSHOT.jar' in cmdline:
                    server_pid = proc.info['pid']
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not server_pid:
            print("Could not find server process for monitoring")
            return None
        
        # Start monitoring
        monitor_cmd = [
            'python3', 'tools/monitor.py',
            '--pid', str(server_pid),
            '--interval', '1',
            '--duration', str(duration_seconds),
            '--out', output_file
        ]
        
        try:
            monitor_process = subprocess.Popen(
                monitor_cmd,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return monitor_process
        except Exception as e:
            print(f"Failed to start monitoring: {e}")
            return None

    def run_experiment(self, experiment_name, experiment_config, jvm_config_name, jvm_config):
        """Run a single experiment with specified JVM configuration"""
        print(f"\n{'='*60}")
        print(f"Running {experiment_config['name']} with {jvm_config['name']}")
        print(f"{'='*60}")
        
        # Generate output filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{experiment_name}_{jvm_config_name}_{timestamp}"

        # Create dated run directory: e.g., 13-oct-2025-run-1
        today_str = datetime.now().strftime("%d-%b-%Y").lower()
        pattern = re.compile(rf"^{re.escape(today_str)}-run-(\d+)$")
        existing = [d for d in os.listdir(self.runs_dir) if os.path.isdir(os.path.join(self.runs_dir, d))]
        nums = []
        for d in existing:
            m = pattern.match(d)
            if m:
                try:
                    nums.append(int(m.group(1)))
                except ValueError:
                    pass
        next_num = max(nums) + 1 if nums else 1
        run_dir = os.path.join(self.runs_dir, f"{today_str}-run-{next_num}")
        os.makedirs(run_dir, exist_ok=True)

        # Create separate output files for each country
        workload_outputs = {}
        for country in COUNTRIES_TO_TEST:
            # Clean country name for filename (remove special characters)
            clean_country = country.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')
            workload_outputs[country] = os.path.join(run_dir, f"{base_name}_workload_{clean_country}.csv")
        
        monitor_output = os.path.join(run_dir, f"{base_name}_monitor.csv")
        emissions_output = os.path.join(run_dir, f"{base_name}_emissions.csv")


        # Start server
        server_process = self.start_server(jvm_config_name, jvm_config)
        if not server_process:
            return False

        server_pid_to_track = server_process.pid

        # Measure emissions
        tracker = EmissionsTracker(
            project_name=f"{experiment_name}_{jvm_config_name}",
            output_dir=run_dir,
            output_file=os.path.basename(emissions_output),
            measure_power_secs=1,  # Sample every second
            log_level="warning",
            save_to_file=True,

        )
        tracker.start()
        
        try:
            # Start monitoring
            monitor_process = self.run_monitoring(experiment_config['duration'], monitor_output)
            
            # Wait a bit for monitoring to start
            time.sleep(2)
            
            # Run experiment
            # Pass duration in seconds (not minutes)
            duration_arg = str(experiment_config['duration'])
            
            # Pass base output path and let the script create separate files per country
            base_output_path = os.path.join(run_dir, f"{base_name}_workload")
            
            experiment_cmd = [
                'python3', f'tools/{experiment_config["script"]}',
                '--url', 'http://localhost:8080',
                '--workers', str(experiment_config['workers']),
                '--output', base_output_path,
                '--duration', duration_arg,
                '--countries', ','.join(COUNTRIES_TO_TEST),
                '--profiles', 'tools/country_workload_30min.csv',
                '--separate-files'  # Flag to enable separate files per country
            ]
            
            print(f"Running experiment: {' '.join(experiment_cmd)}")
            
            try:
                experiment_process = subprocess.Popen(
                    experiment_cmd,
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Stream output in real time
                while True:
                    output = experiment_process.stdout.readline()
                    if output == '' and experiment_process.poll() is not None:
                        break
                    if output:
                        print(output.strip())
                
                # Wait for process to complete
                return_code = experiment_process.wait()
                
                if return_code == 0:
                    print("Experiment completed successfully")
                else:
                    print(f"Experiment failed with return code {return_code}")
                    
            except Exception as e:
                print(f"Experiment error: {e}")
                experiment_process = None
            
            # Stop monitoring
            if monitor_process:
                monitor_process.terminate()
                try:
                    monitor_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    monitor_process.kill()

            tracker.stop()
            print(f"Detailed emissions log saved to {emissions_output}")

            # Check if files were created
            country_files_exist = all(os.path.exists(workload_outputs[country]) for country in COUNTRIES_TO_TEST)
            if country_files_exist and os.path.exists(monitor_output):
                print(f"Results saved:")
                for country in COUNTRIES_TO_TEST:
                    print(f"  {country}: {workload_outputs[country]}")
                print(f"  Monitor: {monitor_output}")

                # Generate per-country profiles plot
                try:
                    profiles_png = os.path.join(run_dir, f"{base_name}_profiles.png")
                    plot_cmd = [
                        'python3', 'tools/experiment3_country_plot.py',
                        '--profiles', 'tools/country_workload_30min.csv',
                        '--countries', ','.join(COUNTRIES_TO_TEST),
                        '--out', profiles_png
                    ]
                    print(f"Generating profiles plot: {' '.join(plot_cmd)}")
                    subprocess.run(plot_cmd, cwd=self.project_dir, check=False)
                    if os.path.exists(profiles_png):
                        print(f"  Profiles plot: {profiles_png}")
                    else:
                        print("  Profiles plot not generated")
                except Exception as e:
                    print(f"Failed to generate profiles plot: {e}")

                # Generate emissions  analysis
                try:
                    emissions_analysis_png = os.path.join(run_dir, f"{base_name}_emissions_analysis.png")
                    energy_analysis_png = os.path.join(run_dir, f"{base_name}_emissions_energy_analysis.png")
                    emissions_cmd = [
                        'python3', 'tools/analyze_emissions.py',
                        '--emissions_csv', emissions_output,
                        '--workload_csvs', ','.join([workload_outputs[country] for country in COUNTRIES_TO_TEST]),
                        '--emissions_out', emissions_analysis_png,
                        '--energy_out', energy_analysis_png
                    ]
                    print(f"Generating emissions analysis: {' '.join(emissions_cmd)}")
                    subprocess.run(emissions_cmd, cwd=self.project_dir, check=False)
                    if os.path.exists(emissions_analysis_png) and os.path.exists(energy_analysis_png):
                        print(f"  Emissions analysis plot: {emissions_analysis_png}")
                        print(f"  Energy analysis plot: {energy_analysis_png}")
                    else:
                        print("  Emissions analysis plots not generated")
                except Exception as e:
                    print(f"Failed to generate emissions analysis: {e}")


                # Generate one results plot with a line per country
                try:
                    results_png = os.path.join(run_dir, f"{base_name}_results.png")
                    # Pass all country files to the plotting script
                    country_files_arg = ','.join([workload_outputs[country] for country in COUNTRIES_TO_TEST])
                    plot_results_cmd = [
                        'python3', 'tools/experiment3_results_plot.py',
                        '--workload_csv', country_files_arg,
                        '--out', results_png
                    ]
                    print(f"Generating results plot: {' '.join(plot_results_cmd)}")
                    subprocess.run(plot_results_cmd, cwd=self.project_dir, check=False)
                    if os.path.exists(results_png):
                        print(f"  Results plot: {results_png}")
                    else:
                        print("  Results plot not generated")
                except Exception as e:
                    print(f"Failed to generate results plot: {e}")

                # Generate comprehensive analysis (throughput, latency, CPU, memory, power)
                try:
                    analysis_prefix = os.path.join(run_dir, f"{base_name}_analysis")
                    # Pass all country files to the analysis script
                    country_files_arg = ','.join([workload_outputs[country] for country in COUNTRIES_TO_TEST])
                    analysis_cmd = [
                        'python3', 'tools/experiment3_analysis.py',
                        '--workload_csv', country_files_arg,
                        '--monitor_csv', monitor_output,
                        '--out_prefix', analysis_prefix
                    ]
                    print(f"Generating comprehensive analysis: {' '.join(analysis_cmd)}")
                    subprocess.run(analysis_cmd, cwd=self.project_dir, check=False)
                    print(f"  Analysis plots: {analysis_prefix}_*.png")
                    
                    # Generate country-specific system impact analysis
                    try:
                        system_impact_cmd = [
                            'python3', 'tools/experiment3_country_system_impact.py',
                            '--workload_csv', country_files_arg,
                            '--monitor_csv', monitor_output,
                            '--out_prefix', analysis_prefix,
                            '--output_dir', run_dir
                        ]
                        print(f"Generating country-specific system impact analysis: {' '.join(system_impact_cmd)}")
                        subprocess.run(system_impact_cmd, cwd=self.project_dir, check=False)
                        print(f"  Country system impact plots: {analysis_prefix}_system_during_*.png")
                    except Exception as e:
                        print(f"  Warning: Country system impact analysis failed: {e}")
                    
                    # Generate country-specific performance analysis
                    try:
                        performance_cmd = [
                            'python3', 'tools/experiment3_country_performance_analysis.py',
                            '--workload_csv', country_files_arg,
                            '--out_prefix', analysis_prefix,
                            '--output_dir', run_dir
                        ]
                        print(f"Generating country-specific performance analysis: {' '.join(performance_cmd)}")
                        subprocess.run(performance_cmd, cwd=self.project_dir, check=False)
                        print(f"  Country performance plots: {analysis_prefix}_performance_analysis_*.png")
                    except Exception as e:
                        print(f"  Warning: Country performance analysis failed: {e}")
                        
                except Exception as e:
                    print(f"Failed to generate analysis: {e}")

                return True
            else:
                print("Results files not found")
                return False
                
        finally:
            # Stop server
            self.stop_server(server_process)
        
        return False

    def run_all_experiments(self, selected_experiments=None, selected_configs=None):
        """Run selected experiments with selected JVM configurations"""
        # Default: run only experiment3
        if selected_experiments is None:
            selected_experiments = ['experiment3']
        
        if selected_configs is None:
            selected_configs = list(self.jvm_configs.keys())
        
        # Build project first
        if not self.build_project():
            print("Failed to build project. Exiting.")
            return False
        
        results = {}
        
        for experiment_name in selected_experiments:
            if experiment_name not in self.experiments:
                print(f"Unknown experiment: {experiment_name}")
                continue
                
            experiment_config = self.experiments[experiment_name]
            results[experiment_name] = {}
            
            for jvm_config_name in selected_configs:
                if jvm_config_name not in self.jvm_configs:
                    print(f"Unknown JVM config: {jvm_config_name}")
                    continue
                
                jvm_config = self.jvm_configs[jvm_config_name]
                
                # Run experiment
                success = self.run_experiment(experiment_name, experiment_config, jvm_config_name, jvm_config)
                results[experiment_name][jvm_config_name] = success
                
                # Wait between experiments
                print("Waiting 10 seconds before next experiment...")
                time.sleep(10)
        
        # Print summary
        print(f"\n{'='*60}")
        print("EXPERIMENT SUMMARY")
        print(f"{'='*60}")
        
        for experiment_name, experiment_results in results.items():
            print(f"\n{self.experiments[experiment_name]['name']}:")
            for jvm_config_name, success in experiment_results.items():
                status = "\u2713" if success else "\u2717"
                print(f"  {status} {self.jvm_configs[jvm_config_name]['name']}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Run JIT optimization experiments')
    parser.add_argument('--experiments', nargs='+', 
                       choices=['experiment3'],
                       help='Specific experiments to run (default: experiment3)')
    parser.add_argument('--configs', nargs='+',
                       choices=['baseline', 'interpret_only', 'c2_only', 'c1_only', 
                               'lower_threshold', 'single_compiler', 'heap_sized'],
                       help='Specific JVM configs to test (default: all)')
    parser.add_argument('--project-dir', 
                       default=PROJECT_DIR,
                       help='Project directory path')
    
    args = parser.parse_args()
    
    runner = ExperimentRunner(args.project_dir)
    
    try:
        results = runner.run_all_experiments(args.experiments, args.configs)
        
        if results:
            print("\nAll experiments completed!")
        else:
            print("\nSome experiments failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
