"""
Unit Tests: MemoryStore Core Ops (remember, recall, update, version chain)
TLCM_TEST_MODE=1 for deterministic embeddings — no GPU required.

NOTE: remember() returns {id, workspace, epoch} (slim dict).
      update() returns {new_id, old_id, version, reason} (slim dict).
      Full row access requires DB query when needed.
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

WS = f"unit_ms_{uuid.uuid4().hex[:6]}"


def _fetch_row(memory_id):
    """Fetch full memory row from DB by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@pytest.fixture(scope="module")
def setup():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    store = MemoryStore()
    ws = ws_mgr.get_or_create(WS)
    ep = ep_mgr.get_or_create_active(ws["id"], WS)
    return store, ws, ep


def test_remember_returns_id(setup):
    store, _, _ = setup
    result = store.remember("AGI will require temporal memory.", workspace_name=WS)
    assert "id" in result
    assert result["id"]


def test_remember_stores_content(setup):
    store, _, _ = setup
    result = store.remember("TLCM uses neuro-weighted decay.", workspace_name=WS)
    row = _fetch_row(result["id"])
    assert row is not None
    assert row["content"] == "TLCM uses neuro-weighted decay."


def test_remember_default_source(setup):
    store, _, _ = setup
    result = store.remember("Workspace isolation is mathematical.", workspace_name=WS)
    row = _fetch_row(result["id"])
    assert row["source"] == "user_stated"


def test_remember_custom_source(setup):
    store, _, _ = setup
    result = store.remember("Cascade orphaning removes stale beliefs.", workspace_name=WS, source="observed")
    row = _fetch_row(result["id"])
    assert row["source"] == "observed"


def test_remember_version_starts_at_one(setup):
    store, _, _ = setup
    result = store.remember("First version of this belief.", workspace_name=WS)
    row = _fetch_row(result["id"])
    assert row["version"] == 1


def test_recall_returns_results(setup):
    store, _, _ = setup
    store.remember("The base decay rate alpha is 0.05.", workspace_name=WS)
    results = store.recall("decay rate alpha", workspace_name=WS, limit=5)
    assert isinstance(results, list)
    assert len(results) > 0


def test_recall_respects_limit(setup):
    store, _, _ = setup
    for i in range(7):
        store.remember(f"Recall limit test memory {i}.", workspace_name=WS)
    results = store.recall("recall limit test", workspace_name=WS, limit=3)
    assert len(results) <= 3


def test_update_creates_new_version(setup):
    store, _, _ = setup
    m = store.remember("Original: AGI deadline is 2030.", workspace_name=WS)
    updated = store.update(
        memory_id=m["id"],
        new_content="Updated: AGI deadline revised to 2028.",
        reason="New research findings",
        workspace_name=WS,
    )
    assert updated["version"] == 2
    row = _fetch_row(updated["new_id"])
    assert row["content"] == "Updated: AGI deadline revised to 2028."


def test_update_preserves_parent_id(setup):
    store, _, _ = setup
    m = store.remember("Original belief preserved.", workspace_name=WS)
    updated = store.update(m["id"], "Updated belief.", "Test", WS)
    row = _fetch_row(updated["new_id"])
    assert row["parent_id"] == m["id"]


def test_get_version_history_chain(setup):
    store, _, _ = setup
    m = store.remember("Chain start.", workspace_name=WS)
    v2 = store.update(m["id"], "Chain v2.", "Reason A", WS)
    v3 = store.update(v2["new_id"], "Chain v3.", "Reason B", WS)
    history = store.get_version_history(m["id"])
    assert len(history) >= 2


def test_recall_epoch_state_returns_list(setup):
    store, ws, ep = setup
    results = store.recall_epoch_state(ws["id"], ep["id"])
    assert isinstance(results, list)
