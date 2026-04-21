"""
TLCM Epoch Manager
Principle 2: Temporal Epoch Tagging
Every memory belongs to a named phase of time.
"Pre-launch", "Post-Ella", "Blue Love development" — each is a distinct contextual identity.
Epochs are preserved FOREVER, even after they end.
"""

from .database import get_connection, new_id


class EpochManager:
    def create(self, workspace_id: str, name: str, description: str = "",
               start_date: str = None, end_date: str = None) -> dict:
        """Create a new temporal epoch within a workspace."""
        conn = get_connection()
        try:
            epoch_id = new_id()
            conn.execute(
                """INSERT INTO epochs (id, workspace_id, name, description, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (epoch_id, workspace_id, name, description, start_date, end_date),
            )
            conn.commit()
            print(f"[Epoch] Created: '{name}' (id={epoch_id[:8]}...)")
            return {"id": epoch_id, "name": name, "workspace_id": workspace_id}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_active(self, workspace_id: str) -> dict | None:
        """Get the currently active (open) epoch for a workspace."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM epochs WHERE workspace_id = ? AND is_active = 1 "
                "ORDER BY created_at DESC LIMIT 1",
                (workspace_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_by_name(self, workspace_id: str, name: str) -> dict | None:
        """Get a specific epoch by name within a workspace."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM epochs WHERE workspace_id = ? AND name = ?",
                (workspace_id, name),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_or_create_active(self, workspace_id: str, workspace_name: str) -> dict:
        """Get active epoch or create a default one if none exists."""
        active = self.get_active(workspace_id)
        if active:
            return active
        # Auto-create a default epoch
        return self.create(
            workspace_id=workspace_id,
            name=f"Default — {workspace_name}",
            description="Auto-created default epoch",
        )

    def close_epoch(self, workspace_id: str, epoch_name: str, end_date: str = None) -> bool:
        """
        Close an epoch (mark as no longer active).
        The epoch and ALL its memories are PRESERVED — they just get an end date.
        This is the TLCM equivalent of closing a lifetime period.
        """
        from datetime import datetime
        conn = get_connection()
        try:
            end = end_date or datetime.now().isoformat()
            conn.execute(
                "UPDATE epochs SET is_active = 0, end_date = ? WHERE workspace_id = ? AND name = ?",
                (end, workspace_id, epoch_name),
            )
            conn.commit()
            print(f"[Epoch] Closed: '{epoch_name}' — memories preserved, epoch archived.")
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def list_epochs(self, workspace_id: str) -> list[dict]:
        """List all epochs for a workspace (including closed ones)."""
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT e.*, COUNT(m.id) as memory_count
                   FROM epochs e
                   LEFT JOIN memories m ON m.epoch_id = e.id AND m.is_current = 1
                   WHERE e.workspace_id = ?
                   GROUP BY e.id
                   ORDER BY e.created_at ASC""",
                (workspace_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
