# JIT Optimization Experiment Results Summary
==================================================

## Daily Workload Simulation

                  Configuration  Total Requests Success Rate Avg RPS P95 Latency (ms) Total Energy (J) Energy/Request (J) Avg CPU % Avg Memory (MB)
         Baseline (Default JIT)              67      100.00%    0.41           129.78             0.00             0.0000       1.0           121.2
        Interpret-only (No JIT)              65      100.00%    0.42           934.30             0.00             0.0000       2.1            84.7
C2-only (No Tiered Compilation)              67      100.00%    0.43           143.14             0.00             0.0000       1.0            98.9
            C1-only (No C2 JIT)              65      100.00%    0.40           130.74             0.00             0.0000       0.7            92.1
        Lower Compile Threshold               8      100.00% 2665.80           153.02             0.00             0.0000       2.5           173.6
                Fixed Heap Size              64      100.00%    0.41           210.28             0.00             0.0000       0.4           174.4

### Key Findings:

- **Highest Throughput**: Lower Compile Threshold (2665.80 RPS)
- **Lowest Latency**: Baseline (Default JIT) (129.78 ms)
- **Most Energy Efficient**: Baseline (Default JIT) (0.0000 J/request)

---

## Yearly Workload Simulation

                  Configuration  Total Requests Success Rate Avg RPS P95 Latency (ms) Total Energy (J) Energy/Request (J) Avg CPU % Avg Memory (MB)
         Baseline (Default JIT)              54      100.00%    0.33            14.23             0.00             0.0000       0.9           143.2
        Interpret-only (No JIT)              52      100.00%    0.32            25.27             0.00             0.0000       1.9           146.5
C2-only (No Tiered Compilation)              52      100.00%    0.32            20.47             0.00             0.0000       0.8           153.2
            C1-only (No C2 JIT)              52      100.00%    0.33            14.77             0.00             0.0000       0.6           141.5
        Lower Compile Threshold              49      100.00%    0.30            17.78             0.00             0.0000       0.9           178.1
                Fixed Heap Size              50      100.00%    0.31            14.56             0.00             0.0000       0.9           257.1

### Key Findings:

- **Highest Throughput**: Baseline (Default JIT) (0.33 RPS)
- **Lowest Latency**: Baseline (Default JIT) (14.23 ms)
- **Most Energy Efficient**: Baseline (Default JIT) (0.0000 J/request)

---

## Global Workload Comparison

                  Configuration  Total Requests Success Rate Avg RPS P95 Latency (ms) Total Energy (J) Energy/Request (J) Avg CPU % Avg Memory (MB)
         Baseline (Default JIT)             975      100.00%    4.10            75.64             0.00             0.0000      17.9           196.5
        Interpret-only (No JIT)             833      100.00%    3.50          1158.81             0.00             0.0000     169.7           145.9
C2-only (No Tiered Compilation)             972      100.00%    0.30            76.31             0.00             0.0000      16.5           146.9
            C1-only (No C2 JIT)             112      100.00%    0.03           504.44             0.00             0.0000       0.2           142.6
        Lower Compile Threshold             149      100.00%    0.05           424.52             0.00             0.0000      48.5           174.4
                Fixed Heap Size             284       99.65%    0.45           849.50             0.00             0.0000      85.2           275.4

### Key Findings:

- **Highest Throughput**: Baseline (Default JIT) (4.10 RPS)
- **Lowest Latency**: Baseline (Default JIT) (75.64 ms)
- **Most Energy Efficient**: Baseline (Default JIT) (0.0000 J/request)

---
