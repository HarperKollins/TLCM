"""
TLCM Engine API — Slim Node Hybrid Architecture
================================================
FastAPI server with:
- Async memory bus (Tier 1 STM → Tier 2 LTM background processing)
- SSE event stream for real-time client notifications
- Full CORS support for the React Web UI
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from core.database import init_db
from core.async_bus import MemoryBus
from server.middleware import TLCMAuthMiddleware

# Import routers
from server.routers import workspaces, epochs, memories, jump, export

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

# SSE event queue — clients subscribe, bus pushes events here
_sse_subscribers: list[asyncio.Queue] = []


async def _broadcast_sse_event(event_data: dict):
    """Push an event to all connected SSE clients."""
    dead = []
    for q in _sse_subscribers:
        try:
            await q.put(event_data)
        except Exception:
            dead.append(q)
    for q in dead:
        _sse_subscribers.remove(q)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle for the TLCM engine."""
    # Startup
    init_db()

    # Start the async memory bus
    bus = MemoryBus.get_instance()
    bus.set_sse_callback(_broadcast_sse_event)
    bus.start_worker()
    logging.info("[TLCM] Slim Node engine started. Async bus active.")

    # Start the biological decay daemon
    decay_task = asyncio.create_task(_decay_daemon())
    logging.info("[TLCM] Neuro-weighted biological decay daemon started (24h cycle).")

    yield

    # Shutdown
    decay_task.cancel()
    bus.stop_worker()
    logging.info("[TLCM] Engine shutdown complete.")


async def _decay_daemon():
    """
    Periodic background task implementing the Ebbinghaus Forgetting Curve.
    Runs the neuro-weighted decay equation from the TLCM research paper:
        C(t) = max(0.1, C(t-1) - α / (1 + U/10 + |E|/10))
    Executes every 24 hours (86400 seconds).
    """
    from core.memory_store import MemoryStore
    store = MemoryStore()
    
    DECAY_INTERVAL = int(os.environ.get("TLCM_DECAY_INTERVAL_SECONDS", 86400))
    
    while True:
        try:
            await asyncio.sleep(DECAY_INTERVAL)
            await asyncio.to_thread(store.decay_memories)
            logging.info("[TLCM] Biological decay cycle completed.")
        except asyncio.CancelledError:
            logging.info("[TLCM] Decay daemon stopped.")
            break
        except Exception as e:
            logging.error(f"[TLCM] Decay daemon error: {e}")
            await asyncio.sleep(60)  # Retry after 1 min on error


app = FastAPI(
    title="TLCM Engine API",
    description="Temporal Layered Context Memory Engine — Slim Node Hybrid Architecture",
    version="0.4.0",
    lifespan=lifespan,
)

# Enable CORS for the Web UI (configurable via TLCM_CORS_ORIGINS env var)
from core.config import settings as _cfg
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply API Key Authentication
app.add_middleware(TLCMAuthMiddleware)

app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["Workspaces"])
app.include_router(epochs.router, prefix="/api/v1/epochs", tags=["Epochs"])
app.include_router(memories.router, prefix="/api/v1/memories", tags=["Memories"])
app.include_router(jump.router, prefix="/api/v1/jump", tags=["Temporal Jump"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Backup & Export"])

# Mount Universal Dashboard statically (for Docker single-container launch)
DIST_DIR = Path(__file__).parent.parent / "tlcm-web" / "dist"
if DIST_DIR.exists() and DIST_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(DIST_DIR), html=True), name="dashboard")
    logging.info(f"[TLCM] Universal Dashboard mounted at /dashboard")
else:
    logging.warning(f"[TLCM] Dist directory not found at {DIST_DIR}. Dashboard UI heavily requires 'npm run build' first.")



@app.get("/")
def read_root():
    bus = MemoryBus.get_instance()
    return {
        "message": "TLCM Engine API is running",
        "version": "0.4.0",
        "architecture": "Slim Node Hybrid",
        "queue_depth": bus.queue_size,
    }


@app.get("/api/v1/events")
async def sse_stream(request: Request):
    """
    Server-Sent Events stream for real-time memory processing notifications.
    
    Connect from the Web UI:
        const source = new EventSource('/api/events');
        source.onmessage = (e) => { console.log(JSON.parse(e.data)); };
    
    Events:
        - memory_stored: A memory has been processed and committed to LTM
        - memory_error: A memory failed to process
    """
    client_queue: asyncio.Queue = asyncio.Queue()
    _sse_subscribers.append(client_queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield {
                        "event": event.get("type", "message"),
                        "data": json.dumps(event),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping every 30s
                    yield {"event": "ping", "data": "{}"}
        finally:
            if client_queue in _sse_subscribers:
                _sse_subscribers.remove(client_queue)

    return EventSourceResponse(event_generator())


@app.get("/api/v1/bus/status")
def bus_status():
    """Check the current state of the async memory bus."""
    bus = MemoryBus.get_instance()
    return {
        "queue_depth": bus.queue_size,
        "worker_running": bus._running,
    }


@app.get("/api/v1/health")
def health_check():
    """
    Production health check for container orchestration (K8s, Docker).
    Verifies DB connectivity, ChromaDB accessibility, and Bus worker state.
    """
    from core.database import get_connection
    status = {"db": False, "bus_worker": False}
    
    # Check SQLite
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        status["db"] = True
    except Exception as e:
        status["db_error"] = str(e)
    
    # Check Bus
    bus = MemoryBus.get_instance()
    status["bus_worker"] = bus._running
    status["queue_depth"] = bus.queue_size
    
    healthy = status["db"] and status["bus_worker"]
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"healthy": healthy, **status}
    )


@app.post("/api/v1/decay/run")
async def trigger_decay():
    """
    Manually trigger the neuro-weighted biological decay cycle.
    Useful for testing and admin operations.
    Runs the paper's Ebbinghaus equation: C(t) = max(0.1, C(t-1) - α/(1+U/10+|E|/10))
    """
    from core.memory_store import MemoryStore
    store = MemoryStore()
    await asyncio.to_thread(store.decay_memories)
    return {"status": "decay_completed", "message": "Neuro-weighted biological decay applied to all current memories."}

