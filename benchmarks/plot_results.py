"""
TLCM-Bench Plot Generator
Reads benchmark and ablation CSV results and generates publication-ready charts.

Output: benchmarks/plots/ (PNG files)
Requires: matplotlib (pip install matplotlib)
"""
import csv
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend (no display needed)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    print("matplotlib not installed. Run: pip install matplotlib")
    sys.exit(1)

RESULTS_DIR = Path(__file__).parent / "results"
PLOTS_DIR = Path(__file__).parent / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(filename):
    path = RESULTS_DIR / filename
    if not path.exists():
        print(f"  [SKIP] {filename} not found")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_ablation_comparison():
    """Bar chart comparing ablation configurations."""
    data = load_csv("ablation_results.csv")
    if not data:
        return

    configs = [d["config"] for d in data]
    decay_counts = [int(d["decayed_memories"]) for d in data]
    delta_correct = [1 if d["delta_correct"] == "True" else 0 for d in data]
    drift_rates = [float(d["simulated_drift_rate"]) * 100 for d in data]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("TLCM-Bench Ablation Study", fontsize=14, fontweight="bold")

    colors = ["#2ecc71", "#e74c3c", "#3498db", "#f39c12"]

    # Decay effect
    axes[0].bar(configs, decay_counts, color=colors)
    axes[0].set_title("Biological Decay Effect")
    axes[0].set_ylabel("Decayed Memories")
    axes[0].tick_params(axis="x", rotation=30)

    # Delta correctness
    axes[1].bar(configs, delta_correct, color=colors)
    axes[1].set_title("Semantic Delta Correctness")
    axes[1].set_ylabel("Correct (1=yes, 0=no)")
    axes[1].set_ylim(0, 1.2)
    axes[1].tick_params(axis="x", rotation=30)

    # Drift rate
    axes[2].bar(configs, drift_rates, color=colors)
    axes[2].set_title("Simulated Drift Rate")
    axes[2].set_ylabel("Ghost Memory Rate (%)")
    axes[2].tick_params(axis="x", rotation=30)

    plt.tight_layout()
    out_path = PLOTS_DIR / "ablation_comparison.png"
    plt.savefig(out_path, dpi=150)
    print(f"  Saved: {out_path}")
    plt.close()


def plot_benchmark_summary():
    """Summary metrics from the main benchmark."""
    data = load_csv("benchmark_results.csv")
    if not data:
        return

    # Use the last row (most recent run)
    d = data[-1]

    metrics = {
        "Point-in-Time\nAccuracy": float(d.get("point_in_time_accuracy", 0)),
        "Evolution\nTracking": float(d.get("evolution_tracking_accuracy", 0)),
        "Isolation\nTest": 1.0 if d.get("isolation") == "PASS" else 0.0,
        "Delta\nComputed": 1.0 if d.get("delta_computed") in ["True", True] else 0.0,
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(metrics.keys(), metrics.values(),
                  color=["#2ecc71" if v >= 0.8 else "#e74c3c" for v in metrics.values()],
                  edgecolor="white", linewidth=2)

    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score (0.0 - 1.0)")
    ax.set_title("TLCM-Bench: Core Metric Scores", fontsize=14, fontweight="bold")
    ax.axhline(y=0.8, color="gray", linestyle="--", alpha=0.5, label="Threshold (0.8)")
    ax.legend()

    # Add value labels on bars
    for bar, val in zip(bars, metrics.values()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{val:.1%}", ha="center", va="bottom", fontweight="bold")

    plt.tight_layout()
    out_path = PLOTS_DIR / "benchmark_summary.png"
    plt.savefig(out_path, dpi=150)
    print(f"  Saved: {out_path}")
    plt.close()


def plot_latency_breakdown():
    """Latency breakdown from benchmark."""
    data = load_csv("benchmark_results.csv")
    if not data:
        return

    d = data[-1]
    ingest = float(d.get("ingest_time_s", 0))
    update = float(d.get("update_time_s", 0))
    per_mem = float(d.get("ingest_per_memory_s", 0))

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle("TLCM-Bench: Latency Analysis", fontsize=14, fontweight="bold")

    # Total times
    axes[0].barh(["Ingestion", "Updates"], [ingest, update],
                 color=["#3498db", "#2ecc71"])
    axes[0].set_xlabel("Time (seconds)")
    axes[0].set_title("Total Operation Time")

    # Per-memory
    axes[1].bar(["Per Memory\n(Ingest)"], [per_mem * 1000],
                color=["#3498db"], width=0.4)
    axes[1].set_ylabel("Milliseconds")
    axes[1].set_title("Per-Operation Latency")

    plt.tight_layout()
    out_path = PLOTS_DIR / "latency_breakdown.png"
    plt.savefig(out_path, dpi=150)
    print(f"  Saved: {out_path}")
    plt.close()


def generate_all_plots():
    """Generate all benchmark plots."""
    print("=" * 60)
    print("TLCM-BENCH: Generating Plots")
    print("=" * 60)

    plot_benchmark_summary()
    plot_ablation_comparison()
    plot_latency_breakdown()

    print(f"\nAll plots saved to: {PLOTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    generate_all_plots()
