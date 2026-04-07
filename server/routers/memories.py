from fastapi import APIRouter, HTTPException
from core.memory_store import MemoryStore
from server.models import MemoryStoreReq, MemoryUpdateReq, MemoryRecallReq

router = APIRouter()
memory = MemoryStore()

@router.post("/remember")
def store_memory(req: MemoryStoreReq):
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
