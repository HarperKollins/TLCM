from fastapi import APIRouter, HTTPException
from core.epoch import EpochManager
from core.workspace import WorkspaceManager
from server.models import EpochCreate

router = APIRouter()
epochs = EpochManager()
workspaces = WorkspaceManager()

@router.get("/{workspace_name}")
def list_epochs(workspace_name: str):
    ws = workspaces.get(workspace_name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return epochs.list_epochs(ws["id"])

@router.post("/")
def create_epoch(req: EpochCreate):
    ws = workspaces.get(req.workspace)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        return epochs.create(
            workspace_id=ws["id"],
            name=req.name,
            description=req.description,
            start_date=req.start_date,
            end_date=req.end_date
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{workspace_name}/{epoch_name}/close")
def close_epoch(workspace_name: str, epoch_name: str):
    ws = workspaces.get(workspace_name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        epochs.close_epoch(ws["id"], epoch_name)
        return {"status": "success", "message": f"Epoch {epoch_name} closed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
