"""
TLCM Engine API — Slim Node Hybrid Architecture
================================================
FastAPI server with:
- Async memory bus (Tier 1 STM → Tier 2 LTM background processing)
- SSE event stream for real-time client notifications
- Full CORS support for the React Web UI
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from core.database import init_db
from core.async_bus import MemoryBus

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

    yield

    # Shutdown
    bus.stop_worker()
    logging.info("[TLCM] Engine shutdown complete.")


app = FastAPI(
    title="TLCM Engine API",
    description="Temporal Layered Context Memory Engine — Slim Node Hybrid Architecture",
    version="0.4.0",
    lifespan=lifespan,
)

# Enable CORS for the Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(epochs.router, prefix="/api/epochs", tags=["Epochs"])
app.include_router(memories.router, prefix="/api/memories", tags=["Memories"])
app.include_router(jump.router, prefix="/api/jump", tags=["Temporal Jump"])
app.include_router(export.router, prefix="/api/export", tags=["Backup & Export"])


@app.get("/")
def read_root():
    bus = MemoryBus.get_instance()
    return {
        "message": "TLCM Engine API is running",
        "version": "0.4.0",
        "architecture": "Slim Node Hybrid",
        "queue_depth": bus.queue_size,
    }


@app.get("/api/events")
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


@app.get("/api/bus/status")
def bus_status():
    """Check the current state of the async memory bus."""
    bus = MemoryBus.get_instance()
    return {
        "queue_depth": bus.queue_size,
        "worker_running": bus._running,
    }
