from fastapi import APIRouter, HTTPException
from core.workspace import WorkspaceManager
from server.models import WorkspaceCreate, WorkspaceLink

router = APIRouter()
workspaces = WorkspaceManager()

@router.get("/")
def list_workspaces():
    return workspaces.list_all()

@router.post("/")
def create_workspace(req: WorkspaceCreate):
    try:
        return workspaces.create(req.name, req.description)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{name}")
def get_workspace(name: str):
    ws = workspaces.get(name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@router.post("/link")
def link_workspaces(req: WorkspaceLink):
    try:
        return workspaces.authorize_link(req.source, req.target, req.reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{name}/links")
def get_links(name: str):
    return workspaces.get_authorized_links(name)


@router.delete("/{name}")
def delete_workspace(name: str):
    """Soft-delete a workspace — memories are preserved but workspace is archived."""
    from core.database import get_connection
    ws = workspaces.get(name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM workspaces WHERE id=?", (ws["id"],))
        conn.commit()
        return {"status": "deleted", "workspace": name}
    finally:
        conn.close()

