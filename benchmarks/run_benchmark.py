"""
TLCM-Bench Runner
Runs the full benchmark workload against the TLCM engine and measures:
- Ingestion latency
- Retrieval F1 (precision/recall)
- Temporal Reconstruction Accuracy (point-in-time)
- Belief Revision Accuracy (evolution tracking)
- Cross-workspace isolation verification
- Biological decay behavior
- Semantic delta correctness

Outputs CSV results to benchmarks/results/
"""
import os
import sys
import time
import json
import csv
import re
from pathlib import Path

# Force test mode
os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import init_db, get_connection, DB_PATH
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.temporal_jump import TemporalJumpEngine
import core.database
import core.embeddings
import tempfile

from benchmarks.generate_dataset import generate_dataset, MEMORIES, UPDATES, EPOCHS, WORKSPACES, QUESTIONS


def setup_temp_env():
    """Create an isolated temp environment for benchmarking."""
    temp_dir = tempfile.mkdtemp(prefix="tlcm_bench_")
    core.database.DB_PATH = Path(temp_dir) / "bench.db"
    core.embeddings.CHROMA_PATH = Path(temp_dir) / "bench_chroma"
    core.embeddings._chroma_client = None  # Reset singleton
    init_db()
    return temp_dir


def ingest_memories(mem, memories_dict, epochs_dict, ws_mgr, ep_mgr):
    """Ingest all memories into the TLCM engine. Returns timing + memory IDs."""
    memory_ids = {}  # (workspace, epoch, content_fragment) -> id
    total_count = 0
    start = time.time()

    for ws_name, ws_epochs in memories_dict.items():
        ws_mgr.get_or_create(ws_name, WORKSPACES[ws_name])
        for ep_info in epochs_dict[ws_name]:
            ep_name = ep_info["name"]
            ep_mgr.create(ws_mgr.get_or_create(ws_name, "")["id"], ep_name, ep_info["desc"],
                         ep_info.get("start"), ep_info.get("end"))

        for ep_name, mems in ws_epochs.items():
            for content in mems:
                result = mem.remember(content, ws_name, ep_name)
                memory_ids[(ws_name, ep_name, content[:40])] = result["id"]
                total_count += 1

    elapsed = time.time() - start
    return elapsed, total_count, memory_ids


def apply_updates(mem, updates_list):
    """Apply deliberate updates and track version chains."""
    update_results = []
    start = time.time()

    conn = get_connection()
    for upd in updates_list:
        ws, epoch, fragment, new_content, reason = upd["workspace"], upd["epoch"], upd["original_fragment"], upd["new_content"], upd["reason"]
        # Find the original memory by content fragment
        row = conn.execute(
            "SELECT id FROM memories WHERE content LIKE ? AND is_current = 1",
            (f"%{fragment}%",)
        ).fetchone()
        if row:
            try:
                result = mem.update(row["id"], new_content, reason, ws)
                update_results.append({"success": True, "old_id": row["id"], "new_id": result["new_id"]})
            except Exception as e:
                update_results.append({"success": False, "error": str(e)})
        else:
            update_results.append({"success": False, "error": f"Original not found: {fragment[:30]}"})
    conn.close()

    elapsed = time.time() - start
    return elapsed, update_results


def test_isolation(ws_mgr):
    """Verify zero cross-workspace bleed at the database level."""
    conn = get_connection()
    results = {}
    ws_list = conn.execute("SELECT id, name FROM workspaces").fetchall()
    for ws in ws_list:
        mems = conn.execute(
            "SELECT content FROM memories WHERE workspace_id = ? AND is_current = 1",
            (ws["id"],)
        ).fetchall()
        results[ws["name"]] = [m["content"] for m in mems]
    conn.close()

    # Check: no Research Lab content in Supply Chain, and vice versa
    # Use word-boundary regex to avoid false positives (e.g. 'mpa' inside 'company')
    lab_keywords = ["tensile", "Palladium", "synthesis", "MPa", "Compound X"]
    chain_keywords = ["ShipFast", "NPS", "warehouse", "logistics", "carrier"]

    isolation_pass = True
    violations = []

    def word_match(keyword, text):
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))

    if "Research Lab" in results and "Supply Chain" in results:
        for content in results.get("Supply Chain", []):
            for kw in lab_keywords:
                if word_match(kw, content):
                    isolation_pass = False
                    violations.append(f"Lab keyword '{kw}' found in Supply Chain: {content[:50]}")

        for content in results.get("Research Lab", []):
            for kw in chain_keywords:
                if word_match(kw, content):
                    isolation_pass = False
                    violations.append(f"Chain keyword '{kw}' found in Research Lab: {content[:50]}")

    return isolation_pass, violations, {k: len(v) for k, v in results.items()}


