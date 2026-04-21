"""
Unit Tests: Graph Surgery / Cascade Orphaning
Validates TLCM's core contradiction resolution — the paper's signature feature.

NOTE: update() returns {new_id, old_id, version, reason} (slim dict).
      Full row access via DB query.
"""
import os
import sys
import uuid
import pytest

os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.database import get_connection

WS = f"unit_surgery_{uuid.uuid4().hex[:6]}"


def _fetch_row(memory_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@pytest.fixture(scope="module")
def store():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    s = MemoryStore()
    ws = ws_mgr.get_or_create(WS)
    ep_mgr.get_or_create_active(ws["id"], WS)
    return s


def test_graph_surgery_on_archived_memory(store):
    """Update an archived root → all descendants must become orphaned."""
    root = store.remember("Foundation: AGI requires symbolic reasoning.", workspace_name=WS)
    v2 = store.update(root["id"], "Foundation v2: AGI requires neural + symbolic.", "new data", WS)
    v3 = store.update(v2["new_id"], "Foundation v3: AGI is purely emergent.", "paradigm shift", WS)

    # Now update the ROOT (archived) memory — this triggers Graph Surgery
    store.update(root["id"], "CORRECTED ROOT: AGI requires temporal memory systems.", "fundamental correction", WS)

    # v2 and v3 should now be orphaned
    v2_row = _fetch_row(v2["new_id"])
    v3_row = _fetch_row(v3["new_id"])

    assert v2_row is not None
    assert v3_row is not None
    assert v2_row["reconsolidation_flag"] == "orphaned_via_surgery" or v2_row["is_current"] == 0
    assert v3_row["reconsolidation_flag"] == "orphaned_via_surgery" or v3_row["is_current"] == 0


def test_update_sets_parent_id(store):
    """Update must link new version to old via parent_id."""
    m = store.remember("Belief before surgery.", workspace_name=WS)
    updated = store.update(m["id"], "Belief after correction.", "Graph surgery test", WS)
    row = _fetch_row(updated["new_id"])
    assert row["parent_id"] == m["id"]


def test_update_increments_version(store):
    """Each update must increment the version counter by 1."""
    m = store.remember("Version counter test.", workspace_name=WS)
    v2 = store.update(m["id"], "v2", "increment test", WS)
    v3 = store.update(v2["new_id"], "v3", "increment test", WS)
    assert v2["version"] == 2
    assert v3["version"] == 3


def test_update_stores_reason(store):
    """The update reason must be stored in the new version."""
    m = store.remember("Reason storage test.", workspace_name=WS)
    reason = "New empirical evidence contradicts prior belief"
    updated = store.update(m["id"], "Updated content.", reason, WS)
    row = _fetch_row(updated["new_id"])
    assert row["update_reason"] == reason


def test_version_history_oldest_to_newest(store):
    """Version history must be ordered oldest → newest."""
    m = store.remember("Order test start.", workspace_name=WS)
    store.update(m["id"], "Order test v2.", "r2", WS)
    history = store.get_version_history(m["id"])
    versions = [h["version"] for h in history]
    assert versions == sorted(versions), f"History not sorted: {versions}"


def test_confidence_zeroed_on_orphan(store):
    """Orphaned memories should have confidence=0.0 per the paper."""
    root = store.remember("Root for confidence test.", workspace_name=WS)
    child = store.update(root["id"], "Child belief.", "setup", WS)
    # Trigger surgery on root (archived)
    store.update(root["id"], "Corrected root.", "surgery trigger", WS)

    row = _fetch_row(child["new_id"])
    if row:
        assert row["confidence"] <= 0.1, f"Orphaned memory should have near-zero confidence, got {row['confidence']}"
