"""
TLCM Conversational Interface
A natural language interface that wraps all four TLCM principles
into a simple chat loop powered by Gemini 3.1 Flash Lite API.

v0.4: Migrated from Ollama/gemma2:2b to Gemini API.
The AI:
- Always knows which workspace it's in
- Can recall memories semantically
- Stores important facts automatically
- Never bleeds context between workspaces
- Can perform temporal jumps on command
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from .memory_store import MemoryStore
from .workspace import WorkspaceManager
from .epoch import EpochManager
from .temporal_jump import TemporalJumpEngine

load_dotenv(Path(__file__).parent.parent / ".env")

memory = MemoryStore()
workspaces = WorkspaceManager()
epochs = EpochManager()
jumper = TemporalJumpEngine()

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

SYSTEM_PROMPT = """You are an AI assistant with TLCM (Temporal Layered Context Memory).
You are operating within a specific workspace context. You have access to relevant memories
from that workspace only. 

Your behavior:
- Reference provided memories when answering
- Be honest when you don't have a memory for something
- If the user mentions something worth remembering, indicate it clearly
- Never mix information from different workspaces unless explicitly told to
- If the user asks about the past, you can perform a temporal jump
"""


def _call_gemini(system_prompt: str, messages: list[dict]) -> str:
    """Call Gemini API for chat. Falls back to error message."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "[Error] GEMINI_API_KEY not set. Cannot chat."
    
    client = genai.Client(api_key=api_key)
    
    # Build a single prompt from message history
    prompt_parts = [f"SYSTEM: {system_prompt}\n"]
    for msg in messages:
        role = msg["role"].upper()
        prompt_parts.append(f"{role}: {msg['content']}")
    
    full_prompt = "\n\n".join(prompt_parts)
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
        )
        return response.text
    except Exception as e:
        return f"[Error] Gemini API call failed: {e}"


class TLCMChat:
    def __init__(self, workspace_name: str, epoch_name: str = None):
        self.workspace_name = workspace_name
        self.epoch_name = epoch_name
        self.history = []
        
        # Ensure workspace + epoch exist
        workspace = workspaces.get_or_create(workspace_name)
        if epoch_name:
            epoch = epochs.get_by_name(workspace["id"], epoch_name)
            if not epoch:
                epochs.create(workspace["id"], epoch_name)
        else:
            epochs.get_or_create_active(workspace["id"], workspace_name)

    def chat(self, user_input: str) -> str:
        """Process a user message with full TLCM memory context."""
        # Retrieve relevant memories from this workspace
        relevant_memories = memory.recall(
            query=user_input,
            workspace_name=self.workspace_name,
            epoch_name=self.epoch_name,
            limit=5,
        )

        # Build memory context string
        if relevant_memories:
            mem_context = "\n".join([
                f"- [{m.get('source', 'stated')}] {m['content']}"
                for m in relevant_memories
            ])
            memory_block = f"\n\nRELEVANT MEMORIES (from workspace '{self.workspace_name}'):\n{mem_context}"
        else:
            memory_block = f"\n\n(No memories yet in workspace '{self.workspace_name}')"

        # Construct full system prompt with memory
        full_system = SYSTEM_PROMPT + memory_block

        # Add to conversation history
        self.history.append({"role": "user", "content": user_input})

        # Query Gemini
        reply = _call_gemini(full_system, self.history)

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def remember_this(self, content: str, reason: str = "user_stated") -> str:
        """Explicitly store a memory in the current workspace/epoch."""
        result = memory.remember(
            content=content,
            workspace_name=self.workspace_name,
            epoch_name=self.epoch_name,
            source=reason,
        )
        return f"[Remembered in '{self.workspace_name}' / '{result['epoch']}']"

    def update_memory(self, memory_id: str, new_content: str, reason: str) -> str:
        """Update a memory without overwriting the old version."""
        result = memory.update(
            memory_id=memory_id,
            new_content=new_content,
            reason=reason,
            workspace_name=self.workspace_name,
        )
        return f"[Updated to v{result['version']} — old version preserved with id {result['old_id'][:8]}...]"

    def temporal_jump(self, from_epoch: str, to_epoch: str = None, query: str = None) -> str:
        """Perform a temporal jump between epochs."""
        return jumper.jump(
            workspace_name=self.workspace_name,
            from_epoch_name=from_epoch,
            to_epoch_name=to_epoch,
            query=query,
        )