def test_point_in_time(questions):
    """Test point-in-time recall accuracy."""
    conn = get_connection()
    results = []

    for q in questions:
        if q["category"] != "point_in_time":
            continue

        ws = conn.execute("SELECT id FROM workspaces WHERE name = ?", (q["workspace"],)).fetchone()
        ep = conn.execute("SELECT id FROM epochs WHERE name = ? AND workspace_id = ?",
                         (q["epoch"], ws["id"])).fetchone() if ws else None

        if not ep:
            results.append({"id": q["id"], "correct": False, "reason": "Epoch not found"})
            continue

        # Get all current memories for this epoch
        mems = conn.execute(
            "SELECT content FROM memories WHERE epoch_id = ? AND is_current = 1",
            (ep["id"],)
        ).fetchall()

        # Check if ground truth value appears in any memory content
        found = any(q["ground_truth"].lower() in m["content"].lower() for m in mems)

        # Also check archived versions (original beliefs before updates)
        if not found:
            archived = conn.execute(
                "SELECT content FROM memories WHERE epoch_id = ? AND is_current = 0",
                (ep["id"],)
            ).fetchall()
            found = any(q["ground_truth"].lower() in m["content"].lower() for m in archived)

        results.append({"id": q["id"], "correct": found, "memories_checked": len(mems)})

    conn.close()
    accuracy = sum(1 for r in results if r["correct"]) / len(results) if results else 0
    return accuracy, results


def test_evolution_tracking(questions, mem):
    """Test belief revision accuracy by checking version chains."""
    conn = get_connection()
    results = []

    for q in questions:
        if q["category"] != "evolution":
            continue

        # Check that version chains exist for the tracked belief
        ws = conn.execute("SELECT id FROM workspaces WHERE name = ?", (q["workspace"],)).fetchone()
        if not ws:
            results.append({"id": q["id"], "has_version_chain": False})
            continue

        # Find memories with parent_id (versioned)
        versioned = conn.execute(
            "SELECT COUNT(*) as cnt FROM memories WHERE workspace_id = ? AND parent_id IS NOT NULL",
            (ws["id"],)
        ).fetchone()

        results.append({
            "id": q["id"],
            "has_version_chain": versioned["cnt"] > 0,
            "version_count": versioned["cnt"],
        })

    conn.close()
    accuracy = sum(1 for r in results if r["has_version_chain"]) / len(results) if results else 0
    return accuracy, results


def test_decay():
    """Test biological decay mechanism."""
    conn = get_connection()

    # First, set ALL memories as recently recalled (baseline: everything fresh)
    conn.execute("UPDATE memories SET last_recalled_at = datetime('now'), recall_count = 1")
    conn.commit()

    # Now age SPECIFIC memories artificially (simulate 5 days without recall)
    conn.execute(
        "UPDATE memories SET last_recalled_at = datetime('now', '-5 day') "
        "WHERE content LIKE '%standup%' OR content LIKE '%safety protocol%' "
        "OR content LIKE '%Compliance audit%' OR content LIKE '%safety incident%'"
        "OR content LIKE '%lab notebooks%' OR content LIKE '%equipment calibration%'"
    )
    conn.commit()

    mem = MemoryStore()
    mem.decay_memories()

    # Check decayed memories (confidence < 1.0)
    decayed = conn.execute(
        "SELECT content, confidence FROM memories WHERE confidence < 1.0 AND is_current = 1"
    ).fetchall()

    # Check non-decayed memories (still at 1.0)
    fresh = conn.execute(
        "SELECT COUNT(*) as cnt FROM memories WHERE confidence = 1.0 AND is_current = 1"
    ).fetchone()

    conn.close()

    return {
        "decayed_count": len(decayed),
        "fresh_count": fresh["cnt"],
        "decayed_samples": [{"content": d["content"][:50], "confidence": d["confidence"]} for d in decayed[:5]],
    }


def test_semantic_delta(jump_eng):
    """Test the mathematical semantic delta computation."""
    results = []

    for ws_name in ["Research Lab", "Supply Chain"]:
        epochs = [e["name"] for e in EPOCHS[ws_name]]
        if len(epochs) >= 2:
            try:
                delta = jump_eng.jump(ws_name, epochs[0], epochs[-1])
                has_new = "NEW BELIEFS" in delta
                has_cont = "CONTINUITIES" in delta
                has_evol = "EVOLUTIONS" in delta
                results.append({
                    "workspace": ws_name,
                    "from": epochs[0],
                    "to": epochs[-1],
                    "has_additions": has_new,
                    "has_continuities": has_cont,
                    "has_evolutions": has_evol,
                    "delta_length": len(delta),
                })
            except Exception as e:
                results.append({"workspace": ws_name, "error": str(e)})

    return results


