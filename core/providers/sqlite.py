"""
SQLiteProvider — Relational Store Implementation (complete)
============================================================
Implements RelationalStoreProvider using the existing SQLite schema.
Provides full get_memory_chain() using the recursive version-walking
logic that mirrors the PostgreSQL recursive CTE.
"""

from typing import Dict, Any, List
from ..interfaces import RelationalStoreProvider
from ..database import get_connection
import logging

logger = logging.getLogger("tlcm.sqlite_provider")


class SQLiteProvider(RelationalStoreProvider):
    """Relational store backed by SQLite — the default production backend."""

    def save_memory(self, memory_data: Dict[str, Any]):
        """Persist a fully-formed memory dict to the memories table."""
        conn = get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO memories
                   (id, workspace_id, epoch_id, content, version, parent_id, source, tags,
                    emotional_valence, urgency_score, semantic_impact,
                    reconsolidation_flag, is_current, confidence, update_reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    memory_data["id"],
                    memory_data["workspace_id"],
                    memory_data["epoch_id"],
                    memory_data["content"],
                    memory_data.get("version", 1),
                    memory_data.get("parent_id"),
                    memory_data.get("source", "user_stated"),
                    memory_data.get("tags", "[]"),
                    memory_data.get("emotional_valence", 0),
                    memory_data.get("urgency_score", 5),
                    memory_data.get("semantic_impact", 5),
                    memory_data.get("reconsolidation_flag", "append"),
                    memory_data.get("is_current", 1),
                    memory_data.get("confidence", 1.0),
                    memory_data.get("update_reason"),
                )
            )
            conn.commit()
        finally:
            conn.close()

    def get_memory_chain(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve the complete version chain of a memory by walking the
        parent_id links — equivalent to the PostgreSQL recursive CTE.
        Returns the chain ordered oldest → newest.
        """
        conn = get_connection()
        try:
            # Find the root of this chain (the memory with no parent that
            # is an ancestor of memory_id)
            root_id = self._find_root(conn, memory_id)

            # Walk forward from root collecting all versions
            chain = []
            current_id = root_id
            visited = set()

            while current_id and current_id not in visited:
                visited.add(current_id)
                row = conn.execute(
                    "SELECT * FROM memories WHERE id = ?", (current_id,)
                ).fetchone()
                if not row:
                    break
                chain.append(dict(row))

                # Find the next version (child of current)
                child = conn.execute(
                    "SELECT id FROM memories WHERE parent_id = ? ORDER BY version ASC LIMIT 1",
                    (current_id,)
                ).fetchone()
                current_id = child["id"] if child else None

            return chain
        finally:
            conn.close()

    def _find_root(self, conn, memory_id: str) -> str:
        """Walk up parent_id links to find the root of the version chain."""
        current_id = memory_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            row = conn.execute(
                "SELECT parent_id FROM memories WHERE id = ?", (current_id,)
            ).fetchone()
            if not row or not row["parent_id"]:
                return current_id
            current_id = row["parent_id"]

        return current_id
