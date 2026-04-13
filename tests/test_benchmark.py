"""
TLCM Benchmark Suite
Tests workspace isolation, temporal jump semantic delta, and biological decay.
Ollama is mocked in conftest.py — tests run fast without GPU.
"""
import time
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.temporal_jump import TemporalJumpEngine
from core.database import get_connection


def test_workspace_isolation_and_scale():
    """
    Creates multiple workspaces and verifies zero cross-workspace bleed.
    Also validates latency for ingestion.
    """
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    mem = MemoryStore()

    wsA = ws_mgr.get_or_create("Isolate A", "A")
    wsB = ws_mgr.get_or_create("Isolate B", "B")

    ep_mgr.get_or_create_active(wsA["id"], "Epoch A")
    ep_mgr.get_or_create_active(wsB["id"], "Epoch B")

    # Generate 50 synthetic memories per workspace
    print("\n[Benchmark] Ingesting 100 synthetic memories...")
    start_time = time.time()

    for i in range(50):
        mem.remember(f"Subject Alpha property {i} is validated.", "Isolate A", "Epoch A")
        mem.remember(f"Subject Beta dimension {i} is theoretical.", "Isolate B", "Epoch B")

    ingest_time = time.time() - start_time
    print(f"[Benchmark] Ingestion time: {ingest_time:.2f}s ({ingest_time/100:.3f}s per memory)")

    # Test Isolation via direct DB query (deterministic, no vector similarity needed)
    conn = get_connection()
    alpha_mems = conn.execute(
        "SELECT content FROM memories WHERE workspace_id = ? AND is_current = 1",
        (wsA["id"],)
    ).fetchall()
    beta_mems = conn.execute(
        "SELECT content FROM memories WHERE workspace_id = ? AND is_current = 1",
        (wsB["id"],)
    ).fetchall()
    conn.close()

    print(f"[Benchmark] Alpha workspace: {len(alpha_mems)} memories")
    print(f"[Benchmark] Beta workspace:  {len(beta_mems)} memories")

    assert len(alpha_mems) == 50, f"Expected 50 Alpha memories, got {len(alpha_mems)}"
    assert len(beta_mems) == 50, f"Expected 50 Beta memories, got {len(beta_mems)}"

    for m in alpha_mems:
        assert "Alpha" in m["content"], f"BLEED: Non-Alpha data in Alpha workspace: {m['content']}"
    for m in beta_mems:
        assert "Beta" in m["content"], f"BLEED: Non-Beta data in Beta workspace: {m['content']}"

    print("[Benchmark] ISOLATION: PASSED - Zero cross-workspace bleed across 100 memories.")


def test_temporal_jump_semantic_delta():
    """
    Verifies the mathematical semantic delta logic in the temporal jump engine.
    The test sets up two epochs with overlapping and unique memories, then
    checks that the raw prompt (returned in test mode) contains the correct
    categorizations.
    """
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    mem = MemoryStore()
    jump_eng = TemporalJumpEngine()

    ws_id = ws_mgr.get_or_create("Jump Test", "...")[  "id"]
    ep_1 = ep_mgr.create(ws_id, "J-Epoch 1", "...")

    # Insert initial beliefs into Epoch 1
    m1 = mem.remember("Gravity is 9.8.", "Jump Test", "J-Epoch 1")
    m2 = mem.remember("The sky is blue.", "Jump Test", "J-Epoch 1")

    # Advance epoch
    ep_2 = ep_mgr.create(ws_id, "J-Epoch 2", "...")

    # Add new belief in epoch 2 (this is an ADDITION — not in epoch 1)
    m3 = mem.remember("The ocean is deep.", "Jump Test", "J-Epoch 2")

    # Also add a duplicate-ish continuity memory in epoch 2
    m4 = mem.remember("The sky is blue.", "Jump Test", "J-Epoch 2")

    start_time = time.time()
    result = jump_eng.jump("Jump Test", "J-Epoch 1", "J-Epoch 2")
    jump_time = time.time() - start_time

    print(f"\n[Benchmark] Temporal Jump latency: {jump_time:.2f}s")
    print(f"[Benchmark] Jump result (raw prompt):\n{result}")

    # In test mode, result IS the raw prompt containing the mathematical delta
    assert "NEW BELIEFS" in result, "Jump result missing NEW BELIEFS section"
    assert "ocean" in result.lower(), "Jump result missing the new ocean belief"

    print("[Benchmark] TEMPORAL JUMP: PASSED - Mathematical delta correctly computed.")


