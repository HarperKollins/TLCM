"""
TLCM Memory Router — Slim Node Hybrid Architecture
===================================================
The /remember endpoint is now ASYNC:
  - Returns 202 Accepted instantly with a temp_id
  - Background worker processes via Gemini → SQLite → ChromaDB
  - Client receives completion via SSE at /api/events

All other endpoints (recall, update, history) remain synchronous
as they read from committed DB state.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from core.async_bus import MemoryBus
from server.models import MemoryStoreReq, MemoryUpdateReq, MemoryRecallReq

router = APIRouter()
memory = MemoryStore()
ws_mgr = WorkspaceManager()
epoch_mgr = EpochManager()


@router.post("/remember")
async def store_memory(req: MemoryStoreReq):
    """
    Enqueue a memory for async processing (Tier 1 STM → Tier 2 LTM).
    Returns 202 Accepted immediately with a temp_id.
    Listen on /api/events SSE for the completion notification.
    """
    try:
        bus = MemoryBus.get_instance()
        temp_id = await bus.enqueue(
            content=req.content,
            workspace_name=req.workspace,
            epoch_name=req.epoch,
            source=req.source or "user_stated",
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued",
                "temp_id": temp_id,
                "message": "Memory accepted for processing. Listen on /api/events for completion.",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{temp_id}")
def get_memory_status(temp_id: str):
    """
    Poll checking the processing status of a memory.
    Useful for clients that cannot connect to the SSE event stream.
    """
    bus = MemoryBus.get_instance()
    status_data = bus.get_status(temp_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Memory temp_id not found or expired.")
    return status_data


@router.post("/remember/sync")
def store_memory_sync(req: MemoryStoreReq):
    """
    Synchronous fallback — commits memory directly (skips async bus).
    Use for CLI, tests, or when you need the memory_id immediately.
    """
    try:
        return memory.remember(
            content=req.content,
            workspace_name=req.workspace,
            epoch_name=req.epoch,
            source=req.source
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recall")
def recall_memory(req: MemoryRecallReq):
    try:
        return memory.recall(
            query=req.query,
            workspace_name=req.workspace,
            epoch_name=req.epoch,
            limit=req.limit
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{memory_id}")
def update_memory(memory_id: str, req: MemoryUpdateReq):
    try:
        return memory.update(
            memory_id=memory_id,
            new_content=req.new_content,
            reason=req.reason,
            workspace_name=req.workspace
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{memory_id}/history")
def get_memory_history(memory_id: str):
    chain = memory.get_version_history(memory_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Memory not found")
    return chain


@router.get("/workspace/{workspace_name}/epoch/{epoch_name}")
def get_epoch_memories(workspace_name: str, epoch_name: str):
    ws = ws_mgr.get(workspace_name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    ep = epoch_mgr.get_by_name(ws["id"], epoch_name)
    if not ep:
        raise HTTPException(status_code=404, detail="Epoch not found")
        
    mems = memory.recall_epoch_state(ws["id"], ep["id"])
    return mems
