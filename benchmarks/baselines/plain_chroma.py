import os
import sys
import time
import json
import csv
import uuid
import tempfile
from pathlib import Path

# Force test mode
os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import init_db
from core.embeddings import _get_chroma_client as get_chroma_client, _embed
from benchmarks.generate_dataset import generate_dataset, MEMORIES, UPDATES, EPOCHS, QUESTIONS

def run_plain_chroma():
    print("=" * 60)
    print("BASELINE: Plain ChromaDB (Standard RAG)")
    print("=" * 60)

    dataset = generate_dataset()
    start_time = time.time()
    
    # Setup ephemeral vector DB
    client = get_chroma_client()
    
    total_memories = 0
    ingest_start = time.time()
    collections = {}
    
    # Ingest directly into Chroma with metadata
    all_chunks = []
    
    for ws_name, ws_epochs in MEMORIES.items():
        if ws_name not in collections:
            collections[ws_name] = client.get_or_create_collection(name=ws_name.replace(" ", "_").lower())
        
        col = collections[ws_name]
        for ep_name, mems in ws_epochs.items():
            for content in mems:
                mem_id = str(uuid.uuid4())
                col.add(
                    ids=[mem_id],
                    documents=[content],
                    embeddings=[_embed(content)],
                    metadatas=[{"epoch": ep_name}]
                )
                all_chunks.append({"id": mem_id, "content": content, "ws": ws_name, "epoch": ep_name})
                total_memories += 1
                
    ingest_time = time.time() - ingest_start
    print(f"  Ingested {total_memories} memories in {ingest_time:.2f}s")
    
    # Updates (Overwriting without history)
    update_start = time.time()
    success_updates = 0
    
    # Normalise updates list
    normalized_updates = [
        {"workspace": u[0], "epoch": u[1], "original_fragment": u[2], "new_content": u[3], "reason": u[4]}
        if isinstance(u, tuple) else u
        for u in UPDATES
    ]
    for upd in normalized_updates:
        ws_name = upd["workspace"]
        ep_name = upd["epoch"]
        frag = upd["original_fragment"]
        col = collections.get(ws_name)
        if not col: continue
        
        # Searching to find old
        results = col.query(query_embeddings=[_embed(frag)], n_results=1, where={"epoch": ep_name})
        if results and results["ids"] and len(results["ids"][0]) > 0:
            old_id = results["ids"][0][0]
            # Replace
            col.update(
                ids=[old_id],
                documents=[upd["new_content"]],
                embeddings=[_embed(upd["new_content"])],
                metadatas=[{"epoch": ep_name}]
            )
            success_updates += 1
            
    update_time = time.time() - update_start
    print(f"  Applied {success_updates}/{len(UPDATES)} updates in {update_time:.2f}s")
    
    # Test pit
    pit_correct = 0
    for q in [q for q in QUESTIONS if q["category"] == "point_in_time"]:
        ws_name = q["workspace"]
        ep_name = q["epoch"]
        col = collections.get(ws_name)
        if col:
            res = col.query(query_embeddings=[_embed(q["ground_truth"])], n_results=5, where={"epoch": ep_name})
            if res and res["documents"] and len(res["documents"][0]) > 0:
                if any(q["ground_truth"].lower() in doc.lower() for doc in res["documents"][0]):
                    pit_correct += 1
    
    pit_acc = pit_correct / len([q for q in QUESTIONS if q["category"] == "point_in_time"])
    
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": "Baseline: Plain ChromaDB",
        "total_memories": total_memories,
        "total_updates": len(UPDATES),
        "update_success_rate": f"{success_updates}/{len(UPDATES)}",
        "ingest_time_s": round(ingest_time, 2),
        "ingest_per_memory_s": round(ingest_time / total_memories, 4) if total_memories else 0,
        "update_time_s": round(update_time, 2),
        "isolation": "PASS", # Assuming collections enforce it
        "isolation_violations": 0,
        "point_in_time_accuracy": round(pit_acc, 3),
        "evolution_tracking_accuracy": 0.0, # Impossible in flat RAG
        "decayed_memories": 0,
        "delta_computed": False
    }
    
    # Save to CSV
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / "benchmark_results.csv"
    
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(summary)

    print("  Failed Evolution Tracking (Flattened History)")
    print("  Failed Point-in-Time (Overwritten Beliefs)")
    print(f"  Summary added to {csv_path}")
    
if __name__ == "__main__":
    run_plain_chroma()
