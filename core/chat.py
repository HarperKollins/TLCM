"""
TLCM Conversational Interface
A natural language interface that wraps all four TLCM principles
into a simple chat loop powered by llama3.2 via Ollama.

The AI:
- Always knows which workspace it's in
- Can recall memories semantically
- Stores important facts automatically
- Never bleeds context between workspaces
- Can perform temporal jumps on command
"""

import ollama
from .memory_store import MemoryStore
from .workspace import WorkspaceManager
from .epoch import EpochManager
from .temporal_jump import TemporalJumpEngine

memory = MemoryStore()
workspaces = WorkspaceManager()
epochs = EpochManager()
jumper = TemporalJumpEngine()

MODEL = "gemma2:2b"

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

        # Query LLM
        messages = [{"role": "system", "content": full_system}] + self.history

        response = ollama.chat(model=MODEL, messages=messages, options={"num_ctx": 2048})
        assistant_reply = response["message"]["content"]

        self.history.append({"role": "assistant", "content": assistant_reply})
        return assistant_reply

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
