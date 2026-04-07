"""
TLCM Temporal Jump Engine
Principle 4: The Temporal Jump Capability

This is the most novel part of TLCM.
When asked to "jump" to a previous epoch, the engine:
1. Reconstructs the COMPLETE world-state from that epoch
2. Asks the LLM to reason FROM WITHIN that world-state
3. Then surfaces the delta to the current state
4. Maps the arc: what changed, what stayed, what it means

This is the AI equivalent of the brain's "neural jump back in time."
"""

import ollama
from .database import get_connection, new_id
from .workspace import WorkspaceManager
from .epoch import EpochManager
from .memory_store import MemoryStore

workspace_mgr = WorkspaceManager()
epoch_mgr = EpochManager()
memory_store = MemoryStore()

MODEL = "gemma2:2b"


def _format_memories(memories: list[dict]) -> str:
    if not memories:
        return "(No memories recorded for this period)"
    lines = []
    for i, m in enumerate(memories, 1):
        lines.append(f"{i}. [{m.get('source', 'stated')}] {m['content']}")
        if m.get("update_reason"):
            lines.append(f"   (Updated because: {m['update_reason']})")
    return "\n".join(lines)


class TemporalJumpEngine:
    def jump(
        self,
        workspace_name: str,
        from_epoch_name: str,
        to_epoch_name: str = None,
        query: str = None,
    ) -> str:
        """
        Perform a temporal jump between two epochs within a workspace.
        Reconstructs the world-state at each epoch and maps the arc between them.
        """
        workspace = workspace_mgr.get(workspace_name)
        if not workspace:
            return f"[Error] Workspace '{workspace_name}' not found."

        from_epoch = epoch_mgr.get_by_name(workspace["id"], from_epoch_name)
        if not from_epoch:
            return f"[Error] Epoch '{from_epoch_name}' not found in workspace '{workspace_name}'."

        # Get memories AT the from_epoch
        from_memories = memory_store.recall_epoch_state(workspace["id"], from_epoch["id"])

        # Get memories at the to_epoch (default: current active epoch)
        if to_epoch_name:
            to_epoch = epoch_mgr.get_by_name(workspace["id"], to_epoch_name)
        else:
            to_epoch = epoch_mgr.get_active(workspace["id"])
            to_epoch_name = to_epoch["name"] if to_epoch else "Current"

        to_memories = (
            memory_store.recall_epoch_state(workspace["id"], to_epoch["id"])
            if to_epoch
            else []
        )

        # Build the temporal jump prompt
        prompt = self._build_prompt(
            workspace_name=workspace_name,
            from_epoch=from_epoch_name,
            to_epoch=to_epoch_name,
            from_memories=from_memories,
            to_memories=to_memories,
            query=query,
        )

        print(f"[TemporalJump] Jumping: '{from_epoch_name}' → '{to_epoch_name}' in workspace '{workspace_name}'...")

        # Run through local LLM
        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the TLCM Temporal Analysis Engine. Your job is to reason about "
                        "how a given context evolved across time. Be specific, honest, and analytical. "
                        "Do not hallucinate — only reference the facts provided."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            options={"num_ctx": 2048}
        )
        result = response["message"]["content"]

        # Log the jump
        conn = get_connection()
        conn.execute(
            "INSERT INTO temporal_jumps (id, workspace_id, from_epoch_id, to_epoch_id, query, result) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_id(),
                workspace["id"],
                from_epoch["id"],
                to_epoch["id"] if to_epoch else None,
                query,
                result,
            ),
        )
        conn.commit()
        conn.close()

        return result

    def _build_prompt(
        self,
        workspace_name: str,
        from_epoch: str,
        to_epoch: str,
        from_memories: list[dict],
        to_memories: list[dict],
        query: str = None,
    ) -> str:
        base = f"""
TEMPORAL JUMP ANALYSIS
Workspace: {workspace_name}

═══ STATE DURING: {from_epoch} ═══
{_format_memories(from_memories)}

═══ STATE DURING: {to_epoch} ═══
{_format_memories(to_memories)}

Your task:
1. Reason from WITHIN the '{from_epoch}' world-state first. What was true? What was uncertain?
2. Identify every significant change between '{from_epoch}' and '{to_epoch}'.
3. Map the arc: how did things evolve? What caused the shifts?
4. Highlight what STAYED THE SAME across both epochs (continuity matters).
5. What does this arc reveal about the trajectory of '{workspace_name}'?
"""
        if query:
            base += f"\nSpecific question to answer: {query}"
        return base.strip()

    def explain_belief_arc(self, memory_id: str, workspace_name: str) -> str:
        """
        Given a memory ID, trace its full version history and explain the arc
        of how that specific belief evolved over time.
        """
        history = memory_store.get_version_history(memory_id)
        if not history:
            return "Memory not found."

        if len(history) == 1:
            return f"This memory has no updates. Original belief: {history[0]['content']}"

        history_text = "\n".join([
            f"Version {m['version']} ({m['created_at'][:10]}): {m['content']}"
            + (f"\n  → Updated because: {m['update_reason']}" if m.get("update_reason") else "")
            for m in history
        ])

        prompt = f"""
This is the complete version history of a single belief in workspace '{workspace_name}':

{history_text}

Explain:
1. How did this belief evolve?
2. What drove each update?
3. What does the full arc reveal?
"""

        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a temporal reasoning analyst. Be concise and analytical."},
                {"role": "user", "content": prompt},
            ],
            options={"num_ctx": 2048}
        )
        return response["message"]["content"]
