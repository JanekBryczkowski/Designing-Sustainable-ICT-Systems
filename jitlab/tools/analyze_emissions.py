#!/usr/bin/env python3

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# --- Configuration ---
PUE = {
    'Germany': 1.10,
    'France': 1.15,
    'United States (Eastern)': 1.12,
    'Japan': 1.18,
}

EMISSION_FACTORS = { # kg CO2/kWh
    'Germany': 0.338,
    'France': 0.053,
    'United States (Eastern)': 0.386,
    'Japan': 0.463,
}


def create_plots(emissions_path, workload_df, emissions_out_path=None, energy_out_path=None):
    """
    Analyzes emissions from a single combined workload DataFrame.

    Args:
        emissions_path (str): Path to the CodeCarbon emissions CSV.
        workload_df (pd.DataFrame): A single, combined DataFrame containing
                                    workload data from all countries.
        emissions_out_path (str): Path to save the emissions plot.
        energy_out_path (str): Path to save the energy plot.
    """
    emissions_data = pd.read_csv(emissions_path)
    if emissions_data.empty or 'energy_consumed' not in emissions_data.columns:
        raise ValueError(f'{emissions_path} is empty or lacks "energy_consumed" column.')

    energy_total_kwh = emissions_data['energy_consumed'].iloc[0]
    print(f"Successfully loaded total measured energy from CodeCarbon: {energy_total_kwh:.8f} kWh")

    # --- Step 2: Compute workload share per country (Corrected Logic) ---

    # Determine which column to use for workload aggregation
    if 'requests_completed' in workload_df.columns:
        workload_col = 'requests_completed'
    else:
        workload_col = 'workload_factor'

    print(f"Aggregating workload using column: '{workload_col}'")

    # Group by country and sum the total workload
    workload_sums = workload_df.groupby('country')[workload_col].sum()

    # Get total workload for normalization
    total_workload = workload_sums.sum()

    # Create the DataFrame for calculating shares
    workload_shares_df = workload_sums.reset_index()
    workload_shares_df.columns = ['Country', 'WorkloadSum']

    if total_workload > 0:
        workload_shares_df['Share'] = workload_shares_df['WorkloadSum'] / total_workload
    else:
        print("Warning: Total workload is zero. Shares will be zero.")
        workload_shares_df['Share'] = 0.0

    # --- Step 3: Compute regional energy and emissions ---
    results = []
    # Iterate over the aggregated shares DataFrame
    for _, row in workload_shares_df.iterrows():
        country = row['Country']
        share = row['Share']

        # Apportion the total energy based on the share of work
        energy_kwh = energy_total_kwh * share

        # Apply PUE to get total datacenter energy
        pue = PUE.get(country, 1.0)  # Default to 1.0 if country not in dict
        emission_factor = EMISSION_FACTORS.get(country, 0.0)  # Default to 0.0
        energy_adj = energy_kwh * pue

        # Apply emission factor to get emissions (and convert kg to g)
        emissions = energy_adj * emission_factor * 1000  # gCO2e

        results.append({
            'Country': country,
            'Energy_Share_kWh': energy_kwh,
            'PUE_Adjusted_kWh': energy_adj,
            'Emissions_gCO2e': emissions,
            'Workload_Share_%': share * 100
        })

    results_df = pd.DataFrame(results)

    # --- Step 4: Print summary ---
    print('\nRegional Carbon Footprint Summary (PUE-adjusted):')
    print(results_df.round(6))
    print('\nTotal Energy (PUE-adjusted): {:.6f} kWh'.format(results_df['PUE_Adjusted_kWh'].sum()))
    print('Total Emissions: {:.6f} gCO2e'.format(results_df['Emissions_gCO2e'].sum()))

    # --- Step 5: Visualization ---
    try:
        plt.figure(figsize=(10, 5))
        plt.bar(results_df['Country'], results_df['Emissions_gCO2e'])
        plt.title(f'PUE-adjusted CO2 Emissions per Country (Total: {results_df["Emissions_gCO2e"].sum():.4f} gCO2e)')
        plt.ylabel('Emissions (g CO2e)')
        plt.xticks(rotation=15)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        if emissions_out_path:
            plt.savefig(emissions_out_path)
            print(f"Saved emissions plot to {emissions_out_path}")
        plt.close()

        plt.figure(figsize=(10, 5))
        plt.bar(results_df['Country'], results_df['PUE_Adjusted_kWh'] * 1000)  # Convert to Wh for readability
        plt.title(
            f'Energy Consumption per Country (PUE-adjusted, Total: {results_df["PUE_Adjusted_kWh"].sum() * 1000:.4f} Wh)')
        plt.ylabel('Energy (Wh)')
        plt.xticks(rotation=15)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        if energy_out_path:
            plt.savefig(energy_out_path)
            print(f"Saved energy plot to {energy_out_path}")
        plt.close()

    except Exception as e:
        print(f"Error during plotting: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Analyze and visualize regional carbon footprint from workload data")
    ap.add_argument("--emissions_csv", required=True, help="Path to the CodeCarbon emissions CSV file")
    ap.add_argument("--workload_csvs", required=True, help="Comma-separated list of country workload CSV files")
    ap.add_argument("--emissions_out", required=True, help="Path to the output emissions plot PNG file")
    ap.add_argument("--energy_out", required=True, help="Path to the output energy plot PNG file")
    args = ap.parse_args()

    csv_files = [f.strip() for f in args.workload_csvs.split(',')]
    dfs = []

    try:
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            if df.empty:
                print(f"Warning: Workload file {csv_file} is empty.", file=sys.stderr)
                continue
            dfs.append(df)

        if not dfs:
            raise ValueError("No valid workload data found in any CSV file.")

        workload_df = pd.concat(dfs, ignore_index=True)

    except FileNotFoundError as e:
        print(f"Error: Could not find file. {e}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError as e:
        print(f"Error: File is empty. {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    countries = workload_df['country'].unique()
    print(f"Found countries: {', '.join(countries)}")

    # Call create_plots with the single, combined DataFrame
    create_plots(args.emissions_csv, workload_df, args.emissions_out, args.energy_out)


if __name__ == "__main__":
    main()