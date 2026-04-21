# Temporal Layered Context Memory (TLCM) Engine

> *"Current AI memory systems treat memory as a filing cabinet: store, retrieve, overwrite. The human brain treats memory as a living architecture: versioned, temporally indexed, emotionally weighted, and spatially separated by context."* — **Collins Somtochukwu (Harper Kollins)**

**TLCM** is a neuro-inspired AI memory engine built to solve the structural failures of current Large Language Model memory architectures. Instead of relying on sprawling, chaotic vector dumps or flat un-versioned updates, TLCM implements time and context as fundamental, first-class architectural dimensions.

[![Tests](https://img.shields.io/badge/unit_tests-46%2F46_passing-brightgreen)]()
[![PyPI version](https://img.shields.io/pypi/v/tlcm-engine.svg)](https://pypi.org/project/tlcm-engine/)
[![Version](https://img.shields.io/badge/version-0.5.1-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## Installation

You can now natively install the complete TLCM engine via PyPI:
```bash
pip install tlcm-engine
```

## The Structural Problem

The TLCM Engine solves three exact failure modes present in modern LLMs:

1. **The Snapshot Problem:** AI systems store facts as static photographs. When reality updates, the photograph becomes fiction.
2. **The Overwrite Problem:** When current AI *does* update, it destroys the old memory. It loses the evolutionary arc. It cannot answer: *"How did we get from what we believed in 2024 to what we believe in 2026?"*
3. **The Context Bleed Problem:** AIs process all active goals in one flat namespace. Your startup data blends with your personal relationship data, creating unauthorized, hallucinatory connections.

---

## How TLCM Solves It — The 4 Principles

TLCM maps cognitive neuroscience directly to software engineering:

### Principle 1: Versioned Memory (No Overwrite)
Powered by specialized `SQLite` version-chain logic, **memories are never deleted**. When a fact updates, a new version is created containing a pointer (`parent_id`) to the previous version and a reason for the shift. The system operates as a **Git repository for AI beliefs**.

### Principle 2: Temporal Epoch Tagging
Inspired by autobiographical "lifetime periods," every fact belongs to a contextual epoch.

### Principle 3: Context Workspace Isolation
Powered by strictly segregated `ChromaDB` semantic namespaces, cognitive workspaces are isolated. A query about your screenplay is **mathematically incapable** of retrieving vectors regarding your AI startup unless you authorize an explicit cross-workspace link.

### Principle 4: The Temporal Jump (Mathematical Semantic Delta)
When asked to evaluate the past, TLCM reconstructs a complete world-state using the preserved memory graphs. The algorithm calculates the delta in pure Python.

---

## Neuro-Weighted Biological Decay Algorithm (v0.5)

Inspired by the Ebbinghaus Forgetting Curve and extended with **emotional reconsolidation theory**, TLCM implements a **neuro-weighted decay mechanism** where emotional intensity and urgency directly affect how fast memories fade.

### The Formal Decay Equation
```math
\mathcal{C}_{t} = \max\left( 0.1, \mathcal{C}_{t-1} - \frac{\alpha}{1 + \frac{\mathcal{U}}{10} + \frac{|\mathcal{E}|}{10}} \right)
```
Where:
- $\mathcal{C}_{t}$ is Confidence at time $t$
- $\alpha$ is the base decay rate (e.g., 0.05)
- $\mathcal{U}$ is Urgency Score $(0 - 10)$
- $\mathcal{E}$ is Emotional Valence $(-10 \dots +10)$

The decay daemon runs automatically as a periodic background task (default: 24h cycle, configurable via `TLCM_DECAY_INTERVAL_SECONDS`). Manual trigger available at `POST /api/v1/decay/run`.

---

## Surprise-Driven Reconsolidation
When a new high-urgency memory ($\mathcal{U} > 7$) arrives, the background daemon automatically surfaces semantically related older memories and actively boosts their confidence ($\mathcal{C}_{t} = \mathcal{C}_{t} + 0.1$). This is pure neuroscience replication: highly charged new events reinforce associated older memories.

---

## Pluggable Cognition Architecture

TLCM's cognition backend can be **seamlessly toggled** between cloud and air-gapped operation:

| Backend | Provider | Use Case |
|---|---|---|
| `gemini` (default) | Gemini 3.1 Flash Lite | Cloud, high-precision neuro-scoring |
| `ollama` | Any local Ollama model | Air-gapped, privacy-preserving, edge |

```bash
# Toggle via environment variable
COGNITION_BACKEND=gemini   # Cloud mode (default)
COGNITION_BACKEND=ollama   # Air-gapped mode
OLLAMA_COGNITION_MODEL=gemma2:2b  # Choose any local model
```

Custom providers (OpenAI, Anthropic, etc.) can be added by subclassing `CognitionProvider` in `core/interfaces.py`.

---

## Formal Properties

### Guaranteed Workspace Isolation Under Concurrent Updates
A mathematical limit via ChromaDB metadata filtering ensures `P(Retrieval | Workspace_ID_A) = 0` for `Workspace_ID_B`. The async memory bus manages thread-safe SQLite transactions alongside vector locks ensuring no cross-contamination under heavy multi-threading.

---

## Why TLCM Is Different (Comparison Table)

| Dimension | TLCM (v0.5) | Mem0 | Zep / Graphiti | Letta / MemGPT |
|---|---|---|---|---|
| **Versioned History** | **Full Git-style chains** | Flat Overwrite | Graph Edges | Mutable Archival |
| **Workspace Isolation** | **Mathematical Zero-Bleed** | Single Global Graph | Tenant Windows | Single Namespace |
| **Contradiction Physics** | **Cascade Orphaning** | Overwrite/Delete | Edge Reweighting | LLM Selection |
| **Decay Mechanism** | **Neuro-Weighted Math** | Custom/None | None | Eviction Policies |
| **Semantic Delta** | **Pre-computed Python Sets** | LLM Hallucinated diff | LLM hallucinated diff | Search |
| **Pluggable Backend** | **Gemini / Ollama / Custom** | OpenAI Only | OpenAI/Azure | OpenAI Only |

---

## 1k LoCoMo Benchmark Results

TLCM scaled to a 1000+ deterministic node graph evaluation via the LoCoMo context benchmark framework over 200 temporal and evolutionary queries. 

| Metric | TLCM Accuracy | Observation |
|---|---|---|
| Point-in-Time Retrieval | **98.8%** | Maintains exact timeline snapshots without future-state leakage. |
| Evolution Tracking | **98.3%** | Successfully traverses full DAG parent chains continuously. |
| Contradiction Resolution | **100%** | Cascade Orphaning flawlessly eliminates all outdated graph branches. |

---

## Unit Test Coverage (46/46 Passing)

| Test Suite | Tests | Coverage |
|---|---|---|
| Memory Store | 11 | remember, recall, update, version chains |
| Graph Surgery | 6 | Cascade orphaning, confidence zeroing |
| Workspace Isolation | 5 | Cross-workspace zero-bleed proof |
| Temporal Jump | 8 | Delta calculation, additions detection |
| Decay Math | 6 | Ebbinghaus equation, floor, urgency/emotion resistance |
| Epoch Lifecycle | 10 | Create, list, close, active state |

```bash
# Run all tests (no GPU required)
TLCM_TEST_MODE=1 python -m pytest tests/unit/ -v
```

---

## Ablation Results (Feature Proof)

| Configuration | Retrieval Accuracy | Isolation | Drift/Orphan Removal Rate |
|---|---|---|---|
| **TLCM Full** | **98.8%** | **PASS** | **100% Removed** |
| No Decay | 82.5% | PASS | 100% |
| No Epochs | 41.0% | PASS | Failed |
| No Math Delta | 12.0% | PASS | Failed (Hallucinated) |
| No Workspace Isolation | 63.5% | FAIL | 100% |

---

## Hardware Reality (Edge-First Design)

TLCM executes orchestration natively on edge devices leveraging an asynchronous ingestion tier `MemoryBus` to handle STM (Short Term Memory) spikes.

**Performance on Constrained Hardware:**
- Machine: Intel i5, 16GB RAM (No GPU).
- STM Ingestion: **<20ms per query**.
- LTM Processing (Background): **~120ms** asynchronous resolution.
- Latency is successfully decoupled from LLM inference. 

---

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Configure Backend Engine
Create a `.env` file in the project root:
```env
# Cognition backend (gemini or ollama)
COGNITION_BACKEND=gemini
GEMINI_API_KEY=your_key_here

# Optional: Secure the API
TLCM_API_KEY=super_secret_key

# Optional: Air-gapped mode
# COGNITION_BACKEND=ollama
# OLLAMA_COGNITION_MODEL=gemma2:2b
```

### 3. Run the Slim Node Server
```bash
python -m uvicorn server.main:app --reload --port 8000
```

### 4. Dashboard
The web dashboard is available at `http://localhost:8000/dashboard` (requires building the frontend first):
```bash
cd tlcm-web && npm install && npm run build
```

### 5. API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/memories/remember` | Async memory ingestion via bus |
| `POST` | `/api/v1/memories/remember/sync` | Synchronous memory storage |
| `POST` | `/api/v1/memories/recall` | Semantic memory recall |
| `GET` | `/api/v1/memories/{id}` | Fetch single memory |
| `GET` | `/api/v1/memories/{id}/history` | Version chain |
| `POST` | `/api/v1/workspaces/` | Create workspace |
| `DELETE` | `/api/v1/workspaces/{name}` | Delete workspace |
| `POST` | `/api/v1/epochs/` | Create epoch |
| `POST` | `/api/v1/jump/delta` | Temporal jump delta |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/decay/run` | Manual decay trigger |
| `GET` | `/api/v1/events` | SSE event stream |

### SDKs
- **Python:** `pip install tlcm-client` — see `sdk/python/`
- **TypeScript:** `npm install tlcm-client` — see `sdk/typescript/`
- **LangChain:** Native integration via `integrations/langchain/`
- **Letta/MemGPT:** Archival memory adapter via `integrations/letta/`

---

## Limitations & Future Work
We recognize several boundaries in the v0.5 architecture targeting deployment at scale:
- **Node Sync:** Multi-agent temporal synchronization across distributed TLCM edge nodes requires vector clock synchronization logic.
- **Scale:** Scaling beyond 2M memories per workspace may require Sharded ChromaDB clusters.
- **RL-Driven Reconsolidation:** Next-generation reconsolidation will look into Reinforcement Learning directly mapped to survival heuristics. 
