"""
TLCM Adapter for MemPalace-style Evaluation
Bridges MemPalace's session-based adding/retrieval to TLCM's
Epoch-based Workspace architecture.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure core modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ["TLCM_TEST_MODE"] = "1"

from core.database import init_db
from core.memory_store import MemoryStore
from core.epoch import EpochManager
from core.workspace import WorkspaceManager


class TLCMMemoryAdapter:
    """
    Adapter bridging MemPalace's session-based adding/retrieval
    to TLCM's Epoch-based Workspace architecture.

    MemPalace sessions map to TLCM epochs.
    MemPalace memories map to TLCM versioned memories.
    """

    def __init__(self, workspace_name: str):
        self.workspace_name = workspace_name
        self.memory_store = MemoryStore()
        self.epoch_manager = EpochManager()
        self.workspace_manager = WorkspaceManager()
        self.current_session_id = None

        # Ensure DB is initialized
        init_db()

        # Ensure workspace exists
        self.workspace = self.workspace_manager.get_or_create(
            workspace_name, f"Eval workspace: {workspace_name}"
        )

    def start_session(self, session_id: str):
        """Start a new session (maps to creating a TLCM epoch)."""
        self.current_session_id = session_id
        # EpochManager.create() takes (workspace_id, name, description)
        existing = self.epoch_manager.get_by_name(self.workspace["id"], session_id)
        if not existing:
            self.epoch_manager.create(
                workspace_id=self.workspace["id"],
                name=session_id,
                description=f"Eval session {session_id}",
            )

    def add(self, text: str, tags: List[str] = None):
        """
        Add a memory to the current session.
        MemoryStore.remember() signature: (content, workspace_name, epoch_name)
        """
        if not self.current_session_id:
            raise ValueError("Must start a session before adding memories.")

        result = self.memory_store.remember(
            content=text,
            workspace_name=self.workspace_name,
            epoch_name=self.current_session_id,
        )
        return result

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top_k memories related to the query across the workspace.
        MemoryStore.recall() signature: (query, workspace_name, epoch_name, limit)
        """
        memories = self.memory_store.recall(
            query=query,
            workspace_name=self.workspace_name,
            limit=top_k,
        )
        # Format for eval: include epoch info
        results = []
        from core.database import get_connection

        conn = get_connection()
        for m in memories:
            epoch_row = conn.execute(
                "SELECT name FROM epochs WHERE id = ?", (m.get("epoch_id", ""),)
            ).fetchone()
            results.append(
                {
                    "content": m["content"],
                    "epoch": epoch_row["name"] if epoch_row else "unknown",
                    "confidence": m.get("confidence", 1.0),
                    "version": m.get("version", 1),
                }
            )
        conn.close()
        return results

    def temporal_jump(self, from_session: str, to_session: str) -> str:
        """Perform a TLCM temporal jump between two sessions/epochs."""
        from core.temporal_jump import TemporalJumpEngine

        jump_engine = TemporalJumpEngine()
        return jump_engine.jump(self.workspace_name, from_session, to_session)
