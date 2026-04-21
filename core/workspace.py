"""
TLCM Workspace Manager
Principle 3: Context Workspace Isolation
Each workspace is a fully siloed cognitive environment.
Memories never bleed between workspaces unless the user explicitly authorizes it.
"""

from datetime import datetime
from .database import get_connection, new_id


class WorkspaceManager:
    def create(self, name: str, description: str = "") -> dict:
        """Create a new isolated cognitive workspace."""
        conn = get_connection()
        try:
            workspace_id = new_id()
            conn.execute(
                "INSERT INTO workspaces (id, name, description) VALUES (?, ?, ?)",
                (workspace_id, name, description),
            )
            conn.commit()
            print(f"[Workspace] Created: '{name}' (id={workspace_id[:8]}...)")
            return {"id": workspace_id, "name": name}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get(self, name: str) -> dict | None:
        """Get workspace by name."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_or_create(self, name: str, description: str = "") -> dict:
        """Get existing workspace or create a new one."""
        existing = self.get(name)
        if existing:
            return existing
        return self.create(name, description)

    def list_all(self) -> list[dict]:
        """List all workspaces."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT w.*, COUNT(m.id) as memory_count "
                "FROM workspaces w "
                "LEFT JOIN memories m ON m.workspace_id = w.id AND m.is_current = 1 "
                "GROUP BY w.id"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def authorize_link(self, source_name: str, target_name: str, reason: str) -> dict:
        """
        Explicitly authorize a cross-workspace link.
        TLCM Principle: connections between workspaces are DELIBERATE decisions, 
        not automatic associations.
        """
        conn = get_connection()
        source = self.get(source_name)
        target = self.get(target_name)
        if not source or not target:
            raise ValueError("One or both workspaces not found.")
        
        link_id = new_id()
        try:
            conn.execute(
                "INSERT INTO cross_workspace_links (id, source_workspace_id, target_workspace_id, link_reason) "
                "VALUES (?, ?, ?, ?)",
                (link_id, source["id"], target["id"], reason),
            )
            conn.commit()
            print(f"[Workspace] Authorized link: '{source_name}' <-> '{target_name}'")
            return {"source": source_name, "target": target_name, "reason": reason}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_authorized_links(self, workspace_name: str) -> list[dict]:
        """Get all workspaces this workspace is authorized to connect with."""
        conn = get_connection()
        workspace = self.get(workspace_name)
        if not workspace:
            return []
        try:
            rows = conn.execute(
                """
                SELECT w.name, l.link_reason, l.created_at
                FROM cross_workspace_links l
                JOIN workspaces w ON (
                    CASE WHEN l.source_workspace_id = ? THEN l.target_workspace_id
                         ELSE l.source_workspace_id END = w.id
                )
                WHERE l.source_workspace_id = ? OR l.target_workspace_id = ?
                """,
                (workspace["id"], workspace["id"], workspace["id"]),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
