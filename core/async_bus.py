"""
TLCM Async Memory Bus — The Tiered Memory Architecture
=======================================================
Tier 1 (STM): asyncio.Queue — accepts memories instantly, returns temp_id
Tier 2 (LTM): Background worker — processes via Gemini Judge, writes to
              SQLite + ChromaDB, fires SSE completion events.

This is what makes TLCM run at 0.01s ingestion on a 2012 i5.
The CPU never blocks on LLM inference — it just routes.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Callable, Awaitable

logger = logging.getLogger("tlcm.async_bus")


class MemoryPayload:
    """A memory waiting to be processed by the background worker."""

    def __init__(
        self,
        temp_id: str,
        content: str,
        workspace_name: str,
        epoch_name: Optional[str] = None,
        source: str = "user_stated",
        tags: Optional[list] = None,
    ):
        self.temp_id = temp_id
        self.content = content
        self.workspace_name = workspace_name
        self.epoch_name = epoch_name
        self.source = source
        self.tags = tags or []
        self.queued_at = datetime.now().isoformat()


class MemoryBus:
    """
    Singleton async memory bus.
    
    Usage:
        bus = MemoryBus.get_instance()
        temp_id = await bus.enqueue(content, workspace_name, ...)
        # Background worker processes it automatically
    """

    _instance = None

    def __init__(self):
        self._queue: asyncio.Queue[MemoryPayload] = asyncio.Queue()
        self._chroma_lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._sse_callback: Optional[Callable[[dict], Awaitable[None]]] = None
        self._running = False
        self._status_map = {}

    @classmethod
    def get_instance(cls) -> "MemoryBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (used in tests)."""
        if cls._instance and cls._instance._worker_task:
            cls._instance._worker_task.cancel()
        cls._instance = None

    def set_sse_callback(self, callback: Callable[[dict], Awaitable[None]]):
        """Register a callback that fires when a memory finishes processing."""
        self._sse_callback = callback

    def get_status(self, temp_id: str) -> Optional[dict]:
        """Fetch the current processing status of a memory."""
        return self._status_map.get(temp_id)

    async def enqueue(
        self,
        content: str,
        workspace_name: str,
        epoch_name: Optional[str] = None,
        source: str = "user_stated",
        tags: Optional[list] = None,
    ) -> str:
        """
        Enqueue a memory for background processing.
        Returns a temp_id immediately (Tier 1 STM).
        """
        temp_id = f"tmp_{uuid.uuid4().hex[:12]}"
        payload = MemoryPayload(
            temp_id=temp_id,
            content=content,
            workspace_name=workspace_name,
            epoch_name=epoch_name,
            source=source,
            tags=tags,
        )
        await self._queue.put(payload)
        self._status_map[temp_id] = {"status": "processing"}
        logger.info(f"[Bus] Enqueued {temp_id} for '{workspace_name}' (queue size: {self._queue.qsize()})")
        return temp_id

    def start_worker(self):
        """Start the background worker loop. Call once at FastAPI startup."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[Bus] Background memory worker started.")

    def stop_worker(self):
        """Stop the background worker. Call at FastAPI shutdown."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            logger.info("[Bus] Background memory worker stopped.")

    async def _worker_loop(self):
        """
        Continuously pull from the queue and process memories.
        Each memory goes through: Gemini analysis → SQLite → ChromaDB → SSE push.
        """
        from core.memory_store import MemoryStore
        from core.gemini_judge import analyze_memory

        store = MemoryStore()

        while self._running:
            try:
                # Block until a payload is available (with timeout to allow shutdown)
                try:
                    payload = await asyncio.wait_for(self._queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue

                logger.info(f"[Bus] Processing {payload.temp_id}...")

                # Step 0: Local Fallback Heuristic
                local_bypassed = False
                try:
                    similar = store.recall(
                        query=payload.content,
                        workspace_name=payload.workspace_name,
                        epoch_name=payload.epoch_name,
                        limit=1
                    )
                    if similar and similar[0].get("relevance_score", 0) > 0.95:
                        logger.info(f"[Bus] Local fallback activated. {payload.temp_id} matched memory {similar[0]['id'][:8]}")
                        analysis = {
                            "semantic_delta": "Redundant/continuation of existing memory.",
                            "emotional_valence": similar[0].get("emotional_valence", 0),
                            "urgency_score": similar[0].get("urgency_score", 5),
                            "semantic_impact": 1,
                            "reconsolidation_suggestion": "strengthen",
                        }
                        local_bypassed = True
                except Exception as e:
                    logger.error(f"[Bus] Local fallback check failed: {e}")

                if not local_bypassed:
                    # Step 1: Run Gemini analysis (offloaded to API, non-blocking for i5)
                    try:
                        analysis = await asyncio.to_thread(
                            analyze_memory,
                            content=payload.content,
                            workspace_name=payload.workspace_name,
                        )
                    except Exception as e:
                        logger.error(f"[Bus] Gemini analysis failed for {payload.temp_id}: {e}")
                        analysis = {
                            "semantic_delta": "",
                            "emotional_valence": 0,
                            "urgency_score": 5,
                            "semantic_impact": 5,
                            "reconsolidation_suggestion": "append",
                        }

                # Step 2: Commit to SQLite + ChromaDB (under lock for Chroma safety)
                try:
                    async with self._chroma_lock:
                        result = await asyncio.to_thread(
                            store.commit_memory,
                            content=payload.content,
                            workspace_name=payload.workspace_name,
                            epoch_name=payload.epoch_name,
                            source=payload.source,
                            tags=payload.tags,
                            emotional_valence=analysis.get("emotional_valence", 0),
                            urgency_score=analysis.get("urgency_score", 5),
                            semantic_impact=analysis.get("semantic_impact", 5),
                            reconsolidation_flag=analysis.get("reconsolidation_suggestion", "append"),
                        )
                except Exception as e:
                    logger.error(f"[Bus] Commit failed for {payload.temp_id}: {e}")
                    self._status_map[payload.temp_id] = {
                        "status": "error",
                        "error": str(e)
                    }
                    if self._sse_callback:
                        await self._sse_callback({
                            "type": "memory_error",
                            "temp_id": payload.temp_id,
                            "error": str(e),
                        })
                    self._queue.task_done()
                    continue

                # Step 3: Fire SSE completion event
                event_data = {
                    "type": "memory_stored",
                    "temp_id": payload.temp_id,
                    "memory_id": result["id"],
                    "workspace": payload.workspace_name,
                    "epoch": result.get("epoch", ""),
                    "emotional_valence": analysis.get("emotional_valence", 0),
                    "urgency_score": analysis.get("urgency_score", 5),
                    "semantic_impact": analysis.get("semantic_impact", 5),
                    "reconsolidation": analysis.get("reconsolidation_suggestion", "append"),
                    "status": "complete",
                }

                self._status_map[payload.temp_id] = event_data

                if self._sse_callback:
                    await self._sse_callback(event_data)

                logger.info(
                    f"[Bus] Committed {payload.temp_id} → {result.get('id', 'updated')[:12]}... "
                    f"(emotion={analysis.get('emotional_valence')}, "
                    f"urgency={analysis.get('urgency_score')}, "
                    f"recon={analysis.get('reconsolidation_suggestion')})"
                )

                self._queue.task_done()

            except asyncio.CancelledError:
                logger.info("[Bus] Worker cancelled.")
                break
            except Exception as e:
                logger.error(f"[Bus] Unexpected worker error: {e}")
                await asyncio.sleep(1)

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()
