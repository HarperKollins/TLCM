import subprocess
import sys

commands = [
    "python -X utf8 benchmarks/run_locomo_bench.py",
    "python -X utf8 benchmarks/baselines/simulated_mem0.py",
    "python -X utf8 benchmarks/baselines/simulated_zep.py",
    "python -X utf8 benchmarks/baselines/simulated_letta.py",
    "python -X utf8 benchmarks/run_ablation.py",
    "python -X utf8 benchmarks/plot_results.py"
]

for cmd in commands:
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)
print("ALL DONE")
