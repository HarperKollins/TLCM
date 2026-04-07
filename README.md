# Temporal Layered Context Memory (TLCM) Engine

> *"Current AI memory systems treat memory as a filing cabinet: store, retrieve, overwrite. The human brain treats memory as a living architecture: versioned, temporally indexed, emotionally weighted, and spatially separated by context."* — **Collins Somtochukwu (Harper Kollins)**

**TLCM** is a neuro-inspired AI memory engine built to solve the structural failures of current Large Language Model memory architectures. Instead of relying on sprawling, chaotic vector dumps or flat un-versioned updates, TLCM implements time and context as fundamental, first-class architectural dimensions.

---

## The Structural Problem

The TLCM Engine solves three exact failure modes present in modern LLMs (MemGPT, ChatGPT, standard RAG):

1. **The Snapshot Problem:** AI systems store facts as static photographs. When reality updates, the photograph becomes fiction.
2. **The Overwrite Problem:** When current AI *does* update, it destroys the old memory. It loses the evolutionary arc. It cannot answer: *"How did we get from what we believed in 2024 to what we believe in 2026?"*
3. **The Context Bleed Problem:** AIs process all active goals in one flat namespace. Your startup data blends with your personal relationship data, creating unauthorized, hallucinatory connections.

---

## How TLCM Solves It — The 4 Principles

TLCM maps cognitive neuroscience directly to software engineering:

### Principle 1: Versioned Memory (No Overwrite)
Powered by specialized `SQLite` version-chain logic, **memories are never deleted**. When a fact updates, a new version is created containing a pointer (`parent_id`) to the previous version and a reason for the shift. The system operates as a **Git repository for AI beliefs**.

```
v1 (original) --> v2 (updated) --> v3 (updated)
|                  |                  |
parent_id=NULL     parent_id=v1       parent_id=v2
                   reason="..."       reason="..."
```

Every update triggers a **transactional write**: the SQLite insert and ChromaDB vector upsert happen inside a `try/except/rollback` block. If either fails, both are rolled back — preventing "ghost memories" where one store has data the other doesn't.

### Principle 2: Temporal Epoch Tagging
Inspired by autobiographical "lifetime periods," every fact belongs to a contextual epoch (e.g., *"Pre-Launch Phase"*, *"Data Collection"*). When an epoch closes, it is archived but mathematically preserved. Epochs are stored as relational rows with foreign keys to workspaces.

### Principle 3: Context Workspace Isolation
Powered by strictly segregated `ChromaDB` semantic namespaces, cognitive workspaces are isolated. A query about your screenplay is **mathematically incapable** of retrieving vectors regarding your AI startup unless you authorize an explicit cross-workspace link.

**Technical implementation**: Each workspace gets a single ChromaDB collection (e.g., `ws_project_alpha`). Epoch filtering uses ChromaDB's native metadata `where` clause — not separate collections. This prevents the scalability trap of creating hundreds of tiny SQLite files on disk.

### Principle 4: The Temporal Jump (Mathematical Semantic Delta)
When asked to evaluate the past, TLCM reconstructs a complete world-state using the preserved memory graphs. Unlike naive implementations that dump two epoch lists into an LLM and ask *"what changed?"*, TLCM **algorithmically computes the delta** in Python before the LLM ever sees it.

The algorithm walks the `parent_id` version chains and categorizes every memory into:

| Category | Definition | Symbol |
|---|---|---|
| **Continuity** | Memory exists in both epochs, unchanged | `from_ids ∩ to_ids` |
| **Evolution** | Memory exists in both epochs, but version changed | `parent_id(to) ∈ from_ids` |
| **Addition** | Memory exists only in the target epoch | `to_ids \ from_ids \ evolved_ids` |

The LLM (locally via `Ollama`) only receives this **pre-computed structured delta** and is asked to summarize its meaning — not to calculate it. This eliminates hallucinated changes and semantic drift.

---

## Biological Decay Algorithm

Inspired by the Ebbinghaus Forgetting Curve from human physiology, TLCM implements a **biological decay mechanism** for memory confidence:

### The Math

Each memory has three decay-related fields:

| Field | Type | Purpose |
|---|---|---|
| `confidence` | `REAL` (0.1 — 1.0) | Current belief strength |
| `recall_count` | `INTEGER` | Times this memory has been retrieved |
| `last_recalled_at` | `TEXT` (ISO datetime) | Timestamp of last retrieval |

**On Recall (Strengthening):**
```
confidence = MIN(1.0, confidence + 0.05)
recall_count += 1
last_recalled_at = NOW()
```

**On Decay (Periodic weakening of dormant memories):**
```
IF (julianday('now') - julianday(last_recalled_at)) > 1 day:
    confidence = MAX(0.1, confidence - 0.05)
    recall_count = recall_count / 2
```

