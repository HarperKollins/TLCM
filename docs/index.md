# TLCM Engine

> *"Current AI memory systems treat memory as a filing cabinet: store, retrieve, overwrite. The human brain treats memory as a living architecture: versioned, temporally indexed, emotionally weighted, and spatially separated by context."* — **Collins Somtochukwu (Harper Kollins)**

**TLCM (Temporal Layered Context Memory)** is a neuro-inspired AI memory engine built to solve the structural failures of current Large Language Model memory architectures. Instead of relying on sprawling, chaotic vector dumps or flat un-versioned updates, TLCM implements time and context as fundamental, first-class architectural dimensions.

---

## 4 Principles of Operation

1. **Versioned Memory (No Overwrite):** Memories are never deleted. When a fact updates, a new version is created containing a pointer to the previous version. The system operates as a **Git repository for AI beliefs**.
2. **Temporal Epoch Tagging:** Every fact belongs to a contextual epoch.
3. **Context Workspace Isolation:** Cognitive workspaces are mathematically isolated.
4. **The Temporal Jump:** Calculates the pure Python mathematical delta to reconstruct a complete world-state using the preserved memory graphs.

**(To read more about the formal Neuroscience & Biology logic, read the `README.md` at the root of the repository.)**

---

## Quickstart Guide

This guide will show you how to securely launch the TLCM Engine locally or via Docker.

### 1. Installation

TLCM is a headless Python engine with REST interfaces.
```bash
git clone https://github.com/your-org/tlcm-engine.git
cd tlcm-engine
pip install -e .
```

### 2. Configuration (`.env`)

At the root of your project, create a `.env` file for the LLM Judge backend.
```env
COGNITION_BACKEND=gemini
GEMINI_API_KEY=your_key_here
# Optional: Set this to secure your Engine endpoints
TLCM_API_KEY=super_secret_key
```

### 3. Running the Server

Start the Slim Node architecture which automatically launches the asynchronous STM ingestion bus and API REST endpoints.
```bash
python -m uvicorn server.main:app --reload --port 8000
```
Check `http://localhost:8000/docs` to see the FastAPI Swagger UI and all `/api/v1/` endpoints.

### SDK Usage
If you are integrating TLCM into a web application, check whether you are using the Node.js/TypeScript SDK or Python SDK.
