"""
DIAGNOSTIC: Find out exactly what's slow in the TLCM pipeline.
Run: python -X utf8 diag.py
"""
import os, time, tempfile, sys
from pathlib import Path

os.environ["TLCM_TEST_MODE"] = "1"
sys.path.insert(0, ".")

# ---- Step 1: Test _embed speed ----
print("=" * 50)
print("STEP 1: Testing _embed speed (should be instant with TLCM_TEST_MODE)")
from core.embeddings import _embed
t0 = time.time()
for i in range(10):
    _embed(f"test text {i}")
t1 = time.time()
print(f"  10 embeddings took {t1-t0:.3f}s  --> {'OK' if t1-t0 < 1 else 'SLOW'}")

# ---- Step 2: Test ChromaDB upsert speed ----
print("\nSTEP 2: Testing ChromaDB upsert speed (PersistentClient)")
import chromadb
tmp = tempfile.mkdtemp()
client = chromadb.PersistentClient(path=tmp)
col = client.get_or_create_collection("test_diag")
t0 = time.time()
for i in range(10):
    col.upsert(
        ids=[f"id_{i}"],
        embeddings=[[0.1]*768],
        documents=[f"doc {i}"],
        metadatas=[{"ws": "test"}]
    )
t1 = time.time()
print(f"  10 Chroma upserts took {t1-t0:.3f}s  --> {'OK' if t1-t0 < 5 else 'SLOW'}")

# ---- Step 3: Test EphemeralClient speed ----
print("\nSTEP 3: Testing ChromaDB upsert speed (EphemeralClient / in-memory)")
client2 = chromadb.EphemeralClient()
col2 = client2.get_or_create_collection("test_diag_mem")
t0 = time.time()
for i in range(10):
    col2.upsert(
        ids=[f"id_{i}"],
        embeddings=[[0.1]*768],
        documents=[f"doc {i}"],
        metadatas=[{"ws": "test"}]
    )
t1 = time.time()
print(f"  10 Chroma upserts (in-memory) took {t1-t0:.3f}s  --> {'OK' if t1-t0 < 1 else 'SLOW'}")

# ---- Step 4: Test full remember() pipeline ----
print("\nSTEP 4: Testing full MemoryStore.remember() pipeline")
# Patch DB and Chroma to temp
import core.database, core.embeddings
core.database.DB_PATH = Path(tmp) / "diag.db"
core.embeddings.CHROMA_PATH = Path(tmp) / "diag_chroma"
core.database.init_db()

from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager

ws = WorkspaceManager()
ep = EpochManager()
mem = MemoryStore()

ws.get_or_create("DiagWS", "diag")
t0 = time.time()
for i in range(5):
    mem.remember(f"Test memory {i}", "DiagWS")
t1 = time.time()
print(f"  5 full remember() calls took {t1-t0:.3f}s  --> {'OK' if t1-t0 < 5 else 'SLOW'}")

# ---- Step 5: Test ollama.chat mock ----
print("\nSTEP 5: Testing temporal jump (should skip LLM)")
from core.temporal_jump import TemporalJumpEngine
jump = TemporalJumpEngine()
ws_id = ws.get_or_create("JumpDiag", "...")[  "id"]
ep.create(ws_id, "Diag-E1", "...")
mem.remember("Fact A.", "JumpDiag", "Diag-E1")
ep.create(ws_id, "Diag-E2", "...")
mem.remember("Fact B.", "JumpDiag", "Diag-E2")
t0 = time.time()
result = jump.jump("JumpDiag", "Diag-E1", "Diag-E2")
t1 = time.time()
print(f"  Temporal jump took {t1-t0:.3f}s  --> {'OK' if t1-t0 < 2 else 'SLOW'}")
print(f"  Jump result snippet: {result[:100]}...")

print("\n" + "=" * 50)
print("DIAGNOSIS COMPLETE")
