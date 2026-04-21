"""
Unit Tests: Workspace Isolation (TLCM Principle 3)
Validates that workspace isolation is mathematically enforced.
Research paper claim: "P(Retrieval | Workspace_A) = 0 for Workspace_B"
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

WS_A = f"isolation_ws_a_{uuid.uuid4().hex[:6]}"
WS_B = f"isolation_ws_b_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def store():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    s = MemoryStore()
    for ws_name in [WS_A, WS_B]:
        ws = ws_mgr.get_or_create(ws_name)
        ep_mgr.get_or_create_active(ws["id"], ws_name)
    return s


def test_ws_a_memory_not_in_ws_b(store):
    """Memory stored in WS_A must not appear in WS_B recall."""
    store.remember("Project Falcon uses titanium airframes.", workspace_name=WS_A)
    results = store.recall("titanium airframes Falcon", workspace_name=WS_B, limit=5)
    for r in results:
        assert "titanium" not in r["content"].lower(), (
            f"ISOLATION BREACH: 'titanium' found in WS_B: {r['content']}"
        )


def test_ws_b_memory_not_in_ws_a(store):
    """Memory stored in WS_B must not appear in WS_A recall."""
    store.remember("My sourdough uses 500g flour and 350ml water.", workspace_name=WS_B)
    results = store.recall("sourdough flour water", workspace_name=WS_A, limit=5)
    for r in results:
        assert "sourdough" not in r["content"].lower(), (
            f"ISOLATION BREACH: 'sourdough' found in WS_A: {r['content']}"
        )


def test_recall_only_returns_own_workspace(store):
    """All recalled memories must belong to the queried workspace."""
    store.remember("AGI project timeline: 2028 target.", workspace_name=WS_A)
    store.remember("Personal diary: walked the dog today.", workspace_name=WS_B)

    results_a = store.recall("project timeline target", workspace_name=WS_A, limit=10)
    for r in results_a:
        assert "walked the dog" not in r["content"].lower(), "WS_B content leaked into WS_A"


def test_workspace_link_does_not_auto_bleed(store):
    """Even linked workspaces must not bleed without explicit cross-workspace query."""
    ws_mgr = WorkspaceManager()
    ws_mgr.authorize_link(WS_A, WS_B, "test link")
    # Recall from WS_A still only returns WS_A memories
    results_a = store.recall("sourdough flour", workspace_name=WS_A, limit=5)
    for r in results_a:
        assert "sourdough" not in r["content"].lower(), "Link must not auto-bleed memories"


def test_isolated_workspaces_can_have_same_content(store):
    """
    Same content stored in both workspaces must return from each separately.
    Proves isolation does not de-duplicate across workspace boundaries.
    """
    content = "The core hypothesis is that consciousness requires temporal binding."
    store.remember(content, workspace_name=WS_A)
    store.remember(content, workspace_name=WS_B)

    results_a = store.recall("consciousness temporal binding", workspace_name=WS_A, limit=3)
    results_b = store.recall("consciousness temporal binding", workspace_name=WS_B, limit=3)

    contents_a = [r["content"] for r in results_a]
    contents_b = [r["content"] for r in results_b]

    assert any("temporal binding" in c.lower() for c in contents_a), "WS_A should find its own copy"
    assert any("temporal binding" in c.lower() for c in contents_b), "WS_B should find its own copy"
