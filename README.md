# Temporal Layered Context Memory (TLCM) Engine

> *"Current AI memory systems treat memory as a filing cabinet: store, retrieve, overwrite. The human brain treats memory as a living architecture: versioned, temporally indexed, emotionally weighted, and spatially separated by context."* — **Collins Somtochukwu (Harper Kollins)**

**TLCM** is a neuro-inspired AI memory engine built to solve the structural failures of current Large Language Model memory architectures. Instead of relying on sprawling, chaotic vector dumps or flat un-versioned updates, TLCM implements time and context as fundamental, first-class architectural dimensions.

## 🧠 The Structural Problem
The TLCM Engine solves three exact failure modes present in modern LLMs (MemGPT, ChatGPT, standard RAG):

1. **The Snapshot Problem:** AI systems store facts as static photographs. When reality updates, the photograph becomes fiction.
2. **The Overwrite Problem:** When current AI *does* update, it destroys the old memory. It loses the evolutionary arc. It cannot answer: "How did we get from what we believed in 2024 to what we believe in 2026?"
3. **The Context Bleed Problem:** AIs process all active goals in one flat namespace. Your startup data blends with your personal relationship data, creating unauthorized, hallucinatory connections.

## 🛠️ How TLCM Solves It (The 4 Principles)

TLCM maps cognitive neuroscience directly to software engineering:

### 1. Versioned Memory (No Overwrite)
Powered by specialized `SQLite` version-chain logic, **memories are never deleted**. When a fact updates, a new version is created containing a pointer to the previous version and a reason for the shift. The system operates as a Git repository for AI beliefs.

### 2. Temporal Epoch Tagging
Inspired by autobiographical "lifetime periods," every fact belongs to a contextual epoch (e.g., *"Pre-Launch Phase"*, *"Blue Love Development"*). When an epoch closes, it is archived but mathematically preserved.

### 3. Context Workspace Isolation
Powered by heavily segregated `ChromaDB` semantic namespaces, cognitive workspaces are strictly isolated. A query about your screenplay is mathematically incapable of retrieving vectors regarding your AI startup unless you authorize an explicit cross-workspace link.

### 4. The Temporal Jump (Neural Time Travel)
When asked to evaluate the past, TLCM reconstructs a complete world-state using the preserved memory graphs. Powered locally by `Ollama` (`gemma2:2b` / `llama3.2`), it forces the LLM to reason *from within* the past state, and map the explicit delta to the present.

---

## 🏗️ Architecture Stack
Designed explicitly to run fully locally without cloud API dependencies on moderate hardware (Intel i5 CPU).

- **Core Storage:** `SQLite` (Strict relational version tracking, Epoch indexing)
- **Vector Engine:** `ChromaDB` (Isolated semantic embedding per workspace)
- **Inference Pipeline:** `Ollama` (Local, privacy-first AI embedding and generation)
- **Service Layer (Phase 2):** `FastAPI` + `Uvicorn` (REST mapping of neuro-principles)
- **Visual Mind UI (Phase 3):** `React` + `Vite` (Dynamic tracking of chronological workspaces)

---

## 🚀 Quick Start Guide

### 1. The Terminal CLI
Access the original Python engine directly from your console:

```bash
cd tlcm-engine

# Initialize a workspace
python tlcm.py workspace create "HK AI" --desc "The AI startup"

# Create a temporal boundary
python tlcm.py epoch create "HK AI" "Pre-launch"

# Store an immutable memory 
python tlcm.py remember --workspace "HK AI" "We currently have 0 users."

# Jump back in time
python tlcm.py jump --workspace "HK AI" --from "Pre-launch" --to "Current"

# Enter the neuro-shell
python tlcm.py chat --workspace "HK AI"
```

### 2. The API Server
Run the FastAPI daemon to allow external apps/agents to utilize the memory engine:
```bash
python -m uvicorn server.main:app --reload --port 8000
```
Endpoints:
- `GET /api/workspaces`
- `POST /api/memories/remember`
- `GET /api/memories/{id}/history` (Fetches the evolutionary arc of a thought)
- `POST /api/jump`

### 3. The Visual Dashboard
Interact physically with the timelines and separated context panes:
```bash
cd tlcm-web
npm run dev
```

---

## 📖 Theoretical Origins
This architecture implements the specifications proposed in **"The Memory Gap: A Thesis on Temporal, Layered, and Context-Isolated Memory for AI Systems"** by Collins Somtochukwu (April 2026). It utilizes the neuro-mathematical models of Endel Tulving's episodic contiguity and the validated Temporal Context Model (TCM). 

*(No facts overwrite. No contexts bleed. Everything is time.)*
