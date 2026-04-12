from fastapi import APIRouter, HTTPException
from core.memory_store import MemoryStore
from core.workspace import WorkspaceManager
from core.epoch import EpochManager
from server.models import MemoryStoreReq, MemoryUpdateReq, MemoryRecallReq

router = APIRouter()
memory = MemoryStore()
ws_mgr = WorkspaceManager()
epoch_mgr = EpochManager()

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
