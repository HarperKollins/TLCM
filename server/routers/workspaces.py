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
        # Cascade delete explicitly to avoid FOREIGN KEY constraint failure
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM temporal_jumps WHERE workspace_id=?", (ws["id"],))
        conn.execute("DELETE FROM cross_workspace_links WHERE source_workspace_id=? OR target_workspace_id=?", (ws["id"], ws["id"]))
        conn.execute("DELETE FROM memories WHERE workspace_id=?", (ws["id"],))
        conn.execute("DELETE FROM epochs WHERE workspace_id=?", (ws["id"],))
        conn.execute("DELETE FROM workspaces WHERE id=?", (ws["id"],))
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        return {"status": "deleted", "workspace": name}
    finally:
        conn.close()

