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
import time
import json
import csv
import math
import httpx
from datetime import datetime, timedelta
import random

class GlobalWorkloadGenerator:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        
        # Timezone patterns based on the provided table
        self.timezone_patterns = {
            'europe': {
                'name': 'Europe (NL/DE/FR)',
                'start_day': 9.0,      # 09:00
                'morning_peak': (9.5, 12.0),  # 09:30-12:00
                'lunch_start': 12.0,   # 12:00
                'lunch_end': 13.0,     # 13:00 (1h lunch)
                'afternoon': (13.0, 15.5),    # 13:00-15:30
                'wind_down': (15.5, 17.0),    # 15:30-17:00
                'evening': None,       # Rare overtime
                'timezone_offset': 0   # UTC+1 (CET)
            },
            'us': {
                'name': 'US (East/West Coast)',
                'start_day': 8.5,      # 08:30
                'morning_peak': (9.0, 12.0),  # 09:00-12:00
                'lunch_start': 12.0,   # 12:00
                'lunch_end': 12.75,    # 12:45 (45m lunch)
                'afternoon': (13.0, 15.5),    # 13:00-15:30
                'wind_down': (15.5, 17.5),    # 15:30-17:30
                'evening': (17.5, 19.0),      # Sometimes emails, late calls
                'timezone_offset': -8  # UTC-8 (PST) or UTC-5 (EST)
            },
            'asia': {
                'name': 'Hong Kong/Asia',
                'start_day': 9.5,      # 09:30
                'morning_peak': (10.0, 13.0), # 10:00-13:00
                'lunch_start': 13.0,   # 13:00
                'lunch_end': 14.0,     # 14:00 (1h lunch, often later)
                'afternoon': (14.0, 17.0),    # 14:00-17:00
                'evening_peak': (17.0, 19.0), # 17:00-19:00
                'late_evening': (19.0, 20.0), # Often until 20:00+
                'timezone_offset': 8   # UTC+8 (HKT)
            }
        }

    def get_workload_factor(self, current_time, timezone):
        """Calculate workload factor based on timezone and time of day"""
        hour = current_time.hour
        minute = current_time.minute
        time_in_hours = hour + minute / 60.0
        
        pattern = self.timezone_patterns[timezone]
        
        # Adjust for timezone offset (simplified - just shift the time)
        adjusted_time = time_in_hours + pattern['timezone_offset']
        if adjusted_time < 0:
            adjusted_time += 24
        elif adjusted_time >= 24:
            adjusted_time -= 24
            
        # Calculate workload based on timezone pattern
        if timezone == 'europe':
            return self._get_europe_workload(adjusted_time)
        elif timezone == 'us':
            return self._get_us_workload(adjusted_time)
        elif timezone == 'asia':
            return self._get_asia_workload(adjusted_time)
        else:
            return 0.1

    def _get_europe_workload(self, time_hours):
        """Europe workload pattern"""
        if 9.0 <= time_hours < 9.5:  # 09:00-09:30 medium ramp-up
            return 0.6
        elif 9.5 <= time_hours < 12.0:  # 09:30-12:00 high focus
            return 1.0
        elif 12.0 <= time_hours < 13.0:  # 12:00-13:00 long lunch
            return 0.1
        elif 13.0 <= time_hours < 15.5:  # 13:00-15:30 medium
            return 0.7
        elif 15.5 <= time_hours < 17.0:  # 15:30-17:00 low, winding down
            return 0.4
        else:  # Evening - rare overtime
            return 0.05

    def _get_us_workload(self, time_hours):
        """US workload pattern"""
        if 8.5 <= time_hours < 9.0:  # 08:30-09:00 high focus start
            return 0.8
        elif 9.0 <= time_hours < 12.0:  # 09:00-12:00 high focus
            return 1.0
        elif 12.0 <= time_hours < 12.75:  # 12:00-12:45 short lunch
            return 0.2
        elif 13.0 <= time_hours < 15.5:  # 13:00-15:30 medium-high
            return 0.8
        elif 15.5 <= time_hours < 17.5:  # 15:30-17:30 medium
            return 0.6
        elif 17.5 <= time_hours < 19.0:  # 17:30-19:00 sometimes emails, late calls
            return 0.3
        else:
            return 0.05

    def _get_asia_workload(self, time_hours):
        """Asia workload pattern"""
        if 9.5 <= time_hours < 10.0:  # 09:30-10:00 high focus start
            return 0.8
        elif 10.0 <= time_hours < 13.0:  # 10:00-13:00 high focus
            return 1.0
        elif 13.0 <= time_hours < 14.0:  # 13:00-14:00 medium lunch
            return 0.3
        elif 14.0 <= time_hours < 17.0:  # 14:00-17:00 high
            return 0.9
        elif 17.0 <= time_hours < 19.0:  # 17:00-19:00 high
            return 1.0
        elif 19.0 <= time_hours < 20.0:  # 19:00-20:00 heavy workload
            return 0.8
        elif 20.0 <= time_hours < 22.0:  # 20:00+ common overtime
            return 0.6
        else:
            return 0.05

    async def worker(self, client, stop_event, results_queue, worker_id, timezone):
        """Worker that generates requests based on timezone workload"""
        request_count = 0
        while not stop_event.is_set():
            current_time = datetime.now()
            workload_factor = self.get_workload_factor(current_time, timezone)
            
            # Adjust request frequency based on workload
            base_delay = 1.5
            actual_delay = base_delay / workload_factor if workload_factor > 0 else base_delay * 5
            
            # Add randomness
            actual_delay *= (0.8 + 0.4 * random.random())
            
            try:
                await asyncio.sleep(actual_delay)
                
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
                            "prefix": f"{timezone}_{worker_id}"
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
                            "prefix": f"{timezone}_{worker_id}"
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
                            "prefix": f"{timezone}_{worker_id}"
                        }
                
                # Make request
                start_time = time.perf_counter()
                try:
                    response = await client.post(url, json=body, timeout=30.0)
                    await response.aread()
                    status_code = response.status_code
                except Exception as e:
                    status_code = -1
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000.0
                
                # Record result
                await results_queue.put({
                    'timestamp': time.time(),
                    'worker_id': worker_id,
                    'timezone': timezone,
                    'workload_factor': workload_factor,
                    'latency_ms': latency_ms,
                    'status_code': status_code,
                    'endpoint': 'cpu' if 'cpu' in url else 'files',
                    'hour': current_time.hour
                })
                
                # Print progress every 10 requests
                request_count += 1
                if request_count % 10 == 0:
                    print(f"Worker {worker_id} ({timezone}): {request_count} requests, workload={workload_factor:.2f}, latency={latency_ms:.1f}ms")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {worker_id} ({timezone}) error: {e}")

    async def run_experiment(self, workers_per_timezone=3, output_file="experiment3_global_workload.csv", duration_minutes=4):
        """Run the global workload experiment"""
        print(f"Starting Experiment 3: Global Workload Comparison")
        print(f"Duration: {duration_minutes} minutes (compressed 24-hour cycle), Workers per timezone: {workers_per_timezone}")
        print(f"Output: {output_file}")
        
        results_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_results(results_queue, output_file))
        
        # Start workers for each timezone
        async with httpx.AsyncClient(http2=False, timeout=30.0) as client:
            worker_tasks = []
            
            for timezone in ['europe', 'us', 'asia']:
                for i in range(workers_per_timezone):
                    task = asyncio.create_task(
                        self.worker(client, stop_event, results_queue, i, timezone)
                    )
                    worker_tasks.append(task)
            
            # Run for specified duration (compressed 24-hour cycle)
            print(f"Running experiment for {duration_minutes} minutes (compressed 24-hour cycle)...")
            print("Workers are generating requests...")
            
            # Show progress every 30 seconds
            start_time = time.time()
            while time.time() - start_time < duration_minutes * 60:
                await asyncio.sleep(30)
                elapsed = int(time.time() - start_time)
                remaining = duration_minutes * 60 - elapsed
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
        
        print(f"Experiment 3 completed. Results saved to {output_file}")

    async def monitor_results(self, results_queue, output_file):
        """Monitor and save results to CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'worker_id', 'timezone', 'workload_factor', 'latency_ms', 'status_code', 'endpoint', 'hour'])
            
            while True:
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                    writer.writerow([
                        result['timestamp'],
                        result['worker_id'],
                        result['timezone'],
                        f"{result['workload_factor']:.3f}",
                        f"{result['latency_ms']:.3f}",
                        result['status_code'],
                        result['endpoint'],
                        result['hour']
                    ])
                    f.flush()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Monitor error: {e}")
                    break

async def main():
    parser = argparse.ArgumentParser(description='Experiment 3: Global Workload Comparison')
    parser.add_argument('--url', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--workers', type=int, default=3, help='Number of workers per timezone')
    parser.add_argument('--output', default='experiment3_global_workload.csv', help='Output CSV file')
    parser.add_argument('--duration', type=int, default=4, help='Experiment duration in minutes')
    
    args = parser.parse_args()
    
    generator = GlobalWorkloadGenerator(args.url)
    
    await generator.run_experiment(args.workers, args.output, args.duration)

if __name__ == "__main__":
    asyncio.run(main())
