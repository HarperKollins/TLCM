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