Memories that are never recalled gradually fade. Memories that are frequently recalled strengthen. The floor of `0.1` prevents total erasure — the system never forgets, it just reduces confidence.

---

## Architecture Stack

```
┌──────────────────────────────────────────────────┐
│                   TLCM ENGINE                     │
├──────────────────────────────────────────────────┤
│  CLI (Typer + Rich)     │    API (FastAPI)        │
├──────────────────────────────────────────────────┤
│              Core Python Logic                    │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │MemoryStore │ │EpochManager│ │TemporalJump  │  │
│  │ (remember, │ │ (create,   │ │ (delta calc, │  │
│  │  update,   │ │  archive,  │ │  LLM summary,│  │
│  │  recall,   │ │  activate) │ │  belief arc) │  │
│  │  decay)    │ │            │ │              │  │
│  └──────┬─────┘ └────────────┘ └──────────────┘  │
│         │                                         │
│  ┌──────┴──────────────────────────────────────┐  │
│  │        Transaction Safety Layer              │  │
│  │  try { SQLite + ChromaDB } catch { rollback }│  │
│  └──────┬───────────────┬──────────────────────┘  │
│         │               │                         │
│  ┌──────┴─────┐  ┌──────┴──────┐                  │
│  │  SQLite    │  │  ChromaDB   │                  │
│  │  (Truth)   │  │  (Search)   │                  │
│  │  Versions, │  │  Embeddings,│                  │
│  │  Epochs,   │  │  1 collection│                 │
│  │  Chains    │  │  per workspace│                │
│  └────────────┘  └─────────────┘                  │
│         │               │                         │
│  ┌──────┴───────────────┴──────────────────────┐  │
│  │             Ollama (Local LLM)               │  │
│  │  gemma2:2b — embeddings + temporal analysis  │  │
│  └──────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────┤
│  Visual Mind UI: React + Vite (Phase 3)          │
└──────────────────────────────────────────────────┘
```

Designed to run fully locally without cloud API dependencies on moderate hardware.

---

## Peer Review Upgrades (v0.2)

After a rigorous peer code review, the following critical upgrades were implemented:

### Challenge 1: Hybrid Store Drift ("Ghost Memories")
**Problem:** `remember()` and `update()` wrote to SQLite first, then called ChromaDB separately. If Chroma crashed mid-write (common on low-VRAM machines), SQLite had the memory but Chroma didn't — or vice versa. This created "ghost memories" that could never be recalled or that returned stale data.

**Solution:** Wrapped all dual-store operations in explicit `try/except/rollback` blocks. The SQLite transaction is only committed **after** ChromaDB confirms the upsert. If either fails, both roll back atomically.

### Challenge 2: ChromaDB Scalability Trap
**Problem:** The original code created a **new ChromaDB collection** for every workspace+epoch combination. With 50 workspaces × 10 epochs = 500 collections, each spawning its own SQLite file on disk. On the target hardware (3rd-gen Intel, 1TB SSD), this caused catastrophic I/O.

**Diagnostic finding:** `PersistentClient` takes **1.84 seconds per upsert** on this hardware. Tests with 100 memories would hang for 3+ minutes.

**Solution:**
- One collection per workspace (epoch filtering via `where={"epoch": name}` metadata)
- Singleton client cache (no re-creation per call)
- `EphemeralClient` (in-memory, 287x faster) for test mode

### Challenge 3: The "Prompt-Logic Trap"
**Problem:** The Temporal Jump fed two raw lists of memories to a 2B-parameter LLM and asked it to *"identify every significant change."* Small models hallucinate connections and miss subtle contradictions. The novel feature was reduced to prompt engineering.

**Solution:** Implemented a **Mathematical Semantic Delta** algorithm in pure Python:
1. Index all `from_epoch` memories by ID into a lookup set
2. For each `to_epoch` memory, check if its ID exists in the from-set (Continuity)
3. If not, walk the `parent_id` chain via `get_version_history()` to find if any ancestor is in the from-set (Evolution)
4. Otherwise, classify as Addition
5. The LLM only receives this pre-categorized delta for summary — it never calculates the diff itself

### Challenge 4: Missing Biological Decay
**Problem:** The README described "emotionally weighted" memory but the schema had no columns for it. No mechanism existed to reduce confidence over time.

**Solution:** Added `recall_count`, `last_recalled_at` columns with safe ALTER TABLE migration. Implemented strengthening-on-recall and periodic decay (see Biological Decay Algorithm section above).

### Challenge 5: Demo Test Was Marketing, Not Validation
**Problem:** `test_tlcm.py` used self-referential data ("HKAI has 200 users across Lagos"), had no assertions, and Principle 4 (Temporal Jump) was not actually tested.

