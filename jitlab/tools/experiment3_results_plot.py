#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser(description="Plot Experiment 3 results with one line per country")
    ap.add_argument("--workload_csv", required=True, help="CSV output from experiment3_global_workload.py (single file) or comma-separated list of country files")
    ap.add_argument("--out", default="experiment3_results.png")
    args = ap.parse_args()

    # Check if multiple files are provided (comma-separated)
    if ',' in args.workload_csv:
        # Multiple files - one per country
        csv_files = [f.strip() for f in args.workload_csv.split(',')]
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)
    else:
        # Single file
        df = pd.read_csv(args.workload_csv)
    # Expected columns: timestamp, worker_id, country, workload_factor, latency_ms, status_code, endpoint, hour_local, minute_local
    if "country" not in df.columns or "workload_factor" not in df.columns:
        raise SystemExit("workload CSV missing required columns")

    # Compute 30-min bin index from local hour/min
    if "hour_local" in df.columns and "minute_local" in df.columns:
        bins = df["hour_local"].astype(int) * 2 + (df["minute_local"].astype(int) >= 30).astype(int)
        df["bin"] = bins.clip(lower=0, upper=47)
    else:
        # fallback: just use timestamp buckets (not ideal); create 48 buckets based on order
        n = len(df)
        idx = (np.arange(n) * 48.0 / max(1, n)).astype(int).clip(0, 47)
        df["bin"] = idx

    # Aggregate: average workload per bin per country
    agg = df.groupby(["country", "bin"])['workload_factor'].mean().reset_index()

    # Prepare x labels
    x_ticks = list(range(0, 48, 2))
    x_labels = [f"{h:02d}:00" for h in range(0, 24)]

    plt.figure()
    for country, g in agg.groupby("country"):
        y = np.full(48, np.nan)
        y[g["bin"].to_numpy()] = g["workload_factor"].to_numpy()
        # Simple forward fill for nicer line continuity
        for i in range(48):
            if np.isnan(y[i]):
                y[i] = y[i-1] if i > 0 else np.nan
        plt.plot(range(48), y, label=country)

    plt.xticks(ticks=x_ticks, labels=x_labels, rotation=45, ha='right')
    plt.xlabel("Local Time (30-min bins)")
    plt.ylabel("Workload factor (relative)")
    plt.title("Experiment 3 — Per-country workload over local time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