def test_biological_decay():
    """
    Verifies the decay algorithm successfully decrements confidence scores.
    """
    ws_mgr = WorkspaceManager()
    mem = MemoryStore()

    ws_mgr.get_or_create("Decay Test", "...")
    mem.remember("Decay me.", "Decay Test")

    conn = get_connection()
    # Artificially age the memory back 5 days
    conn.execute(
        "UPDATE memories SET created_at = date('now', '-5 day'), "
        "last_recalled_at = date('now', '-5 day') "
        "WHERE content = 'Decay me.'"
    )
    conn.commit()
    conn.close()

    mem.decay_memories()

    conn = get_connection()
    aged_m = conn.execute(
        "SELECT confidence FROM memories WHERE content = 'Decay me.'"
    ).fetchone()
    conn.close()

    print(f"\n[Benchmark] Decayed confidence: {aged_m['confidence']}")
    assert aged_m["confidence"] < 1.0, f"Decay FAILED: confidence is still {aged_m['confidence']}"
    assert aged_m["confidence"] >= 0.1, f"Decay over-aggressive: confidence dropped to {aged_m['confidence']}"

    print("[Benchmark] BIOLOGICAL DECAY: PASSED - Confidence correctly reduced.")

def test_corrective_surgery():
    """
    Verifies that inserting a memory with reconsolidation_flag 'contradicts_core'
    surgically archives the conflicting past memory via graph versioning.
    """
    ws_mgr = WorkspaceManager()
    mem = MemoryStore()

    ws_mgr.get_or_create("Surgery Test", "...")
    
    m1 = mem.commit_memory(
        content="The Earth is flat.",
        workspace_name="Surgery Test",
        emotional_valence=8,
        urgency_score=5,
        semantic_impact=10,
        reconsolidation_flag="append"
    )

    conn = get_connection()
    c1_initial = conn.execute("SELECT confidence, is_current FROM memories WHERE id = ?", (m1["id"],)).fetchone()
    conn.close()
    
    assert c1_initial["confidence"] == 1.0, "Initial confidence should be 1.0"
    assert c1_initial["is_current"] == 1, "Initial memory should be current"

    # Insert a contradicting memory. We use the same text in test mode to hit distance 0 (relevance 1.0)
    m2 = mem.commit_memory(
        content="The Earth is flat.",
        workspace_name="Surgery Test",
        emotional_valence=9,
        urgency_score=10,
        semantic_impact=10,
        reconsolidation_flag="contradicts_core"
    )
    
    conn = get_connection()
    c1_final = conn.execute("SELECT is_current, archived_at FROM memories WHERE id = ?", (m1["id"],)).fetchone()
    c2_final = conn.execute("SELECT parent_id, is_current FROM memories WHERE id = ?", (m2["new_id"],)).fetchone()
    conn.close()

    assert c1_final["is_current"] == 0, "Surgical weakening failed. Expected old memory to be explicitly archived."
    assert c1_final["archived_at"] is not None, "Expected old memory to have an archived_at timestamp."
    assert c2_final["parent_id"] == m1["id"], "Expected new memory to explicitly branch from the old baseline."
    assert c2_final["is_current"] == 1, "Expected new memory to become the current active version."

    print("[Benchmark] TRUE CORRECTIVE SURGERY: PASSED - Conflicting memory surgically branched and archived.")


def test_local_fallback_strengthen():
    """
    Verifies that redundant information skips explicit insertions and bolsters existing facts gracefully.
    """
    ws_mgr = WorkspaceManager()
    mem = MemoryStore()

    ws_mgr.get_or_create("Fallback Test", "...")
    
    m1 = mem.commit_memory(
        content="It rains in April.",
        workspace_name="Fallback Test",
        reconsolidation_flag="append"
    )

    conn = get_connection()
    baseline = conn.execute("SELECT confidence, recall_count FROM memories WHERE id = ?", (m1["id"],)).fetchone()
    conn.close()

    # Hit the same fact using 'strengthen' fallback directly (relevance will be 1.0 via mock)
    m2 = mem.commit_memory(
        content="It rains in April.", # identical text triggers 1.0 relevance in test_mode hashing
        workspace_name="Fallback Test",
        reconsolidation_flag="strengthen"
    )
    
    conn = get_connection()
    final = conn.execute("SELECT confidence, recall_count FROM memories WHERE id = ?", (m1["id"],)).fetchone()
    new_mem = conn.execute("SELECT count(*) as c FROM memories WHERE workspace_id = (SELECT id FROM workspaces WHERE name='Fallback Test')").fetchone()
    conn.close()

    assert m2["id"] == m1["id"], "Expected fallback to return the identical memory ID, skipping insertion."
    assert m2.get("status") == "strengthened", "Expected returned status to be 'strengthened'."
    assert final["recall_count"] > baseline["recall_count"], "Expected the old memories recall count to increase."
    assert new_mem["c"] == 1, "Expected only 1 distinct row in the memory store, redundant insertion happened!"

    print("[Benchmark] LOCAL FALLBACK: PASSED - Redundant info bypasses standard ingestion successfully.")
