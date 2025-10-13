#!/usr/bin/env python3
"""
Experiment 3: Global Workload Comparison
Simulates workload patterns across different time zones:
- Europe (NL/DE/FR): 09:00-17:00 with 1h lunch break
- US (East/West Coast): 08:30-17:30 with short lunch breaks
- Hong Kong/Asia: 09:30-20:00+ with heavy evening workload
"""

import argparse
import asyncio
import csv
import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

# Optional plotting of country profiles
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None


class GlobalWorkloadGenerator:
    def __init__(self, base_url="http://localhost:8080", profiles_csv_path="country_workload_30min.csv", countries=None):
        self.base_url = base_url
        self.profiles_csv_path = profiles_csv_path
        self.country_profiles = self._load_country_profiles(self.profiles_csv_path)
        self.countries = countries or list(self.country_profiles.keys())

        # Minimal country -> primary timezone mapping for provided sample countries
        # Extend this map as you add countries to the CSV
        self.country_timezones = {
            "Germany": "Europe/Berlin",
            "France": "Europe/Paris",
            "Netherlands": "Europe/Amsterdam",
            "United Kingdom": "Europe/London",
            "United States (Eastern)": "America/New_York",
            "United States (Pacific)": "America/Los_Angeles",
            "Japan": "Asia/Tokyo",
            "South Korea": "Asia/Seoul",
            "China": "Asia/Shanghai",
            "India": "Asia/Kolkata",
            "Hong Kong": "Asia/Hong_Kong",
        }

        # Fallback if a country timezone is missing
        for c in self.countries:
            if c not in self.country_timezones:
                self.country_timezones[c] = "UTC"

    def _load_country_profiles(self, csv_path):
        profiles = {}
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            # Expect 49 columns: country + 48 half-hour bins
            for row in reader:
                if not row:
                    continue
                country = row[0].strip()
                try:
                    values = [float(x) for x in row[1:49]]
                except Exception:
                    continue
                if len(values) == 48:
                    profiles[country] = values
        return profiles

    def get_country_workload_factor(self, hour, minute, country):
        idx = hour * 2 + (1 if minute >= 30 else 0)
        idx = max(0, min(47, idx))
        values = self.country_profiles.get(country)
        if not values:
            return 0.1
        result = max(0.01, values[idx])
        return result

    async def worker(self, client, stop_event, results_queue, worker_id, country, duration_seconds):
        """Worker that generates requests based on per-country workload profile"""
        request_count = 0
        # Calculate delay: experiment duration in seconds divided by 48 (half-hour bins)
        base_delay = duration_seconds / 48
        
        while not stop_event.is_set():
            # Calculate simulated time based on request count
            # Each request represents one half-hour bin in the 24-hour cycle
            # Simple approach: request_count 0 = 00:00, request_count 1 = 00:30, etc.
            simulated_hour = (request_count * 30) // 60
            simulated_minute = (request_count * 30) % 60
            workload_factor = self.get_country_workload_factor(simulated_hour, simulated_minute, country)

            try:
                # Wait for the calculated delay
                try:
                    await asyncio.wait_for(asyncio.sleep(base_delay), timeout=base_delay + 1.0)
                except asyncio.TimeoutError:
                    break

                if stop_event.is_set():
                    break
                

                # Choose endpoint based on workload (both endpoints used with different frequency)
                if workload_factor > 0.8:  # High load: 75% CPU, 25% files
                    if random.random() < 0.75:
                        url = f"{self.base_url}/work/cpu"
                        body = {
                            "iterations": min(50000000, int(12000 * workload_factor)),  # Cap at 50M
                            "payloadSize": min(1000000, int(60000 * workload_factor))  # Cap at 1M
                        }
                    else:
                        url = f"{self.base_url}/work/files"
                        body = {
                            "fileCount": min(500, int(8 * workload_factor)),  # Cap at 500 files
                            "fileSizeBytes": min(10000000, int(100000 * workload_factor)),  # Cap at 10MB
                            "prefix": f"{country}_{worker_id}"
                        }
                elif workload_factor > 0.5:  # Medium load: 50% CPU, 50% files
                    if random.random() < 0.5:
                        url = f"{self.base_url}/work/cpu"
                        body = {
                            "iterations": min(50000000, int(8000 * workload_factor)),  # Cap at 50M
                            "payloadSize": min(1000000, int(40000 * workload_factor))  # Cap at 1M
                        }
                    else:
                        url = f"{self.base_url}/work/files"
                        body = {
                            "fileCount": min(500, int(12 * workload_factor)),  # Cap at 500 files
                            "fileSizeBytes": min(10000000, int(150000 * workload_factor)),  # Cap at 10MB
                            "prefix": f"{country}_{worker_id}"
                        }
                else:  # Low load: 15% CPU, 85% files
                    if random.random() < 0.15:
                        url = f"{self.base_url}/work/cpu"
                        body = {
                            "iterations": min(50000000, int(4000 * workload_factor)),  # Cap at 50M
                            "payloadSize": min(1000000, int(20000 * workload_factor))  # Cap at 1M
                        }
                    else:
                        url = f"{self.base_url}/work/files"
                        body = {
                            "fileCount": max(1, min(500, int(4 * workload_factor))),  # Cap at 500 files
                            "fileSizeBytes": min(10000000, int(80000 * workload_factor)),  # Cap at 10MB
                            "prefix": f"{country}_{worker_id}"
                        }

                # Make request
                request_start_time = time.perf_counter()
                try:
                    response = await client.post(url, json=body, timeout=30.0)
                    await response.aread()
                    status_code = response.status_code
                except Exception as e:
                    status_code = -1

                end_time = time.perf_counter()
                latency_ms = (end_time - request_start_time) * 1000.0


                # Record result
                result = {
                    'timestamp': time.time(),
                    'worker_id': worker_id,
                    'country': country,
                    'workload_factor': workload_factor,
                    'latency_ms': latency_ms,
                    'status_code': status_code,
                    'endpoint': 'cpu' if 'cpu' in url else 'files',
                    'hour_local': simulated_hour,
                    'minute_local': simulated_minute
                }
                await results_queue.put(result)

                # Print progress every 10 requests
                request_count += 1
                if request_count % 10 == 0:
                    print(f"Worker {worker_id} ({country}): {request_count} requests, workload={workload_factor:.2f}, latency={latency_ms:.1f}ms")
                

            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                print(f"Worker {worker_id} ({country}) error: {e}")
        

    async def run_experiment(self, workers_per_country=3, output_file="experiment3_global_workload.csv", duration_seconds=240, separate_files=False):
        """Run the global workload experiment"""
        print(f"Starting Experiment 3: Global Workload Comparison")
        print(f"Duration: {duration_seconds} seconds (compressed 24-hour cycle), Workers per country: {workers_per_country}")
        
        if separate_files:
            # Create separate output files for each country
            output_files = {}
            for country in self.countries:
                clean_country = country.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')
                output_files[country] = f"{output_file}_{clean_country}.csv"
            print(f"Output files: {list(output_files.values())}")
        else:
            print(f"Output: {output_file}")
            output_files = {country: output_file for country in self.countries}

        results_queue = asyncio.Queue()
        stop_event = asyncio.Event()

        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_results(results_queue, output_files, separate_files))

        # Start workers for each selected country
        async with httpx.AsyncClient(http2=False, timeout=30.0) as client:
            worker_tasks = []

            for country in self.countries:
                for i in range(workers_per_country):
                    task = asyncio.create_task(
                        self.worker(client, stop_event, results_queue, i, country, duration_seconds)
                    )
                    worker_tasks.append(task)

            # Run for specified duration (compressed 24-hour cycle)
            print(f"Running experiment for {duration_seconds} seconds (compressed 24-hour cycle)...")
            print("Workers are generating requests...")

            # Show progress every 10 seconds (or duration if shorter)
            start_time = time.time()
            progress_interval = min(10, duration_seconds)
            while time.time() - start_time < duration_seconds:
                await asyncio.sleep(progress_interval)
                elapsed = int(time.time() - start_time)
                remaining = duration_seconds - elapsed
                print(f"Progress: {elapsed}s elapsed, {remaining}s remaining")

            # Stop workers
            print("Stopping workers...")
            stop_event.set()
            await asyncio.gather(*worker_tasks, return_exceptions=True)

            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        if separate_files:
            print(f"Experiment 3 completed. Results saved to separate files:")
            for country, output_file in output_files.items():
                print(f"  {country}: {output_file}")
        else:
            print(f"Experiment 3 completed. Results saved to {output_file}")

    async def monitor_results(self, results_queue, output_files, separate_files=False):
        """Monitor and save results to CSV"""
        if separate_files:
            # Open separate files for each country
            file_handles = {}
            writers = {}
            for country, output_file in output_files.items():
                f = open(output_file, 'w', newline='')
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'worker_id', 'country', 'workload_factor', 'latency_ms', 'status_code', 'endpoint', 'hour_local', 'minute_local'])
                file_handles[country] = f
                writers[country] = writer
        else:
            # Use single file (backward compatibility)
            output_file = list(output_files.values())[0]
            f = open(output_file, 'w', newline='')
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'worker_id', 'country', 'workload_factor', 'latency_ms', 'status_code', 'endpoint', 'hour_local', 'minute_local'])
            file_handles = {'all': f}
            writers = {'all': writer}

        try:
            while True:
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                    
                    if separate_files:
                        # Write to country-specific file
                        country = result['country']
                        if country in writers:
                            writers[country].writerow([
                                result['timestamp'],
                                result['worker_id'],
                                result['country'],
                                f"{result['workload_factor']:.3f}",
                                f"{result['latency_ms']:.3f}",
                                result['status_code'],
                                result['endpoint'],
                                result['hour_local'],
                                result['minute_local']
                            ])
                            file_handles[country].flush()
                    else:
                        # Write to single file
                        writers['all'].writerow([
                            result['timestamp'],
                            result['worker_id'],
                            result['country'],
                            f"{result['workload_factor']:.3f}",
                            f"{result['latency_ms']:.3f}",
                            result['status_code'],
                            result['endpoint'],
                            result['hour_local'],
                            result['minute_local']
                        ])
                        file_handles['all'].flush()
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Monitor error: {e}")
                    break
        finally:
            # Close all file handles
            for f in file_handles.values():
                f.close()

    def plot_country_profiles(self, out_png="experiment3_country_profiles.png"):
        if plt is None:
            print("matplotlib not available; skipping profile plot")
            return
        x = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0,30)]
        for c in self.countries:
            values = self.country_profiles.get(c)
            if values:
                plt.plot(range(48), values, label=c)
        plt.xticks(ticks=list(range(0,48,2)), labels=[x[i] for i in range(0,48,2)], rotation=45, ha='right')
        plt.xlabel("Local Time (30-min bins)")
        plt.ylabel("Workload factor (relative)")
        plt.title("Per-country workload profiles")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close()
        print(f"Saved {out_png}")


async def main():
    parser = argparse.ArgumentParser(description='Experiment 3: Global Workload Comparison')
    parser.add_argument('--url', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--workers', type=int, default=3, help='Number of workers per country')
    parser.add_argument('--output', default='experiment3_global_workload.csv', help='Output CSV file')
    parser.add_argument('--duration', type=int, default=240, help='Experiment duration in seconds')
    parser.add_argument('--profiles', default='country_workload_30min.csv', help='CSV with 48-bin per-country profiles')
    parser.add_argument('--countries', default='', help='Comma-separated list of countries to include')
    parser.add_argument('--plot-profiles', action='store_true', help='Plot per-country profiles and exit')
    parser.add_argument('--separate-files', action='store_true', help='Create separate output files for each country')

    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(',') if c.strip()] if args.countries else None
    generator = GlobalWorkloadGenerator(args.url, args.profiles, countries)

    if args.plot_profiles:
        generator.plot_country_profiles()
        return

    await generator.run_experiment(args.workers, args.output, args.duration, args.separate_files)


if __name__ == "__main__":
    asyncio.run(main())
