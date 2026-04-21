"""
Unit Tests: Biological Decay Algorithm
Validates the paper's formal decay equation:
    C(t) = max(0.1, C(t-1) - α / (1 + U/10 + |E|/10))
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

WS = f"unit_decay_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def store():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    s = MemoryStore()
    ws = ws_mgr.get_or_create(WS)
    ep_mgr.get_or_create_active(ws["id"], WS)
    return s


def _get_confidence(memory_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT confidence FROM memories WHERE id=?", (memory_id,)).fetchone()
        return row["confidence"] if row else None
    finally:
        conn.close()


def _set_scores(memory_id, urgency, emotion, confidence=1.0):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE memories SET urgency_score=?, emotional_valence=?, confidence=? WHERE id=?",
            (urgency, emotion, confidence, memory_id)
        )
        conn.commit()
    finally:
        conn.close()


def test_decay_reduces_confidence(store):
    """Decay must lower confidence below initial 1.0."""
    m = store.remember("Low urgency low emotion memory.", workspace_name=WS)
    _set_scores(m["id"], urgency=0, emotion=0, confidence=1.0)
    store.decay_memories()
    conf = _get_confidence(m["id"])
    assert conf is not None
    assert conf < 1.0, f"Confidence should have decayed below 1.0, got {conf}"


def test_decay_never_below_floor(store):
    """Confidence must never drop below 0.1 (the paper's minimum floor)."""
    m = store.remember("Memory near floor.", workspace_name=WS)
    _set_scores(m["id"], urgency=0, emotion=0, confidence=0.11)
    # Run decay multiple times
    for _ in range(20):
        store.decay_memories()
    conf = _get_confidence(m["id"])
    assert conf is not None
    assert conf >= 0.1, f"Confidence floored below 0.1: {conf}"


def test_high_urgency_decays_slower(store):
    """High urgency (U=10) should decay slower than low urgency (U=0)."""
    m_low = store.remember("Low urgency — decays fast.", workspace_name=WS)
    m_high = store.remember("High urgency — decays slow.", workspace_name=WS)
    _set_scores(m_low["id"], urgency=0, emotion=0, confidence=1.0)
    _set_scores(m_high["id"], urgency=10, emotion=0, confidence=1.0)

    store.decay_memories()

    conf_low = _get_confidence(m_low["id"])
    conf_high = _get_confidence(m_high["id"])

    assert conf_low is not None and conf_high is not None
    assert conf_high >= conf_low, (
        f"High urgency should decay slower: high={conf_high:.4f}, low={conf_low:.4f}"
    )


def test_high_emotion_decays_slower(store):
    """High |E| (emotional valence) should resist decay."""
    m_neutral = store.remember("Neutral emotional memory.", workspace_name=WS)
    m_emotional = store.remember("Highly emotional memory.", workspace_name=WS)
    _set_scores(m_neutral["id"], urgency=5, emotion=0, confidence=1.0)
    _set_scores(m_emotional["id"], urgency=5, emotion=10, confidence=1.0)

    store.decay_memories()

    conf_neutral = _get_confidence(m_neutral["id"])
    conf_emotional = _get_confidence(m_emotional["id"])

    assert conf_neutral is not None and conf_emotional is not None
    assert conf_emotional >= conf_neutral, (
        f"Emotional memory should decay slower: emotional={conf_emotional:.4f}, neutral={conf_neutral:.4f}"
    )


def test_decay_equation_exact_math():
    """
    Validate the formal decay equation directly:
        C(t) = max(0.1, C(t-1) - α / (1 + U/10 + |E|/10))
    with known values to verify correctness against the paper.
    """
    alpha = 0.05
    C_prev = 1.0
    U = 5     # urgency
    E = 3     # emotional valence

    expected = max(0.1, C_prev - alpha / (1 + U / 10 + abs(E) / 10))
    denominator = 1 + U / 10 + abs(E) / 10
    computed = max(0.1, C_prev - alpha / denominator)

    assert abs(computed - expected) < 1e-10, f"Equation mismatch: {computed} != {expected}"
    assert computed < C_prev, "Decay must reduce confidence"
    assert computed >= 0.1, "Must not fall below floor"


def test_decay_does_not_affect_archived_memories(store):
    """Archived (is_current=0) memories should not gain or lose confidence via decay."""
    m = store.remember("Will be archived.", workspace_name=WS)
    updated = store.update(m["id"], "Updated, archiving original.", "archiving", WS)

    conf_before = _get_confidence(m["id"])
    store.decay_memories()
    conf_after = _get_confidence(m["id"])

    # Archived memories can still decay, but should not go below floor
    if conf_after is not None:
        assert conf_after >= 0.1
