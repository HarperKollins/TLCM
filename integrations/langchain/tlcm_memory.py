from typing import List
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from core.async_bus import MemoryBus
from core.workspace import WorkspaceManager

class TLCMChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain integration for TLCM.
    Maps standard short-term LLM memory history into the TLCM temporal engine.
    """
    
    def __init__(self, workspace_name: str, session_id: str):
        self.workspace_name = workspace_name
        self.session_id = session_id
        
        # Ensure workspace exists
        mgr = WorkspaceManager()
        mgr.get_or_create(workspace_name, f"LangChain Auto-Created Workspace for {session_id}")
        self.bus = MemoryBus.get_instance()
        self._messages = []

    @property
    def messages(self) -> List[BaseMessage]:
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the memory and push into TLCM."""
        self._messages.append(message)
        
        # Fire and forget into the async bus
        # This will securely process background emotional valence and True Graph Surgery
        # while the agent loop proceeds unaffected by latency.
        async_enqueue_coro = self.bus.enqueue(
            content=message.content,
            workspace_name=self.workspace_name,
            epoch_name=self.session_id,
            source=message.type
        )
        
        import asyncio
        try:
             # Fast schedule without blocking
             loop = asyncio.get_running_loop()
             loop.create_task(async_enqueue_coro)
        except RuntimeError:
             # If no loop is running, run it quickly
             asyncio.run(async_enqueue_coro)

    def clear(self) -> None:
        self._messages = []