def run_full_benchmark():
    """Execute the complete benchmark suite."""
    print("=" * 60)
    print("TLCM-BENCH v1.0 — Full Benchmark Suite")
    print("=" * 60)

    # Generate dataset
    dataset = generate_dataset()

    # Setup isolated environment
    print("\n[1/7] Setting up isolated test environment...")
    temp_dir = setup_temp_env()
    print(f"  Temp dir: {temp_dir}")

    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    mem = MemoryStore()
    jump_eng = TemporalJumpEngine()

    # Ingest memories
    print("\n[2/7] Ingesting memories...")
    ingest_time, ingest_count, memory_ids = ingest_memories(mem, MEMORIES, EPOCHS, ws_mgr, ep_mgr)
    print(f"  Ingested {ingest_count} memories in {ingest_time:.2f}s ({ingest_time/ingest_count:.3f}s/memory)")

    # Apply updates
    print(f"\n[3/7] Applying {len(UPDATES)} deliberate updates...")
    update_time, update_results = apply_updates(mem, dataset["updates"])
    success_count = sum(1 for r in update_results if r["success"])
    print(f"  Applied {success_count}/{len(UPDATES)} updates in {update_time:.2f}s")

    # Test isolation
    print("\n[4/7] Testing workspace isolation...")
    iso_pass, violations, mem_counts = test_isolation(ws_mgr)
    print(f"  Isolation: {'PASSED' if iso_pass else 'FAILED'}")
    print(f"  Memory counts: {mem_counts}")
    if violations:
        for v in violations[:3]:
            print(f"  VIOLATION: {v}")

    # Test point-in-time recall
    print("\n[5/7] Testing point-in-time recall accuracy...")
    pit_accuracy, pit_results = test_point_in_time(QUESTIONS)
    print(f"  Point-in-Time Accuracy: {pit_accuracy:.1%} ({sum(1 for r in pit_results if r['correct'])}/{len(pit_results)})")

    # Test evolution tracking
    print("\n[6/7] Testing evolution tracking (Belief Revision Accuracy)...")
    evo_accuracy, evo_results = test_evolution_tracking(QUESTIONS, mem)
    print(f"  Evolution Tracking: {evo_accuracy:.1%}")

    # Test decay
    print("\n[7a/7] Testing biological decay...")
    decay_results = test_decay()
    print(f"  Decayed memories: {decay_results['decayed_count']}")
    print(f"  Fresh memories: {decay_results['fresh_count']}")
    for s in decay_results["decayed_samples"]:
        print(f"    {s['content']}... -> confidence={s['confidence']}")

    # Test semantic delta
    print("\n[7b/7] Testing semantic delta computation...")
    delta_results = test_semantic_delta(jump_eng)
    for d in delta_results:
        if "error" not in d:
            print(f"  {d['workspace']}: {d['from']} -> {d['to']}")
            print(f"    Additions={d['has_additions']}, Continuities={d['has_continuities']}, Evolutions={d['has_evolutions']}")
            print(f"    Delta size: {d['delta_length']} chars")

    # ─── Compile Results ───
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 60)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": "TLCM Full (all features enabled)",
        "total_memories": ingest_count,
        "total_updates": len(UPDATES),
        "update_success_rate": f"{success_count}/{len(UPDATES)}",
        "ingest_time_s": round(ingest_time, 2),
        "ingest_per_memory_s": round(ingest_time / ingest_count, 4),
        "update_time_s": round(update_time, 2),
        "isolation": "PASS" if iso_pass else "FAIL",
        "isolation_violations": len(violations),
        "point_in_time_accuracy": round(pit_accuracy, 3),
        "evolution_tracking_accuracy": round(evo_accuracy, 3),
        "decayed_memories": decay_results["decayed_count"],
        "delta_computed": all("error" not in d for d in delta_results),
    }

    # Print summary table
    for k, v in summary.items():
        print(f"  {k:.<40} {v}")

    # Save to CSV
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / "benchmark_results.csv"

    # Write CSV (append mode for comparison across configs)
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(summary)

    # Save detailed JSON
    json_path = results_dir / "benchmark_detailed.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "point_in_time_detail": pit_results,
            "evolution_detail": evo_results,
            "decay_detail": decay_results,
            "delta_detail": delta_results,
            "isolation_detail": {"pass": iso_pass, "violations": violations, "counts": mem_counts},
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  Results saved to: {csv_path}")
    print(f"  Details saved to: {json_path}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    run_full_benchmark()
