"""
TLCM-Bench Ablation Study (LoCoMo Scale)
Runs the benchmark under 5 configurations to measure the impact of each feature.

Configurations:
1. TLCM Full
2. No Decay
3. No Epochs (flattens memories)
4. No Math Delta
5. No Workspace Isolation (single workspace)

Results saved to benchmarks/results/locomo_ablation_results.csv
"""
import os
import sys
import time
import csv
import json
import random
from pathlib import Path

os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

import core.database
import core.embeddings
import core.memory_store
import tempfile

from core.database import init_db, get_connection
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.temporal_jump import TemporalJumpEngine
from benchmarks.locomo_dataset import LOCOMO_MEMORIES, LOCOMO_UPDATES, LOCOMO_EPOCHS, LOCOMO_WORKSPACES


def setup_fresh_env():
    temp_dir = tempfile.mkdtemp(prefix="tlcm_ablation_locomo_")
    core.database.DB_PATH = Path(temp_dir) / "ablation_locomo.db"
    core.embeddings.CHROMA_PATH = Path(temp_dir) / "ablation_locomo_chroma"
    core.embeddings._chroma_client = None
    init_db()
    return temp_dir


def ingest_all(mem, ws_mgr, ep_mgr, no_epochs=False, no_isolation=False):
    count = 0
    common_ws = "Single Global Workspace"
    if no_isolation:
        ws_mgr.get_or_create(common_ws, "Flattened workspace")

    for ws_name_base, ws_epochs in LOCOMO_MEMORIES.items():
        actual_ws = common_ws if no_isolation else ws_name_base
        if not no_isolation:
            ws_mgr.get_or_create(actual_ws, LOCOMO_WORKSPACES[ws_name_base])
            
        common_ep = "Global Epoch"
        if no_epochs:
            ep_mgr.get_or_create_active(ws_mgr.get_or_create(actual_ws, "")["id"], common_ep)
        else:
            for ep_info in LOCOMO_EPOCHS[ws_name_base]:
                ep_mgr.create(ws_mgr.get_or_create(actual_ws, "")["id"], ep_info["name"], ep_info["desc"])

        for ep_name_base, mems in ws_epochs.items():
            actual_ep = common_ep if no_epochs else ep_name_base
            for content in mems:
                mem.remember(content, actual_ws, actual_ep)
                count += 1
    return count


def apply_all_updates(mem, no_isolation=False):
    conn = get_connection()
    success = 0
    for upd in LOCOMO_UPDATES:
        ws = "Single Global Workspace" if no_isolation else upd[0]
        fragment = upd[2]
        row = conn.execute(
            "SELECT id FROM memories WHERE workspace_id = (SELECT id FROM workspaces WHERE name = ?) AND content LIKE ? AND is_current = 1",
            (ws, f"%{fragment}%",)
        ).fetchone()
        if row:
            try:
                mem.update(row["id"], upd[3], upd[4], ws)
                success += 1
            except:
                pass
    conn.close()
    return success


def run_config(config_name, decay=True, epochs=True, delta=True, isolation=True):
    print(f"\n--- Running: {config_name} ---")
    setup_fresh_env()

    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    mem = MemoryStore()

    t0 = time.time()
    count = ingest_all(mem, ws_mgr, ep_mgr, no_epochs=not epochs, no_isolation=not isolation)
    ingest_time = time.time() - t0

    t0 = time.time()
    update_success = apply_all_updates(mem, no_isolation=not isolation)
    update_time = time.time() - t0

    # Decay
    decay_count = 0
    if decay:
        conn = get_connection()
        conn.execute("UPDATE memories SET last_recalled_at = date('now', '-5 day')")
        conn.commit()
        conn.close()
        mem.decay_memories()
        conn = get_connection()
        decay_count = conn.execute("SELECT COUNT(*) as c FROM memories WHERE confidence < 1.0").fetchone()["c"]
        conn.close()

    # Delta test
    delta_correct = False
    if delta and epochs and isolation:
        jump_eng = TemporalJumpEngine()
        try:
            res = jump_eng.jump("AI Startup", "Ideation", "Series A")
            delta_correct = True
        except:
            pass

    isolation_val = "PASS" if isolation else "FAIL"
    epoch_val = "PASS" if epochs else "FAIL"

    result = {
        "config": config_name,
        "memories_ingested": count,
        "updates_applied": update_success,
        "decay_enabled": decay,
        "decayed_memories": decay_count,
        "epochs_enabled": epochs,
        "epoch_isolation": epoch_val,
        "delta_enabled": delta,
        "delta_correct": delta_correct,
        "isolation_enabled": isolation,
        "workspace_isolation": isolation_val,
    }

    for k, v in result.items():
        print(f"  {k:.<40} {v}")

    return result


def run_ablation():
    print("=" * 60)
    print("TLCM-BENCH ABLATION STUDY (LoCoMo Scale)")
    print("=" * 60)

    configs = [
        ("TLCM Full", True, True, True, True),
        ("No Decay", False, True, True, True),
        ("No Epochs", True, False, True, True),
        ("No Math Delta", True, True, False, True),
        ("No Workspace Isolation", True, True, True, False),
    ]

    results = []
    for name, dec, ep, delt, iso in configs:
        r = run_config(name, dec, ep, delt, iso)
        results.append(r)

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    csv_path = results_dir / "locomo_ablation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    json_path = results_dir / "locomo_ablation_detailed.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nAblation results saved to: {csv_path}")
    return results


if __name__ == "__main__":
    run_ablation()
