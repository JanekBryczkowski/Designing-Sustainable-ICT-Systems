#!/usr/bin/env python3
"""
Experiment 2: Yearly Workload Simulation
Simulates a full year with seasonal patterns and major events:
- Christmas/New Year: High traffic (shopping, celebrations)
- Easter: Medium-high traffic
- Summer holidays: Low traffic (vacation period)
- Winter holidays: Medium traffic
- Major events: Spikes in traffic
- Regular business days: Normal patterns
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

class YearlyWorkloadGenerator:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.experiment_duration = 3 * 60  # 3 minutes (compressed year)
        self.start_time = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Define major events and their impact
        self.major_events = {
            # Christmas period (Dec 20 - Jan 5)
            (12, 20): 2.5,  # Peak shopping
            (12, 24): 3.0,  # Christmas Eve
            (12, 25): 1.5,  # Christmas Day (lower but still high)
            (12, 31): 2.8,  # New Year's Eve
            (1, 1): 2.0,    # New Year's Day
            
            # Easter period (varies by year, using 2024 dates)
            (3, 29): 1.8,   # Good Friday
            (3, 31): 1.6,   # Easter Sunday
            (4, 1): 1.4,    # Easter Monday
            
            # Summer holidays (July-August)
            (7, 4): 1.3,    # US Independence Day
            (7, 14): 1.2,   # Bastille Day
            (8, 15): 1.1,   # Assumption Day
            
            # Black Friday and Cyber Monday
            (11, 29): 3.2,  # Black Friday
            (12, 2): 2.8,   # Cyber Monday
            
            # Other major events
            (2, 14): 1.7,   # Valentine's Day
            (5, 1): 1.2,    # Labor Day
            (10, 31): 1.5,  # Halloween
            (11, 11): 1.3,  # Veterans Day
        }
        
        # Seasonal patterns
        self.seasonal_factors = {
            'winter': 1.2,   # Dec, Jan, Feb - higher activity
            'spring': 1.0,   # Mar, Apr, May - normal
            'summer': 0.7,   # Jun, Jul, Aug - vacation period
            'autumn': 1.1,   # Sep, Oct, Nov - back to work
        }

    def get_season(self, month):
        """Get season based on month"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'

    def get_workload_factor(self, current_time):
        """Calculate workload factor based on date and time (0.0 to 3.0+)"""
        month = current_time.month
        day = current_time.day
        hour = current_time.hour
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        
        # Base factor from season
        season = self.get_season(month)
        base_factor = self.seasonal_factors[season]
        
        # Check for major events
        event_factor = 1.0
        for (event_month, event_day), impact in self.major_events.items():
            if month == event_month and day == event_day:
                event_factor = impact
                break
        
        # Weekend vs weekday factor
        if weekday >= 5:  # Weekend
            weekend_factor = 0.3
        else:  # Weekday
            weekend_factor = 1.0
            
        # Time of day factor (similar to daily pattern but adjusted for events)
        if 9 <= hour < 12:
            time_factor = 1.0
        elif 12 <= hour < 13:
            time_factor = 0.3
        elif 13 <= hour < 17:
            time_factor = 0.8
        elif 17 <= hour < 19:
            time_factor = 0.6
        else:
            time_factor = 0.2
            
        # Special handling for major events (they override normal patterns)
        if event_factor > 2.0:  # Major shopping/celebration events
            time_factor = max(0.8, time_factor)  # High activity throughout the day
            weekend_factor = 1.0  # Events happen regardless of weekend
            
        # Combine all factors
        total_factor = base_factor * event_factor * weekend_factor * time_factor
        
        # Add some randomness to make it more realistic
        random_factor = 0.9 + 0.2 * random.random()
        total_factor *= random_factor
        
        return max(0.1, total_factor)

    async def worker(self, client, stop_event, results_queue, worker_id):
        """Worker that generates requests based on current workload"""
        request_count = 0
        while not stop_event.is_set():
            current_time = datetime.now()
            workload_factor = self.get_workload_factor(current_time)
            
            # Adjust request frequency based on workload
            base_delay = 2.0  # Base delay between requests
            actual_delay = base_delay / workload_factor if workload_factor > 0 else base_delay * 5
            
            # Add some randomness
            actual_delay *= (0.7 + 0.6 * random.random())
            
            try:
                await asyncio.sleep(actual_delay)
                
                if stop_event.is_set():
                    break
                    
                # Choose endpoint and parameters based on workload
                if workload_factor > 2.0:  # Major events - high load
                    url = f"{self.base_url}/work/cpu"
                    body = {
                        "iterations": int(5000 * min(workload_factor, 3.0)),
                        "payloadSize": int(30000 * min(workload_factor, 3.0))
                    }
                elif workload_factor > 1.5:  # High load
                    url = f"{self.base_url}/work/cpu"
                    body = {
                        "iterations": int(3000 * workload_factor),
                        "payloadSize": int(20000 * workload_factor)
                    }
                elif workload_factor > 0.8:  # Medium load
                    url = f"{self.base_url}/work/files"
                    body = {
                        "fileCount": int(8 * workload_factor),
                        "fileSizeBytes": int(150000 * workload_factor),
                        "prefix": f"yearly_{worker_id}"
                    }
                else:  # Low load
                    url = f"{self.base_url}/work/files"
                    body = {
                        "fileCount": max(1, int(3 * workload_factor)),
                        "fileSizeBytes": int(50000 * workload_factor),
                        "prefix": f"yearly_{worker_id}"
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
                    'workload_factor': workload_factor,
                    'latency_ms': latency_ms,
                    'status_code': status_code,
                    'endpoint': 'cpu' if 'cpu' in url else 'files',
                    'date': current_time.strftime('%Y-%m-%d'),
                    'hour': current_time.hour
                })
                
                # Print progress every 10 requests
                request_count += 1
                if request_count % 10 == 0:
                    print(f"Worker {worker_id}: {request_count} requests, workload={workload_factor:.2f}, latency={latency_ms:.1f}ms")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")

    async def run_experiment(self, num_workers=6, output_file="experiment2_yearly_workload.csv", duration_minutes=3):
        """Run the yearly workload experiment (compressed to specified minutes)"""
        print(f"Starting Experiment 2: Yearly Workload Simulation")
        print(f"Duration: {duration_minutes} minutes (compressed year), Workers: {num_workers}")
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
            
            # Run for specified duration
            print(f"Running experiment for {duration_minutes} minutes...")
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
        
        print(f"Experiment 2 completed. Results saved to {output_file}")

    async def monitor_results(self, results_queue, output_file):
        """Monitor and save results to CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'worker_id', 'workload_factor', 'latency_ms', 'status_code', 'endpoint', 'date', 'hour'])
            
            while True:
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                    writer.writerow([
                        result['timestamp'],
                        result['worker_id'],
                        f"{result['workload_factor']:.3f}",
                        f"{result['latency_ms']:.3f}",
                        result['status_code'],
                        result['endpoint'],
                        result['date'],
                        result['hour']
                    ])
                    f.flush()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Monitor error: {e}")
                    break

async def main():
    parser = argparse.ArgumentParser(description='Experiment 2: Yearly Workload Simulation')
    parser.add_argument('--url', default='http://localhost:8080', help='Server URL')
    parser.add_argument('--workers', type=int, default=6, help='Number of concurrent workers')
    parser.add_argument('--output', default='experiment2_yearly_workload.csv', help='Output CSV file')
    parser.add_argument('--duration', type=int, default=3, help='Experiment duration in minutes (compressed year)')
    
    args = parser.parse_args()
    
    generator = YearlyWorkloadGenerator(args.url)
    
    await generator.run_experiment(args.workers, args.output, args.duration)

if __name__ == "__main__":
    asyncio.run(main())
