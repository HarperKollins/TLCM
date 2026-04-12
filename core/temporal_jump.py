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

v0.4: Migrated from local Ollama/gemma2:2b to Gemini 3.1 Flash Lite API
for significantly better temporal reasoning on nuanced deltas.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from .database import get_connection, new_id
from .workspace import WorkspaceManager
from .epoch import EpochManager
from .memory_store import MemoryStore

load_dotenv(Path(__file__).parent.parent / ".env")

workspace_mgr = WorkspaceManager()
epoch_mgr = EpochManager()
memory_store = MemoryStore()

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Gemini API for temporal analysis. Falls back gracefully."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "[Error] GEMINI_API_KEY not set. Cannot perform temporal analysis."
    
    client = genai.Client(api_key=api_key)
    prompt = f"""SYSTEM: {system_prompt}

USER: {user_prompt}"""
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"[Error] Gemini API call failed: {e}"


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
    def calculate_delta(self, workspace_name: str, from_epoch_name: str, to_epoch_name: str = None) -> dict:
        workspace = workspace_mgr.get(workspace_name)
        if not workspace:
            raise ValueError(f"Workspace '{workspace_name}' not found.")

        from_epoch = epoch_mgr.get_by_name(workspace["id"], from_epoch_name)
        if not from_epoch:
            raise ValueError(f"Epoch '{from_epoch_name}' not found.")

        from_memories = memory_store.recall_epoch_state(workspace["id"], from_epoch["id"])

        if to_epoch_name:
            to_epoch = epoch_mgr.get_by_name(workspace["id"], to_epoch_name)
        else:
            to_epoch = epoch_mgr.get_active(workspace["id"])

        to_memories = memory_store.recall_epoch_state(workspace["id"], to_epoch["id"]) if to_epoch else []

        continuities, additions, evolutions = [], [], []
        from_ids = {m["id"]: m for m in from_memories}
        
        for tm in to_memories:
            if tm["id"] in from_ids:
                continuities.append(tm)
            else:
                history = memory_store.get_version_history(tm["id"])
                evolved_from = None
                for old_v in history:
                    if old_v["id"] in from_ids:
                        evolved_from = from_ids[old_v["id"]]
                        break
                
                if evolved_from:
                    evolutions.append({
                        "from": evolved_from,
                        "to": tm,
                        "reason": tm.get("update_reason", "No reason provided")
                    })
                else:
                    additions.append(tm)
                    
        return {
            "continuities": continuities,
            "additions": additions,
            "evolutions": evolutions
        }

    def jump(
        self,
        workspace_name: str,
        from_epoch_name: str,
        to_epoch_name: str = None,
        query: str = None,
    ) -> str:
        # Get the delta structures
        try:
            delta = self.calculate_delta(workspace_name, from_epoch_name, to_epoch_name)
        except ValueError as e:
            return f"[Error] {str(e)}"
            
        continuities = delta["continuities"]
        additions = delta["additions"]
        evolutions = delta["evolutions"]
        
        workspace = workspace_mgr.get(workspace_name)
        from_epoch = epoch_mgr.get_by_name(workspace["id"], from_epoch_name)
        to_epoch = epoch_mgr.get_by_name(workspace["id"], to_epoch_name) if to_epoch_name else epoch_mgr.get_active(workspace["id"])
        
        to_epoch_actual_name = to_epoch["name"] if to_epoch else "Current"

        # Build the structured temporal jump prompt
        prompt = self._build_prompt(
            workspace_name=workspace_name,
            from_epoch=from_epoch_name,
            to_epoch=to_epoch_actual_name,
            continuities=continuities,
            additions=additions,
            evolutions=evolutions,
            query=query,
        )

        print(f"[TemporalJump] Jumping: '{from_epoch_name}' -> '{to_epoch_name}' in workspace '{workspace_name}'...")

        # Run through Gemini API (or return raw prompt in test mode)
        if os.environ.get("TLCM_TEST_MODE") == "1":
            result = prompt
        else:
            system_prompt = (
                "You are the TLCM Temporal Analysis Engine. Your job is to reason about "
                "how a given context evolved across time. Be specific, honest, and analytical. "
                "Do not hallucinate -- only reference the facts provided."
            )
            result = _call_gemini(system_prompt, prompt)

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
        continuities: list[dict],
        additions: list[dict],
        evolutions: list[dict],
        query: str = None,
    ) -> str:
        base = f"TEMPORAL JUMP ANALYSIS\nWorkspace: {workspace_name}\n"
        base += f"Jumping from '{from_epoch}' to '{to_epoch}'.\n\n"
        base += "Here is the explicitly calculated strict mathematical delta between the two states:\n\n"
        
        if continuities:
            base += "🟢 CONTINUITIES (Stayed the same):\n"
            for m in continuities:
                base += f" - {m['content']}\n"
            base += "\n"
            
        if additions:
            base += "🔵 NEW BELIEFS (Added):\n"
            for m in additions:
                base += f" - {m['content']}\n"
            base += "\n"
            
        if evolutions:
            base += "🟡 EVOLUTIONS (Changed/Updated):\n"
            for ev in evolutions:
                base += f" - OLD ({from_epoch}): {ev['from']['content']}\n"
                base += f"   NEW ({to_epoch}): {ev['to']['content']}\n"
                base += f"   REASON: {ev['reason']}\n\n"
            
        base += """Your task:
1. Summarize the meaning of this explicitly provided semantic delta.
2. Do NOT hallucinate changes; only refer to the facts provided above in the Continuties, Additions, and Evolutions.
3. How did the world-state evolve and what caused the shifts?
4. What does this reveal about the trajectory of the workspace?
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

        if os.environ.get("TLCM_TEST_MODE") == "1":
            return prompt
        return _call_gemini(
            "You are a temporal reasoning analyst. Be concise and analytical.",
            prompt
        )
