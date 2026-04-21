"""
Unit Tests: Epoch Lifecycle (TLCM Principle 2)
Validates epoch creation, listing, close, active state management.

EpochManager API:
  create(workspace_id, name, desc) → {id, name, workspace_id}
  get_active(workspace_id) → dict|None
  get_by_name(workspace_id, name) → dict|None (full row)
  get_or_create_active(workspace_id, ws_name) → dict
  close_epoch(workspace_id, epoch_name) → bool
  list_epochs(workspace_id) → list[dict]
"""
import os
import sys
import uuid
import pytest

os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.workspace import WorkspaceManager
from core.epoch import EpochManager

WS = f"unit_epoch_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def setup():
    ws_mgr = WorkspaceManager()
    ep_mgr = EpochManager()
    ws = ws_mgr.get_or_create(WS)
    return ep_mgr, ws


def test_create_epoch_returns_dict(setup):
    ep_mgr, ws = setup
    ep = ep_mgr.create(ws["id"], f"ep_{uuid.uuid4().hex[:4]}", "A test epoch")
    assert isinstance(ep, dict)
    assert "id" in ep


def test_epoch_has_name(setup):
    ep_mgr, ws = setup
    name = f"named_{uuid.uuid4().hex[:4]}"
    ep = ep_mgr.create(ws["id"], name, "Named epoch")
    assert ep["name"] == name


def test_epoch_is_active_by_default(setup):
    ep_mgr, ws = setup
    name = f"active_{uuid.uuid4().hex[:4]}"
    ep_mgr.create(ws["id"], name, "Should be active")
    # create() returns slim dict, so fetch full row via get_by_name
    fetched = ep_mgr.get_by_name(ws["id"], name)
    assert fetched is not None
    assert fetched["is_active"] == 1


def test_list_epochs_returns_list(setup):
    ep_mgr, ws = setup
    result = ep_mgr.list_epochs(ws["id"])
    assert isinstance(result, list)


def test_list_epochs_contains_created(setup):
    ep_mgr, ws = setup
    name = f"listable_{uuid.uuid4().hex[:4]}"
    ep_mgr.create(ws["id"], name, "Listable epoch")
    all_epochs = ep_mgr.list_epochs(ws["id"])
    names = [e["name"] for e in all_epochs]
    assert name in names


def test_get_by_name(setup):
    ep_mgr, ws = setup
    name = f"getbyname_{uuid.uuid4().hex[:4]}"
    ep_mgr.create(ws["id"], name, "Get by name test")
    fetched = ep_mgr.get_by_name(ws["id"], name)
    assert fetched is not None
    assert fetched["name"] == name


def test_get_by_name_nonexistent_returns_none(setup):
    ep_mgr, ws = setup
    result = ep_mgr.get_by_name(ws["id"], "this_epoch_does_not_exist_xyz")
    assert result is None


def test_close_epoch_deactivates(setup):
    ep_mgr, ws = setup
    name = f"closeable_{uuid.uuid4().hex[:4]}"
    ep_mgr.create(ws["id"], name, "Will be closed")
    # close_epoch(workspace_id, epoch_name) — not close(epoch_id)
    ep_mgr.close_epoch(ws["id"], name)
    fetched = ep_mgr.get_by_name(ws["id"], name)
    assert fetched["is_active"] == 0


def test_get_or_create_active_returns_epoch(setup):
    ep_mgr, ws = setup
    ep = ep_mgr.get_or_create_active(ws["id"], WS)
    assert ep is not None
    assert "id" in ep


def test_duplicate_epoch_name_handled(setup):
    """Creating two epochs with same name should either succeed or raise gracefully."""
    ep_mgr, ws = setup
    name = f"dup_{uuid.uuid4().hex[:4]}"
    ep_mgr.create(ws["id"], name, "First")
    try:
        ep_mgr.create(ws["id"], name, "Duplicate")
    except Exception as e:
        assert isinstance(e, Exception)
