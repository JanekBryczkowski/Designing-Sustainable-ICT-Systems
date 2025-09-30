#!/usr/bin/env python3
"""
Experiment 4: Burst Load Simulation
Alternates between idle (low traffic) and burst (extreme traffic) phases.
"""

import argparse
import asyncio
import time
import csv
import random
import httpx

class BurstWorkloadGenerator:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.experiment_duration = 3 * 60  # 3 minutes
        self.burst_duration = 30  # seconds
        self.idle_duration = 15   # seconds

    def get_phase(self, elapsed):
        """Return 'burst' or 'idle' based on elapsed time"""
        cycle_time = self.burst_duration + self.idle_duration
        return "burst" if (elapsed % cycle_time) < self.burst_duration else "idle"

    async def worker(self, client, stop_event, results_queue, worker_id):
        start = time.time()

        while not stop_event.is_set():
            elapsed = int(time.time() - start)
            phase = self.get_phase(elapsed)

            if phase == "burst":
                # Burst: 95% CPU, 5% files
                if random.random() < 0.95:
                    url = f"{self.base_url}/work/cpu"
                    body = {"iterations": 100000, "payloadSize": 500000}
                else:
                    url = f"{self.base_url}/work/files"
                    body = {"fileCount": 10, "fileSizeBytes": 500000, "prefix": f"burst_{worker_id}"}
                delay = 0.05  # very aggressive
            else:
                # Idle: mostly files, light load
                if random.random() < 0.2:
                    url = f"{self.base_url}/work/cpu"
                    body = {"iterations": 2000, "payloadSize": 10000}
                else:
                    url = f"{self.base_url}/work/files"
                    body = {"fileCount": 1, "fileSizeBytes": 10000, "prefix": f"idle_{worker_id}"}
                delay = 1.0  # slow pace

            try:
                await asyncio.sleep(delay)
                start_time = time.perf_counter()
                try:
                    resp = await client.post(url, json=body, timeout=20.0)
                    await resp.aread()
                    status = resp.status_code
                except:
                    status = -1
                latency = (time.perf_counter() - start_time) * 1000

                await results_queue.put({
                    "timestamp": time.time(),
                    "worker_id": worker_id,
                    "phase": phase,
                    "latency_ms": latency,
                    "status_code": status,
                    "endpoint": "cpu" if "cpu" in url else "files"
                })
            except asyncio.CancelledError:
                break

    async def run_experiment(self, num_workers=8, output_file="experiment4_burst_workload.csv"):
        results_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        monitor_task = asyncio.create_task(self.monitor(results_queue, output_file))

        async with httpx.AsyncClient(http2=False, timeout=30.0) as client:
            tasks = [asyncio.create_task(self.worker(client, stop_event, results_queue, i)) for i in range(num_workers)]
            start = time.time()
            while time.time() - start < self.experiment_duration:
                await asyncio.sleep(10)
            stop_event.set()
            await asyncio.gather(*tasks, return_exceptions=True)
            monitor_task.cancel()

    async def monitor(self, results_queue, output_file):
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "worker_id", "phase", "latency_ms", "status_code", "endpoint"])
            while True:
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                    writer.writerow([
                        result["timestamp"],
                        result["worker_id"],
                        result["phase"],
                        f"{result['latency_ms']:.2f}",
                        result["status_code"],
                        result["endpoint"]
                    ])
                    f.flush()
                except asyncio.TimeoutError:
                    continue

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", default="experiment4_burst_workload.csv")
    parser.add_argument("--duration", type=int, default=3*60)
    args = parser.parse_args()

    gen = BurstWorkloadGenerator(args.url)
    gen.experiment_duration = args.duration
    await gen.run_experiment(args.workers, args.output)

if __name__ == "__main__":
    asyncio.run(main())
