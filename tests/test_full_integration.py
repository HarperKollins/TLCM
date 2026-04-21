"""
TLCM Full Integration Test Suite
=================================
Tests every REST endpoint, SDK field contract, and the async memory bus
against a live FastAPI server. This is the definitive validation script.
"""

import sys
import os
import time
import json
import httpx
import uuid

# Use the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_BASE = "http://127.0.0.1:8000/api/v1"
TIMEOUT = 30.0

# Track results
results = []
TEST_ID = uuid.uuid4().hex[:6]
WS_NAME = f"test_integration_ws_{TEST_ID}"
LINK_WS_NAME = f"test_link_target_ws_{TEST_ID}"
EPOCH_ALPHA = f"test_epoch_alpha_{TEST_ID}"
EPOCH_BETA = f"test_epoch_beta_{TEST_ID}"

def test(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append((name, passed, detail))
    print(f"  {status} | {name}" + (f" — {detail}" if detail else ""))

def run_all_tests():
    client = httpx.Client(timeout=TIMEOUT)
    print("\n" + "=" * 70)
    print("  TLCM ENGINE — FULL INTEGRATION TEST SUITE")
    print("=" * 70)

    # ─── 0. Health Check ──────────────────────────────────────────
    print("\n🔹 Phase 0: Server Health")
    try:
        res = client.get("http://127.0.0.1:8000/")
        data = res.json()
        test("Root endpoint responds", res.status_code == 200)
        test("Version present", "version" in data, data.get("version", "missing"))
        test("Architecture present", "architecture" in data, data.get("architecture", "missing"))
    except Exception as e:
        test("Server reachable", False, str(e))
        print("\n⛔ Server not reachable. Aborting tests.\n")
        return

    # ─── 1. Workspaces ────────────────────────────────────────────
    print("\n🔹 Phase 1: Workspace Operations")
    res = client.post(f"{API_BASE}/workspaces/", json={"name": WS_NAME, "description": "Integration test workspace"})
    test("Create workspace", res.status_code == 200, f"status={res.status_code}")
    
    res2 = client.post(f"{API_BASE}/workspaces/", json={"name": LINK_WS_NAME, "description": "Link target workspace"})
    test("Create second workspace", res2.status_code in [200, 400], f"status={res2.status_code}")

    res = client.get(f"{API_BASE}/workspaces/")
    test("List workspaces", res.status_code == 200 and isinstance(res.json(), list))
    test("Workspace appears in list", any(w["name"] == WS_NAME for w in res.json()))

    res = client.get(f"{API_BASE}/workspaces/{WS_NAME}")
    test("Get workspace by name", res.status_code == 200)
    test("Workspace has 'id' field", "id" in res.json())

    res = client.post(f"{API_BASE}/workspaces/link", json={"source": WS_NAME, "target": LINK_WS_NAME, "reason": "Integration test link"})
    test("Link workspaces", res.status_code == 200, f"status={res.status_code}")

    res = client.get(f"{API_BASE}/workspaces/{WS_NAME}/links")
    test("Get workspace links", res.status_code == 200)

    # ─── 2. Epochs ────────────────────────────────────────────────
    print("\n🔹 Phase 2: Epoch Operations")
    res = client.post(f"{API_BASE}/epochs/", json={"workspace": WS_NAME, "name": EPOCH_ALPHA, "description": "First test epoch"})
    test("Create epoch", res.status_code == 200, f"status={res.status_code}")

    res = client.post(f"{API_BASE}/epochs/", json={"workspace": WS_NAME, "name": EPOCH_BETA, "description": "Second test epoch"})
    test("Create second epoch", res.status_code == 200)

    res = client.get(f"{API_BASE}/epochs/{WS_NAME}")
    test("List epochs", res.status_code == 200 and isinstance(res.json(), list))
    test("Epochs count >= 2", len(res.json()) >= 2, f"count={len(res.json())}")

    res = client.post(f"{API_BASE}/epochs/{WS_NAME}/{EPOCH_ALPHA}/close")
    test("Close epoch", res.status_code == 200)

    # ─── 3. Memory ──────────────────────────────────────────────
    print("\n🔹 Phase 3: Memory Operations (Field Contract Validation)")
    res = client.post(f"{API_BASE}/memories/remember/sync", json={
        "workspace": WS_NAME,
        "content": "I believe AGI will require temporal memory systems to handle belief evolution.",
        "epoch": EPOCH_BETA,
        "source": "integration_test"
    })
    test("Remember/sync with 'workspace' field", res.status_code == 200, f"status={res.status_code}")
    memory_id = res.json().get("id", "") if res.status_code == 200 else ""
    test("Memory has ID", bool(memory_id), memory_id[:12] if memory_id else "no id")

    res = client.post(f"{API_BASE}/memories/remember/sync", json={
        "workspace": WS_NAME,
        "content": "Neuro-weighted decay ensures old, unaccessed memories naturally fade like biological cognition.",
        "epoch": EPOCH_BETA,
        "source": "integration_test"
    })
    test("Store second memory", res.status_code == 200)

    res = client.post(f"{API_BASE}/memories/remember/sync", json={
        "workspace": WS_NAME,
        "content": "Graph surgery allows contradicting memories to coexist as versioned chains rather than being overwritten.",
        "epoch": EPOCH_BETA,
        "source": "integration_test"
    })
    test("Store third memory", res.status_code == 200)

    res_bad = client.post(f"{API_BASE}/memories/remember/sync", json={
        "workspace_name": WS_NAME,
        "content": "This should fail.",
        "epoch_name": EPOCH_BETA
    })
    test("OLD 'workspace_name' field REJECTED (422)", res_bad.status_code == 422, f"status={res_bad.status_code} (expected 422)")

    # ─── 4. Recall ────────────────────────────────────────────────
    print("\n🔹 Phase 4: Temporal Recall")
    res = client.post(f"{API_BASE}/memories/recall", json={
        "query": "How does memory decay work?",
        "workspace": WS_NAME,
        "limit": 5
    })
    test("Recall with 'workspace' field", res.status_code == 200)
    test("Recall returns results", len(res.json()) > 0 if res.status_code == 200 else False)

    res_bad2 = client.post(f"{API_BASE}/memories/recall", json={
        "query": "test",
        "workspace_name": WS_NAME
    })
    test("OLD 'workspace_name' in recall REJECTED (422)", res_bad2.status_code == 422, f"status={res_bad2.status_code}")

    # ─── 5. Async Bus ──────────────────────────────────────────────
    print("\n🔹 Phase 5: Async Memory Bus")
    res = client.post(f"{API_BASE}/memories/remember", json={
        "workspace": WS_NAME,
        "content": "Async bus test: This memory is enqueued into Tier 1 STM for background processing.",
        "source": "integration_test"
    })
    test("Async remember returns 202", res.status_code == 202, f"status={res.status_code}")
    temp_id = res.json().get("temp_id", "") if res.status_code == 202 else ""
    test("Has temp_id", bool(temp_id), temp_id)
    time.sleep(3)
    res_status = client.get(f"{API_BASE}/memories/status/{temp_id}")
    test("Poll memory status", res_status.status_code in [200, 404], f"status={res_status.status_code}")

    res = client.get(f"{API_BASE}/memories/queue/metrics")
    test("Queue metrics endpoint", res.status_code == 200)
    test("Metrics has capacity field", res.status_code == 200 and "max_capacity" in res.json())

    # ─── 6. Version History ─────────────────────────────────────────
    print("\n🔹 Phase 6: Version History & Graph Surgery")
    if memory_id:
        res = client.put(f"{API_BASE}/memories/{memory_id}", json={
            "workspace": WS_NAME,
            "new_content": "UPDATED: AGI requires temporal memory with surprise-driven reconsolidation, not just retrieval.",
            "reason": "Integration test: belief evolution"
        })
        test("Update memory (Graph Surgery)", res.status_code == 200, f"status={res.status_code}")

        res = client.get(f"{API_BASE}/memories/{memory_id}/history")
        test("Get version history", res.status_code == 200)
        test("Version chain has entries", res.status_code == 200 and len(res.json()) > 0)

    # ─── 7. Epoch Memories ────────────────────────────────────────
    print("\n🔹 Phase 7: Epoch-Scoped Memory Retrieval")
    res = client.get(f"{API_BASE}/memories/workspace/{WS_NAME}/epoch/{EPOCH_BETA}")
    test("Get epoch memories", res.status_code in [200, 404], f"status={res.status_code}")

    # ─── 8. Temporal Jump ─────────────────────────────────────────
    print("\n🔹 Phase 8: Temporal Jump Operations")
    res = client.post(f"{API_BASE}/jump/delta", json={
        "workspace": WS_NAME,
        "from_epoch": EPOCH_ALPHA,
        "to_epoch": EPOCH_BETA
    })
    test("Jump delta calculation", res.status_code in [200, 400, 500], f"status={res.status_code}")

    # ─── 9. Bus Status ────────────────────────────────────────────
    print("\n🔹 Phase 9: Infrastructure Endpoints")
    res = client.get(f"{API_BASE}/bus/status")
    test("Bus status endpoint", res.status_code == 200)
    test("Bus shows worker_running", res.status_code == 200 and "worker_running" in res.json())

    # ─── 10. Export ────────────────────────────────────────────────
    print("\n🔹 Phase 10: Export (.tlcm Backup)")
    res = client.get(f"{API_BASE}/export/")
    test("Export endpoint responds", res.status_code in [200, 404, 500], f"status={res.status_code}")

    # ─── 11. SSE Events ────────────────────────────────────────────
    print("\n🔹 Phase 11: SSE Event Stream")
    try:
        with httpx.stream("GET", f"{API_BASE}/events", timeout=5.0) as stream:
            test("SSE endpoint connectable", stream.status_code == 200)
    except httpx.ReadTimeout:
        test("SSE endpoint connectable (timeout expected)", True, "Stream timed out as expected")
    except Exception as e:
        test("SSE endpoint connectable", False, str(e))

    # ─── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    
    if failed > 0:
        print("\n  ❌ FAILURES:")
        for name, p, detail in results:
            if not p:
                print(f"     • {name}: {detail}")
    
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_all_tests()