**Solution:**
- Replaced all personal data with generic synthetic variables ("Project Alpha", "metric X yields 15% gain")
- Created `tests/test_benchmark.py` with 3 rigorous `pytest` tests with real assertions
- Added `tests/conftest.py` for isolated test environment (temp DB, mocked Ollama)

## TLCM-Bench Suite Results (v0.3)

The engine was subjected to the full **TLCM-Bench** suite (200 memories, 45 updates, 30 temporal queries) across 2 isolated workspaces. This benchmark runs deterministically in `TLCM_TEST_MODE`.

```
============================================================
BENCHMARK RESULTS SUMMARY
============================================================
  config.................................. TLCM Full (all features enabled)
  total_memories.......................... 200
  total_updates........................... 45
  update_success_rate..................... 45/45
  ingest_time_s........................... 71.14 (0.35s/memory)
  update_time_s........................... 18.42
  isolation............................... PASS (0 violations)
  point_in_time_accuracy.................. 100.0% (10/10)
  evolution_tracking_accuracy............. 100.0% (10/10)
  decayed_memories........................ 7 (confidence dropped to 0.95)
  delta_computed.......................... True
============================================================
```

### 1. Workspace Isolation
Tested across `Research Lab` and `Supply Chain`. Even with semantic overlap (e.g., both discussing "metrics" and "performance"), cross-workspace queries yielded zero bleed.

### 2. The Temporal Delta
Tested temporal jumps (e.g., `Hypothesis` → `Publication`). The Mathematical Semantic Delta algorithm successfully bypassed LLM-dependent diffing by generating strict vectors of Additions, Continuities, and Evolutions based on Git-style version chains.

### 3. Biological Decay
Memories dormant for 5+ days successfully triggered the decay mechanic, reducing their confidence score mathematically (`1.0` → `0.95`) without deletion.

---

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Requires [Ollama](https://ollama.ai/) running locally with `gemma2:2b`:
```bash
ollama pull gemma2:2b
```

### 2. The Terminal CLI
```bash
cd tlcm-engine

# Initialize a workspace
python tlcm.py workspace create "Project Alpha" --desc "Primary research"

# Create a temporal boundary
python tlcm.py epoch create "Project Alpha" "Phase 1"

# Store an immutable memory
python tlcm.py remember --workspace "Project Alpha" "Initial metric X is 15%."

# Jump back in time
python tlcm.py jump --workspace "Project Alpha" --from "Phase 1" --to "Current"

# Enter the neuro-shell
python tlcm.py chat --workspace "Project Alpha"
```

### 3. The API Server
```bash
python -m uvicorn server.main:app --reload --port 8000
```
Endpoints:
- `GET /api/workspaces`
- `POST /api/memories/remember`
- `GET /api/memories/{id}/history` (Fetches the evolutionary arc of a thought)
- `POST /api/jump`

### 4. The Visual Dashboard
```bash
cd tlcm-web
npm run dev
```

### 5. Run the Benchmark Suite
```bash
# Full benchmark (mocked Ollama, fast, no GPU needed)
python -X utf8 -m pytest tests/test_benchmark.py -v -s

# Smoke test (requires Ollama running)
python -X utf8 test_tlcm.py

# Hardware diagnostic
python -X utf8 diag.py
```

---

## File Structure

```
tlcm-engine/
├── core/
│   ├── database.py        # SQLite schema, migrations, WAL mode
│   ├── memory_store.py     # Remember, update, recall, decay (transactional)
│   ├── embeddings.py       # ChromaDB engine, singleton client, metadata filtering
│   ├── temporal_jump.py    # Mathematical Semantic Delta + LLM summary
│   ├── epoch.py            # Epoch lifecycle management
│   ├── workspace.py        # Workspace CRUD + isolation
│   └── chat.py             # Interactive neuro-shell
├── server/                 # FastAPI REST layer
├── tlcm-web/               # React + Vite dashboard
├── tests/
│   ├── conftest.py         # Test environment (temp DB, TLCM_TEST_MODE)
│   └── test_benchmark.py   # 3 rigorous pytest benchmarks
├── tlcm.py                 # CLI entry point (Typer + Rich)
├── test_tlcm.py            # Functional smoke test
├── diag.py                 # Hardware diagnostic script
└── requirements.txt
```

---

## Theoretical Origins

This architecture implements the specifications proposed in **"The Memory Gap: A Thesis on Temporal, Layered, and Context-Isolated Memory for AI Systems"** by Collins Somtochukwu (April 2026). It utilizes the neuro-mathematical models of Endel Tulving's episodic contiguity and the validated Temporal Context Model (TCM).

*(No facts overwrite. No contexts bleed. Everything is time.)*
