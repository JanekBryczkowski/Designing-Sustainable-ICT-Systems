#!/usr/bin/env python3
"""
Experiment 1: Daily Workload Simulation
Simulates a typical working day with:
- 9:00-12:00: High traffic (morning rush)
- 12:00-13:00: Lunch break (low traffic)
- 13:00-17:00: Steady traffic (afternoon work)
- 17:00-18:00: Wind down (decreasing traffic)
"""

import argparse
import asyncio
import time
import json
import csv
import math
import httpx
from datetime import datetime, timedelta

class DailyWorkloadGenerator:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.experiment_duration = 3 * 60  # 3 minutes (compressed 24-hour day)
        self.start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
    def get_workload_factor(self, current_time):
        """Calculate workload factor based on time of day (0.0 to 1.0) for 24-hour cycle"""
        hour = current_time.hour
        minute = current_time.minute
        time_in_minutes = hour * 60 + minute
        
        # 0:00-6:00: Very low traffic (night)
        if 0 <= time_in_minutes < 6*60:
            factor = 0.05
            
        # 6:00-9:00: Gradual ramp-up (early morning)
        elif 6*60 <= time_in_minutes < 9*60:
            # Linear increase from 0.05 to 0.6
            progress = (time_in_minutes - 6*60) / (3*60)
            factor = 0.05 + progress * 0.55
            
        # 9:00-12:00: High traffic (morning rush)
        elif 9*60 <= time_in_minutes < 12*60:
            # Peak at 10:30, gradual increase and decrease
            peak_time = 10.5 * 60
            distance_from_peak = abs(time_in_minutes - peak_time)
            max_distance = 1.5 * 60  # 1.5 hours from peak
            factor = max(0.3, 1.0 - (distance_from_peak / max_distance) * 0.4)
            
        # 12:00-13:00: Lunch break (low traffic)
        elif 12*60 <= time_in_minutes < 13*60:
            factor = 0.1
            
        # 13:00-17:00: Steady traffic (afternoon work)
        elif 13*60 <= time_in_minutes < 17*60:
            # Slight peak around 14:30, then gradual decrease
            peak_time = 14.5 * 60
            distance_from_peak = abs(time_in_minutes - peak_time)
            max_distance = 2 * 60  # 2 hours from peak
            factor = max(0.4, 0.8 - (distance_from_peak / max_distance) * 0.3)
            
        # 17:00-19:00: Wind down (decreasing traffic)
        elif 17*60 <= time_in_minutes < 19*60:
            # Linear decrease from 0.4 to 0.1
            progress = (time_in_minutes - 17*60) / (2*60)
            factor = 0.4 - progress * 0.3
            
        # 19:00-22:00: Evening low activity
        elif 19*60 <= time_in_minutes < 22*60:
            factor = 0.1
            
        # 22:00-24:00: Very low traffic (late night)
        else:
            factor = 0.05
            
        return max(0.05, min(1.0, factor))

    async def worker(self, client, stop_event, results_queue, worker_id):
        """Worker that generates requests based on current workload"""
        request_count = 0
        while not stop_event.is_set():
            current_time = datetime.now()
            workload_factor = self.get_workload_factor(current_time)
            
            # Adjust request frequency based on workload
            base_delay = 1.0  # Base delay between requests
            actual_delay = base_delay / workload_factor if workload_factor > 0 else base_delay * 10
            
            # Add some randomness to make it more realistic
            actual_delay *= (0.8 + 0.4 * (time.time() % 1))  # ±20% variation
            
            try:
                await asyncio.sleep(actual_delay)
                
                if stop_event.is_set():
                    break
                    
                # Choose endpoint based on workload (more CPU-intensive during high load)
                if workload_factor > 0.7:
                    # High load: CPU-intensive work
                    url = f"{self.base_url}/work/cpu"
                    body = {
                        "iterations": int(3000 * workload_factor),
                        "payloadSize": int(25000 * workload_factor)
                    }
                else:
                    # Lower load: File operations
                    url = f"{self.base_url}/work/files"
                    body = {
                        "fileCount": max(1, int(5 * workload_factor)),
                        "fileSizeBytes": int(100000 * workload_factor),
                        "prefix": f"daily_{worker_id}"
                    }
                
                # Make request
                start_time = time.perf_counter()
                try:
                    response = await client.post(url, json=body, timeout=30.0)
                    await response.aread()  # Ensure full response is read
                    status_code = response.status_code
                except Exception as e:
                    status_code = -1
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000.0
                
                # Record result
                await results_queue.put({
                    'timestamp': time.time(),
                    'worker_id': worker_id,
                    'workload_factor': workload_factor,
                    'latency_ms': latency_ms,
                    'status_code': status_code,
                    'endpoint': 'cpu' if 'cpu' in url else 'files'
                })
                
                # Print progress every 10 requests
                request_count += 1
                if request_count % 10 == 0:
                    print(f"Worker {worker_id}: {request_count} requests, workload={workload_factor:.2f}, latency={latency_ms:.1f}ms")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")

    async def run_experiment(self, num_workers=8, output_file="experiment1_daily_workload.csv"):
        """Run the daily workload experiment"""
        print(f"Starting Experiment 1: Daily Workload Simulation")
        print(f"Duration: 3 minutes (compressed 24-hour day), Workers: {num_workers}")
        print(f"Output: {output_file}")
        
        results_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_results(results_queue, output_file))
        
        # Start workers
        async with httpx.AsyncClient(http2=False, timeout=30.0) as client:
            worker_tasks = [
                asyncio.create_task(self.worker(client, stop_event, results_queue, i))
                for i in range(num_workers)
            ]
            
            # Run for 3 minutes (compressed 24-hour day)
            print("Running experiment for 3 minutes (compressed 24-hour day)...")
            print("Workers are generating requests...")
            
            # Show progress every 30 seconds
            start_time = time.time()
            while time.time() - start_time < self.experiment_duration:
                await asyncio.sleep(30)
                elapsed = int(time.time() - start_time)
                remaining = self.experiment_duration - elapsed
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
        
        print(f"Experiment 1 completed. Results saved to {output_file}")

    async def monitor_results(self, results_queue, output_file):
        """Monitor and save results to CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'worker_id', 'workload_factor', 'latency_ms', 'status_code', 'endpoint'])
            
            while True:
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                    writer.writerow([
                        result['timestamp'],
                        result['worker_id'],
                        f"{result['workload_factor']:.3f}",
                        f"{result['latency_ms']:.3f}",
                        result['status_code'],
                        result['endpoint']
                    ])
                    f.flush()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Monitor error: {e}")
                    break

async def main():
    parser = argparse.ArgumentParser(description='Experiment 1: Daily Workload Simulation')
    parser.add_argument('--url', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--workers', type=int, default=8, help='Number of concurrent workers')
    parser.add_argument('--output', default='experiment1_daily_workload.csv', help='Output CSV file')
    parser.add_argument('--duration', type=int, default=3*60, help='Experiment duration in seconds')
    
    args = parser.parse_args()
    
    generator = DailyWorkloadGenerator(args.url)
    generator.experiment_duration = args.duration
    
    await generator.run_experiment(args.workers, args.output)

if __name__ == "__main__":
    asyncio.run(main())
