"""
TLCM Memory Store — The Heart of the System
Principle 1: Versioned Memory, Not Overwrite Memory
Principle 4: Embedding-based retrieval (foundation for Temporal Jump)

Every update creates a NEW memory linked to the old one via parent_id.
Old memories are archived, never deleted.
The result: a complete history of everything the AI has ever believed.

v0.4 UPGRADE: Slim Node Hybrid Architecture
- remember() now enqueues to the async bus (instant return)
- commit_memory() is the actual DB+Chroma write (called by background worker)
- recall() uses neuro-weighted decay (emotional_valence + urgency affect confidence)
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
        
        In synchronous mode (CLI, tests, direct calls): commits immediately.
        In async mode (FastAPI): the router enqueues via the bus instead.
        """
        return self.commit_memory(
            content=content,
            workspace_name=workspace_name,
            epoch_name=epoch_name,
            source=source,
            tags=tags,
        )

    def commit_memory(
        self,
        content: str,
        workspace_name: str,
        epoch_name: str = None,
        source: str = "user_stated",
        tags: list[str] = None,
        emotional_valence: int = 0,
        urgency_score: int = 5,
        semantic_impact: int = 5,
        reconsolidation_flag: str = "append",
    ) -> dict:
        """
        The actual synchronous commit to SQLite + ChromaDB.
        Called directly by remember() in sync mode, or by the async bus worker.
        
        Neuro-weighted fields are populated by the Gemini Judge when called
        via the async bus. In direct/sync mode, defaults are used.
        """
        workspace = workspace_mgr.get_or_create(workspace_name)
        if epoch_name:
            epoch = epoch_mgr.get_by_name(workspace["id"], epoch_name)
            if not epoch:
                epoch = epoch_mgr.create(workspace["id"], epoch_name)
        else:
            epoch = epoch_mgr.get_or_create_active(workspace["id"], workspace_name)

        # Pre-check for local fallback (strengthen) or Core Contradictions (surgery)
        if reconsolidation_flag in ["strengthen", "contradicts_core"]:
            conflicting = self.recall(
                query=content,
                workspace_name=workspace_name,
                epoch_name=epoch["name"],
                limit=1,
                current_only=False # Surgical strike: Search the past too
            )
            
            if conflicting:
                target = conflicting[0]
                target_id = target["id"]
                relevance = target.get("relevance_score", 0)
                
                # Local Fallback (Strengthen/Redundant Bypass)
                if reconsolidation_flag == "strengthen" and relevance > 0.8:
                    conn = get_connection()
                    try:
                        now_iso = datetime.now().isoformat()
                        conn.execute(
                            "UPDATE memories SET confidence = MIN(1.0, confidence + 0.1), recall_count = recall_count + 1, last_recalled_at = ? WHERE id = ?",
                            (now_iso, target_id)
                        )
                        conn.commit()
                        print(f"[Memory Store] 'strengthen' fallback triggered for {target_id[:8]} - skipping duplicate.")
                        return {"id": target_id, "workspace": workspace_name, "epoch": epoch["name"], "status": "strengthened"}
                    finally:
                        conn.close()

                # True Graph Surgery
                elif reconsolidation_flag == "contradicts_core" and relevance > 0.4:
                    print(f"[Surgery] Resolving contradiction natively via explicit graph branch on {target_id[:8]}")
                    return self.update(
                        memory_id=target_id,
                        new_content=content,
                        reason="Resolving core contradiction natively via graph surgery",
                        workspace_name=workspace_name,
                        emotional_valence=emotional_valence,
                        urgency_score=urgency_score,
                        semantic_impact=semantic_impact,
                        reconsolidation_flag=reconsolidation_flag
                    )

        memory_id = new_id()
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO memories
                   (id, workspace_id, epoch_id, content, version, source, tags,
                    emotional_valence, urgency_score, semantic_impact, reconsolidation_flag)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
                (
                    memory_id,
                    workspace["id"],
                    epoch["id"],
                    content,
                    source,
                    json.dumps(tags or []),
                    emotional_valence,
                    urgency_score,
                    semantic_impact,
                    reconsolidation_flag,
                ),
            )
            conn.commit()
            # Store embedding for semantic search
            embedding_engine.embed_and_store(
                memory_id=memory_id,
                content=content,
                workspace_name=workspace_name,
                epoch_name=epoch["name"],
            )

            conn.commit()
            print(f"[Memory] Stored in '{workspace_name}' / '{epoch['name']}' "
                  f"(emotion={emotional_valence}, urgency={urgency_score}, "
                  f"impact={semantic_impact}, recon={reconsolidation_flag})")
            return {"id": memory_id, "workspace": workspace_name, "epoch": epoch["name"]}
        except Exception as e:
            conn.rollback()
            print(f"[Memory Store] ERR: Memory isolated storage rolled back due to error: {e}")
            raise e
        finally:
            conn.close()

    def update(
        self,
        memory_id: str,
        new_content: str,
        reason: str,
        workspace_name: str,
        emotional_valence: int = None,
        urgency_score: int = None,
        semantic_impact: int = None,
        reconsolidation_flag: str = None
    ) -> dict:
        """
        TLCM Principle 1: Versioned update — NEVER overwrites.
        Creates a new version pointing to the old one. Archives the old.
        The old memory is preserved as historical truth.
        """
        conn = get_connection()
        try:
            # Fetch the old memory (can be an archived memory if we are doing timeline surgery!)
            old = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()

            if not old:
                raise ValueError(f"Memory {memory_id} not found.")

            old = dict(old)

            if old["is_current"]:
                # Archive the old version
                conn.execute(
                    "UPDATE memories SET is_current = 0, archived_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), memory_id),
                )
            else:
                # TRUE GRAPH SURGERY: Cascade Orphan
                # We are branching from an archived memory in the past.
                # Therefore, any beliefs downstream from it that were previously current
                # are now on a hallucinated/invalid timeline and must be orphaned.
                now_iso = datetime.now().isoformat()
                conn.execute(
                    """WITH RECURSIVE downstream(id) AS (
                         SELECT id FROM memories WHERE parent_id = ?
                         UNION ALL
                         SELECT m.id FROM memories m JOIN downstream d ON m.parent_id = d.id
                       )
                       UPDATE memories 
                       SET is_current = 0, 
                           confidence = 0.0,
                           reconsolidation_flag = 'orphaned_via_surgery',
                           archived_at = ?
                       WHERE id IN downstream""",
                    (memory_id, now_iso)
                )
                print(f"[Surgery] Cascade Orphan executed on descendants of {memory_id[:8]}")

            # Create the new version (linked to the old via parent_id)
            new_id_ = new_id()
            conn.execute(
                """INSERT INTO memories
                   (id, workspace_id, epoch_id, content, version, parent_id, update_reason, source,
                    emotional_valence, urgency_score, semantic_impact, reconsolidation_flag)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'updated', ?, ?, ?, ?)""",
                (
                    new_id_,
                    old["workspace_id"],
                    old["epoch_id"],
                    new_content,
                    old["version"] + 1,
                    memory_id,
                    reason,
                    emotional_valence if emotional_valence is not None else old.get("emotional_valence", 0),
                    urgency_score if urgency_score is not None else old.get("urgency_score", 5),
                    semantic_impact if semantic_impact is not None else old.get("semantic_impact", 5),
                    reconsolidation_flag if reconsolidation_flag is not None else old.get("reconsolidation_flag", "append"),
                ),
            )

            # Update the embedding
            embedding_engine.embed_and_store(
                memory_id=new_id_,
                content=new_content,
                workspace_name=workspace_name,
                epoch_name="",
            )

            conn.commit()
            print(f"[Memory] Updated to v{old['version'] + 1} — old version preserved.")
            return {
                "new_id": new_id_,
                "old_id": memory_id,
                "version": old["version"] + 1,
                "reason": reason,
            }
        except Exception as e:
            conn.rollback()
            print(f"[Memory Store] ERR: Memory update rolled back due to error: {e}")
            raise e
        finally:
            conn.close()

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
        
        v0.4: Neuro-weighted decay — emotional and urgent memories decay slower.
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

        # Enrich with SQLite metadata and process biological frequency
        conn = get_connection()
        enriched = []
        try:
            now_iso = datetime.now().isoformat()
            for result in semantic_results[:limit]:
                mem = conn.execute(
                    "SELECT * FROM memories WHERE id = ?", (result["memory_id"],)
                ).fetchone()
                if mem:
                    m = dict(mem)
                    if current_only and not m["is_current"]:
                        continue
                    
                    # Neuro-weighted effective confidence
                    # High urgency/emotional memories resist decay
                    raw_confidence = m.get("confidence", 1.0)
                    urgency = m.get("urgency_score", 5)
                    emotion = abs(m.get("emotional_valence", 0))
                    neuro_boost = 1.0 + (urgency / 20.0) + (emotion / 20.0)
                    m["effective_confidence"] = min(1.0, raw_confidence * neuro_boost)
                    
                    m["relevance_score"] = result["score"]
                    enriched.append(m)
                    
                    # Biological Decay: Increase recall frequency and score when retrieved
                    conn.execute(
                        """UPDATE memories 
                           SET recall_count = recall_count + 1, 
                               last_recalled_at = ?,
                               confidence = MIN(1.0, confidence + 0.05) 
                           WHERE id = ?""",
                        (now_iso, m["id"])
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[Memory Store] ERR: Recall persistence failed: {e}")
        finally:
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

    def decay_memories(self):
        """
        Biological Decay: Automatically lowers confidence of old memories.
        Should be called periodically (e.g. daily cron job or during startup).
        
        v0.4: Neuro-weighted decay — urgent/emotional memories decay 2-5x slower.
        Decay rate = base_decay / neuro_boost_factor
        """
        conn = get_connection()
        try:
            # Standard decay for low-urgency, neutral memories
            conn.execute(
                """
                UPDATE memories 
                SET confidence = MAX(0.1, confidence - (0.05 / (1.0 + urgency_score / 10.0 + ABS(emotional_valence) / 10.0)))
                WHERE is_current = 1 
                  AND (last_recalled_at IS NULL OR julianday('now') - julianday(last_recalled_at) > 1)
                """
            )
            # Re-normalize recall count periodically to smooth it out
            conn.execute("UPDATE memories SET recall_count = recall_count / 2 WHERE recall_count > 0")
            conn.commit()
            print("[Memory] Neuro-weighted biological decay applied.")
        except Exception as e:
            conn.rollback()
            print(f"[Memory Store] Decay ERR: {e}")
        finally:
            conn.close()

    def boost_related_memories(
        self,
        trigger_content: str,
        workspace_name: str,
        boost_amount: float = 0.1,
        relevance_threshold: float = 0.7,
        limit: int = 5,
    ) -> list[dict]:
        """
        Surprise-Driven Reconsolidation (v0.5 Killer Feature)
        
        When a new high-urgency/high-emotion memory triggers this method,
        it finds semantically similar OLDER memories and BOOSTS their confidence.
        
        Neuroscience basis: Emotionally salient new events strengthen associated
        older memories through reconsolidation (Nader et al., 2000). A surprise
        input doesn't just store itself — it retroactively reinforces the
        memories it connects to, making them harder to forget.
        
        This is the inverse of decay: decay weakens unused memories, while
        surprise-driven reconsolidation strengthens memories that become
        relevant again due to a high-impact event.
        
        Formula:
            new_confidence = MIN(1.0, confidence + boost_amount)
            recall_count += 1
            last_recalled_at = NOW()
        """
        # Find semantically similar memories in the same workspace
        related = self.recall(
            query=trigger_content,
            workspace_name=workspace_name,
            limit=limit,
            current_only=True,
        )

        if not related:
            return []

        boosted = []
        conn = get_connection()
        try:
            now_iso = datetime.now().isoformat()
            for mem in related:
                relevance = mem.get("relevance_score", 0)
                if relevance < relevance_threshold:
                    continue

                conn.execute(
                    """UPDATE memories 
                       SET confidence = MIN(1.0, confidence + ?),
                           recall_count = recall_count + 1,
                           last_recalled_at = ?
                       WHERE id = ?""",
                    (boost_amount, now_iso, mem["id"])
                )
                boosted.append({
                    "id": mem["id"],
                    "content": mem["content"][:80],
                    "old_confidence": mem.get("confidence", 1.0),
                    "new_confidence": min(1.0, mem.get("confidence", 1.0) + boost_amount),
                    "relevance": relevance,
                })

            conn.commit()
            if boosted:
                print(f"[Reconsolidation] Surprise boost: {len(boosted)} related memories strengthened.")
        except Exception as e:
            conn.rollback()
            print(f"[Memory Store] Reconsolidation ERR: {e}")
        finally:
            conn.close()

        return boosted
