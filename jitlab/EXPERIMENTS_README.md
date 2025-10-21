# JIT Optimization Experiments

Four experiments that test how different JVM configurations affect server performance and energy consumption under realistic workloads.

## Experiment 1: Daily Workload Simulation

### What it does
Simulates a 24-hour day compressed into 3 minutes:
- **Night (0:00-6:00)**: Very low traffic
- **Morning (6:00-12:00)**: Gradual ramp-up to peak at 10:30
- **Lunch (12:00-13:00)**: Low traffic
- **Afternoon (13:00-17:00)**: Steady work with slight peak at 14:30
- **Evening (17:00-24:00)**: Wind down to very low activity

### Endpoint usage
- **High load periods**: 80% CPU requests, 20% file requests
- **Low load periods**: 20% CPU requests, 80% file requests
- **8 workers** generating requests concurrently

## Experiment 2: Yearly Workload Simulation

### What it does
Simulates a full year compressed into 3 minutes with seasonal patterns:
- **Christmas/New Year**: High traffic (shopping, celebrations)
- **Easter**: Medium-high traffic
- **Summer holidays**: Low traffic (vacation period)
- **Black Friday/Cyber Monday**: Peak traffic
- **Regular business days**: Normal patterns

### Endpoint usage
- **Major events**: 90% CPU requests, 10% file requests
- **High load**: 70% CPU requests, 30% file requests
- **Medium load**: 40% CPU requests, 60% file requests
- **Low load**: 10% CPU requests, 90% file requests
- **6 workers** generating requests concurrently

## Experiment 3: Global Workload Comparison

### What it does
Simulates 24-hour workload patterns across different time zones compressed into 4 minutes:
- **Europe (NL/DE/FR)**: 09:00-17:00 with 1h lunch break
- **US (East/West Coast)**: 08:30-17:30 with short lunch breaks
- **Hong Kong/Asia**: 09:30-20:00+ with heavy evening workload

### Endpoint usage
- **High load**: 75% CPU requests, 25% file requests
- **Medium load**: 50% CPU requests, 50% file requests
- **Low load**: 15% CPU requests, 85% file requests
- **9 workers** (3 per timezone) generating requests concurrently

## Experiment 4: Burst Load Simulation

### What it does
Simulates sudden spikes in traffic followed by calm idle phases, compressed into 3 minutes:
- **Burst phase (30s)**: Extreme traffic (flash sales, DDoS-like loads)
- **Idle phase (15s)**: Almost no traffic
- Repeats burst–idle cycles until experiment ends

### Endpoint usage
- **Burst phase**: 95% CPU requests, 5% file requests
- **Idle phase**: 20% CPU requests, 80% file requests
- **8 workers** generating requests concurrently

## JVM Configurations

1. **Baseline**: Default JIT compilation
2. **Interpret-only**: No JIT, pure interpretation
3. **C2-only**: Skip C1, compile directly to C2
4. **C1-only**: Stop compilation at C1 level
5. **Lower threshold**: Compile methods sooner
6. **Single compiler**: Use only one compiler thread
7. **Fixed heap**: Fixed heap size to stabilize GC

## How to Run

### Prerequisites
- Java 23 (OpenJDK)
- Maven 3.9+
- Python 3.9+ with packages: `psutil`, `httpx`, `pandas`, `matplotlib`, `seaborn`

### Run all experiments
```bash
python3 tools/run_experiments.py
```

### Run specific experiments
```bash
# Run only experiment 1 with baseline and interpret-only
python3 tools/run_experiments.py --experiments experiment1 --configs baseline interpret_only

# Run all experiments with specific JVM configs
python3 tools/run_experiments.py --configs baseline c2_only c1_only
```

## Results Analysis

```bash
# Analyze all experiment results
python3 tools/analyze_results.py

# Analyze specific experiments
python3 tools/analyze_results.py --experiments experiment1 experiment2
```

### Generated Outputs
- **Comparison plots**: Bar charts comparing metrics across JVM configurations
- **Timeline plots**: Performance metrics over time
- **Summary report**: Markdown report with key findings
- **CSV data**: Raw experiment data for further analysis

## What Gets Measured

- **Performance**: Throughput (RPS), latency (P50, P95, P99), success rate
- **Energy**: Total energy consumption, energy per request, power usage
- **Resources**: CPU usage, memory consumption

## File Structure

```
jitlab/
├── tools/
│   ├── experiment1_daily_workload.py      # Daily workload simulation
│   ├── experiment2_yearly_workload.py     # Yearly workload simulation
│   ├── experiment3_global_workload.py     # Global workload comparison
│   ├── experiment4_burstload.py           # Burst workload simulation
│   ├── run_experiments.py                 # Experiment runner
│   ├── analyze_results.py                 # Results analysis
│   ├── monitor.py                         # System monitoring
│   └── plot.py                           # Basic plotting
├── runs/                                 # Experiment results directory
├── src/main/java/                        # Java source code
└── target/                               # Compiled JAR files
```
