#!/usr/bin/env python3

import argparse
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", default="country_workload_30min.csv")
    ap.add_argument("--countries", default="", help="Comma-separated list of countries to plot")
    ap.add_argument("--out", default="experiment3_country_profiles.png")
    args = ap.parse_args()

    df = pd.read_csv(args.profiles)
    if args.countries:
        wanted = [c.strip() for c in args.countries.split(",") if c.strip()]
        df = df[df["country"].isin(wanted)]

    x_labels = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0,30)]
    x = list(range(48))

    plt.figure()
    for _, row in df.iterrows():
        y = [row[col] for col in x_labels]
        plt.plot(x, y, label=row["country"])

    plt.xticks(ticks=list(range(0,48,2)), labels=[x_labels[i] for i in range(0,48,2)], rotation=45, ha='right')
    plt.xlabel("Local Time (30-min bins)")
    plt.ylabel("Workload factor (relative)")
    plt.title("Per-country workload profiles")
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
