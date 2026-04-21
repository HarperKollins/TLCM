"""
Unit Tests: Temporal Jump Engine (TLCM Principle 4)
Validates the pure Python mathematical delta calculation.
Research paper claim: "algorithmically computes set transitions before the LLM reviews it"
"""
import os
import sys
import uuid
import pytest

os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.temporal_jump import TemporalJumpEngine
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager

WS = f"unit_jump_{uuid.uuid4().hex[:6]}"
EPOCH_A = f"epoch_alpha_{uuid.uuid4().hex[:4]}"
EPOCH_B = f"epoch_beta_{uuid.uuid4().hex[:4]}"


@pytest.fixture(scope="module")
def setup():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    store = MemoryStore()
    jumper = TemporalJumpEngine()

    ws = ws_mgr.get_or_create(WS)
    ep_mgr.create(ws["id"], EPOCH_A, "Origin epoch")
    ep_mgr.create(ws["id"], EPOCH_B, "Target epoch")

    # Store memories in Epoch A
    store.remember("Budget is $50,000.",           workspace_name=WS, epoch_name=EPOCH_A)
    store.remember("Team uses Python 3.10.",       workspace_name=WS, epoch_name=EPOCH_A)
    store.remember("Office is in London.",         workspace_name=WS, epoch_name=EPOCH_A)

    # Store memories in Epoch B (some new, some evolved)
    store.remember("Budget increased to $75,000.", workspace_name=WS, epoch_name=EPOCH_B)
    store.remember("Team uses Python 3.12.",       workspace_name=WS, epoch_name=EPOCH_B)
    store.remember("Office is in London.",         workspace_name=WS, epoch_name=EPOCH_B)  # continuity
    store.remember("New: hired 5 engineers.",      workspace_name=WS, epoch_name=EPOCH_B)  # addition

    return jumper, store, ws


def test_delta_returns_required_keys(setup):
    """calculate_delta must return continuities, additions, evolutions."""
    jumper, _, _ = setup
    delta = jumper.calculate_delta(WS, EPOCH_A, EPOCH_B)
    assert "continuities" in delta, "Missing 'continuities'"
    assert "additions" in delta,    "Missing 'additions'"
    assert "evolutions" in delta,   "Missing 'evolutions'"


def test_delta_continuities_is_list(setup):
    jumper, _, _ = setup
    delta = jumper.calculate_delta(WS, EPOCH_A, EPOCH_B)
    assert isinstance(delta["continuities"], list)


def test_delta_additions_is_list(setup):
    jumper, _, _ = setup
    delta = jumper.calculate_delta(WS, EPOCH_A, EPOCH_B)
    assert isinstance(delta["additions"], list)


def test_delta_evolutions_is_list(setup):
    jumper, _, _ = setup
    delta = jumper.calculate_delta(WS, EPOCH_A, EPOCH_B)
    assert isinstance(delta["evolutions"], list)


def test_delta_detects_additions(setup):
    """Memories only in epoch B must appear as additions."""
    jumper, _, _ = setup
    delta = jumper.calculate_delta(WS, EPOCH_A, EPOCH_B)
    addition_contents = [a["content"] for a in delta["additions"]]
    assert any("engineer" in c.lower() for c in addition_contents), (
        f"Expected 'engineers' in additions. Got: {addition_contents}"
    )


def test_delta_invalid_epoch_raises(setup):
    jumper, _, _ = setup
    with pytest.raises((ValueError, Exception)):
        jumper.calculate_delta(WS, "nonexistent_epoch_xyz", EPOCH_B)


def test_jump_returns_string(setup):
    """jump() must return a non-empty string (prompt or LLM analysis)."""
    jumper, _, _ = setup
    result = jumper.jump(WS, EPOCH_A, EPOCH_B, query="How did the budget change?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_explain_belief_arc_returns_string(setup):
    """explain_belief_arc must return a coherent string for a valid memory."""
    jumper, store, _ = setup
    m = store.remember("Arc test: Initial belief.", workspace_name=WS)
    store.update(m["id"], "Arc test: Evolved belief.", "Evolution", WS)
    result = jumper.explain_belief_arc(m["id"], WS)
    assert isinstance(result, str)
    assert len(result) > 0
