"""
TLCM Memory Store — The Heart of the System
Principle 1: Versioned Memory, Not Overwrite Memory
Principle 4: Embedding-based retrieval (foundation for Temporal Jump)

Every update creates a NEW memory linked to the old one via parent_id.
Old memories are archived, never deleted.
The result: a complete history of everything the AI has ever believed.
"""

import json
from datetime import datetime
from .database import get_connection, new_id
from .workspace import WorkspaceManager
from .epoch import EpochManager
from .embeddings import EmbeddingEngine

workspace_mgr = WorkspaceManager()
epoch_mgr = EpochManager()
embedding_engine = EmbeddingEngine()


class MemoryStore:
    def remember(
        self,
        content: str,
        workspace_name: str,
        epoch_name: str = None,
        source: str = "user_stated",
        tags: list[str] = None,
    ) -> dict:
        """
        Store a new memory in the correct workspace and epoch.
        TLCM Principle: memories are isolated by workspace and tagged with epoch.
        """
        workspace = workspace_mgr.get_or_create(workspace_name)
        if epoch_name:
            epoch = epoch_mgr.get_by_name(workspace["id"], epoch_name)
            if not epoch:
                epoch = epoch_mgr.create(workspace["id"], epoch_name)
        else:
            epoch = epoch_mgr.get_or_create_active(workspace["id"], workspace_name)

        memory_id = new_id()
        conn = get_connection()
        conn.execute(
            """INSERT INTO memories
               (id, workspace_id, epoch_id, content, version, source, tags)
               VALUES (?, ?, ?, ?, 1, ?, ?)""",
            (
                memory_id,
                workspace["id"],
                epoch["id"],
                content,
                source,
                json.dumps(tags or []),
            ),
        )
        conn.commit()
        conn.close()

        # Store embedding for semantic search
        embedding_engine.embed_and_store(
            memory_id=memory_id,
            content=content,
            workspace_name=workspace_name,
            epoch_name=epoch["name"],
        )

        print(f"[Memory] Stored in '{workspace_name}' / '{epoch['name']}'")
        return {"id": memory_id, "workspace": workspace_name, "epoch": epoch["name"]}

    def update(
        self,
        memory_id: str,
        new_content: str,
        reason: str,
        workspace_name: str,
    ) -> dict:
        """
        TLCM Principle 1: Versioned update — NEVER overwrites.
        Creates a new version pointing to the old one. Archives the old.
        The old memory is preserved as historical truth.
        """
        conn = get_connection()

        # Fetch the old memory
        old = conn.execute(
            "SELECT * FROM memories WHERE id = ? AND is_current = 1", (memory_id,)
        ).fetchone()

        if not old:
            conn.close()
            raise ValueError(f"Memory {memory_id} not found or already archived.")

        old = dict(old)

        # Archive the old version
        conn.execute(
            "UPDATE memories SET is_current = 0, archived_at = ? WHERE id = ?",
            (datetime.now().isoformat(), memory_id),
        )

        # Create the new version (linked to the old via parent_id)
        new_id_ = new_id()
        conn.execute(
            """INSERT INTO memories
               (id, workspace_id, epoch_id, content, version, parent_id, update_reason, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'updated')""",
            (
                new_id_,
                old["workspace_id"],
                old["epoch_id"],
                new_content,
                old["version"] + 1,
                memory_id,
                reason,
            ),
        )
        conn.commit()
        conn.close()

        # Update the embedding
        embedding_engine.embed_and_store(
            memory_id=new_id_,
            content=new_content,
            workspace_name=workspace_name,
            epoch_name="",
        )

        print(f"[Memory] Updated to v{old['version'] + 1} — old version preserved.")
        return {
            "new_id": new_id_,
            "old_id": memory_id,
            "version": old["version"] + 1,
            "reason": reason,
        }

    def get_version_history(self, memory_id: str) -> list[dict]:
        """
        Walk the version chain from any memory_id all the way back to v1.
        This is the full temporal arc of a single belief.
        """
        conn = get_connection()
        chain = []
        current_id = memory_id

        # Walk forward to find current if this is an old version
        # First, find the root of this chain
        mem = conn.execute("SELECT * FROM memories WHERE id = ?", (current_id,)).fetchone()
        if not mem:
            conn.close()
            return []

        mem = dict(mem)
        # Trace up to root
        root_id = current_id
        while mem.get("parent_id"):
            root_id = mem["parent_id"]
            mem = dict(conn.execute("SELECT * FROM memories WHERE id = ?", (root_id,)).fetchone())

        # Now walk all the way down via recursive query
        rows = conn.execute(
            """WITH RECURSIVE version_chain(id, content, version, parent_id,
                                             update_reason, source, created_at, archived_at, is_current) AS (
                 SELECT id, content, version, parent_id, update_reason, source, created_at, archived_at, is_current
                 FROM memories WHERE id = ?
                 UNION ALL
                 SELECT m.id, m.content, m.version, m.parent_id, m.update_reason, m.source,
                        m.created_at, m.archived_at, m.is_current
                 FROM memories m
                 JOIN version_chain vc ON m.parent_id = vc.id
               )
               SELECT * FROM version_chain ORDER BY version ASC""",
            (root_id,),
        ).fetchall()

        conn.close()
        return [dict(r) for r in rows]

    def recall(
        self,
        query: str,
        workspace_name: str,
        epoch_name: str = None,
        limit: int = 5,
        current_only: bool = True,
    ) -> list[dict]:
        """
        Semantic search within a SPECIFIC workspace (and optionally epoch).
        TLCM Principle: isolated retrieval — never crosses workspace boundaries.
        """
        # Semantic search via embeddings
        semantic_results = embedding_engine.search(
            query=query,
            workspace_name=workspace_name,
            epoch_name=epoch_name,
            limit=limit * 2,  # Over-fetch, then filter
        )

        if not semantic_results:
            return []

        # Enrich with SQLite metadata
        conn = get_connection()
        enriched = []
        for result in semantic_results[:limit]:
            mem = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (result["memory_id"],)
            ).fetchone()
            if mem:
                m = dict(mem)
                if current_only and not m["is_current"]:
                    continue
                m["relevance_score"] = result["score"]
                enriched.append(m)
        conn.close()
        return enriched

    def recall_epoch_state(self, workspace_id: str, epoch_id: str) -> list[dict]:
        """
        Get ALL current memories from a specific epoch.
        Used by the temporal jump engine to reconstruct a past world-state.
        """
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM memories WHERE workspace_id = ? AND epoch_id = ? AND is_current = 1 "
            "ORDER BY created_at ASC",
            (workspace_id, epoch_id),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
