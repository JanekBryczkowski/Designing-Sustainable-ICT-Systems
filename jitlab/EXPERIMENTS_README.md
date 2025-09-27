# JIT Optimization Experiments

This document describes the three experiments designed to study JIT compiler optimization effects on server performance and energy consumption.

## Overview

The experiments simulate realistic server workloads to understand how different JVM configurations affect:
- **Performance**: Throughput, latency, response times
- **Energy Consumption**: Power usage, energy per request
- **Resource Utilization**: CPU, memory usage patterns

## Experiment 1: Daily Workload Simulation

### Description
Simulates a complete 24-hour day with realistic traffic patterns:
- **0:00-6:00**: Very low traffic (night)
- **6:00-9:00**: Gradual ramp-up (early morning)
- **9:00-12:00**: High traffic (morning rush, peak at 10:30)
- **12:00-13:00**: Lunch break (low traffic)
- **13:00-17:00**: Steady traffic (afternoon work, slight peak at 14:30)
- **17:00-19:00**: Wind down (decreasing traffic)
- **19:00-22:00**: Evening low activity
- **22:00-24:00**: Very low traffic (late night)

### Workload Characteristics
- **Duration**: 3 minutes (compressed 24-hour day)
- **Workers**: 8 concurrent workers
- **Load Pattern**: Dynamic based on time of day
- **Endpoints**: CPU-intensive work during high load, file operations during low load

### Justification
This experiment represents the most common server workload pattern - a complete 24-hour day. It helps understand how JIT optimizations perform under varying load conditions that servers experience throughout the day, including night-time low activity periods.

## Experiment 2: Yearly Workload Simulation

### Description
Simulates a full year with seasonal patterns and major events:
- **Christmas/New Year**: High traffic (shopping, celebrations)
- **Easter**: Medium-high traffic
- **Summer holidays**: Low traffic (vacation period)
- **Black Friday/Cyber Monday**: Peak traffic
- **Regular business days**: Normal patterns

### Workload Characteristics
- **Duration**: 3 minutes (compressed year)
- **Workers**: 6 concurrent workers
- **Load Pattern**: Seasonal variations with event spikes
- **Endpoints**: CPU-intensive during major events, file operations during normal periods

### Justification
This experiment tests JIT performance under extreme load variations that occur throughout the year. It's particularly relevant for e-commerce and service platforms that experience significant seasonal traffic changes.

## Experiment 3: Global Workload Comparison

### Description
Simulates workload patterns across different time zones:
- **Europe (NL/DE/FR)**: 09:00-17:00 with 1h lunch break
- **US (East/West Coast)**: 08:30-17:30 with short lunch breaks
- **Hong Kong/Asia**: 09:30-20:00+ with heavy evening workload

### Workload Characteristics
- **Duration**: 4 minutes (compressed 24-hour cycle)
- **Workers**: 9 concurrent workers (3 per timezone)
- **Load Pattern**: Timezone-specific 24-hour working patterns
- **Endpoints**: CPU-intensive during peak hours, file operations during off-peak

### Justification
This experiment represents global server deployments that serve users across multiple time zones. It helps understand how JIT optimizations perform under continuous, geographically distributed load across complete 24-hour cycles, showing how different timezones create overlapping and complementary workload patterns.

## JVM Configurations Tested

1. **Baseline (Default JIT)**: Standard JVM with default JIT compilation
2. **Interpret-only (No JIT)**: Pure interpretation, no compilation
3. **C2-only (No Tiered Compilation)**: Skip C1, compile directly to C2
4. **C1-only (No C2 JIT)**: Stop compilation at C1 level
5. **Lower Compile Threshold**: Compile methods sooner (threshold=1000)
6. **Single Compiler Thread**: Use only one compiler thread
7. **Fixed Heap Size**: Fixed heap size to stabilize GC effects

## Running the Experiments

### Prerequisites
- Java 21 (OpenJDK)
- Maven 3.9+
- Python 3.9+ with packages: `psutil`, `httpx`, `pandas`, `matplotlib`, `seaborn`

### Quick Start
```bash
# Run all experiments with all JVM configurations
python3 tools/run_experiments.py

# Run specific experiments
python3 tools/run_experiments.py --experiments experiment1 experiment2

# Run with specific JVM configurations
python3 tools/run_experiments.py --configs baseline interpret_only c2_only
```

### Manual Execution
```bash
# 1. Build the project
mvn clean package -DskipTests

# 2. Start server with specific JVM configuration
java -jar target/jitlab-0.0.1-SNAPSHOT.jar

# 3. Start monitoring (in another terminal)
PID=$(pgrep -f 'jitlab-0.0.1-SNAPSHOT.jar' | head -n1)
python3 tools/monitor.py --pid $PID --interval 1 --duration 180 --out runs/monitor_experiment1.csv

# 4. Run experiment (in another terminal)
python3 tools/experiment1_daily_workload.py --workers 8 --duration 180 --output runs/experiment1_workload.csv
```

## Analyzing Results

### Automatic Analysis
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

## Expected Outcomes

### Performance Metrics
- **Throughput (RPS)**: Requests per second
- **Latency**: P50, P95, P99 response times
- **Success Rate**: Percentage of successful requests

### Energy Metrics
- **Total Energy**: Total energy consumption during experiment
- **Energy per Request**: Energy efficiency metric
- **Power Consumption**: Average and peak power usage

### Resource Metrics
- **CPU Usage**: Average and peak CPU utilization
- **Memory Usage**: Average and peak memory consumption

## Key Research Questions

1. **How does JIT compilation affect energy consumption under different workload patterns?**
2. **Which JVM configuration provides the best balance of performance and energy efficiency?**
3. **How do JIT optimizations perform under varying load conditions (daily, seasonal, global)?**
4. **What is the impact of compilation thresholds on warmup time and overall performance?**
5. **How do different compilation strategies (C1-only, C2-only, tiered) compare across workloads?**

## Troubleshooting

### Common Issues
1. **Energy monitoring**: If energy readings are 0, run monitor script with `sudo`
2. **Server startup**: Ensure port 8080 is available
3. **Python dependencies**: Install required packages with `pip install -r requirements.txt`
4. **Memory issues**: Adjust JVM heap size for long-running experiments

### Performance Tips
- Run experiments on a dedicated machine to avoid interference
- Ensure consistent system load during experiments
- Use SSD storage for better I/O performance
- Monitor system temperature to avoid thermal throttling

## File Structure

```
jitlab/
├── tools/
│   ├── experiment1_daily_workload.py      # Daily workload simulation
│   ├── experiment2_yearly_workload.py     # Yearly workload simulation
│   ├── experiment3_global_workload.py     # Global workload comparison
│   ├── run_experiments.py                 # Experiment runner
│   ├── analyze_results.py                 # Results analysis
│   ├── monitor.py                         # System monitoring
│   └── plot.py                           # Basic plotting
├── runs/                                 # Experiment results directory
├── src/main/java/                        # Java source code
└── target/                               # Compiled JAR files
```

## Contributing

When modifying experiments:
1. Update workload patterns to reflect realistic scenarios
2. Ensure experiments are reproducible
3. Document any changes to JVM configurations
4. Update analysis scripts if new metrics are added
5. Test with shorter durations before running full experiments
