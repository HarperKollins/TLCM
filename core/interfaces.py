from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class JudgmentResult(BaseModel):
    emotional_valence: int
    urgency_score: int
    semantic_impact: int
    reconsolidation_flag: str
    update_reason: Optional[str] = None

class CognitionProvider(ABC):
    """
    Standard interface for LLM backends (Gemini, OpenAI, Anthropic, Custom SLMs).
    Handles memory evaluation, decay scoring, and jump deltas.
    """
    
    @abstractmethod
    def evaluate_memory(self, memory_text: str, context: str = "") -> JudgmentResult:
        """
        Evaluate incoming memory for emotional valence, urgency, semantic impact,
        and determine whether it appends, contradicts, or strengthens existing context.
        """
        pass
        
    @abstractmethod
    def calculate_temporal_delta(self, from_state: str, to_state: str, query: str) -> str:
        """
        Determine the mathematical/semantic delta between two distinct temporal epochs.
        """
        pass

class VectorStoreProvider(ABC):
    """
    Standard interface for Vector Stores (Chroma, Pinecone, Qdrant, PgVector).
    Isolates cognitive workspaces strictly.
    """
    
    @abstractmethod
    def add_memory(self, workspace_id: str, memory_id: str, content: str, metadata: Dict[str, Any]):
        """Embed and add a memory to the strictly isolated workspace collection."""
        pass
        
    @abstractmethod
    def search(self, workspace_id: str, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform a semantic search within a specific workspace boundary."""
        pass

class RelationalStoreProvider(ABC):
    """
    Standard interface for Relational Graphs (SQLite, Postgres, MySQL).
    Maintains the Git-like exact parent-child trees of memories.
    """
    
    @abstractmethod
    def save_memory(self, memory_data: Dict[str, Any]):
        """Persist a memory struct to the graph store."""
        pass
        
    @abstractmethod
    def get_memory_chain(self, memory_id: str) -> List[Dict[str, Any]]:
        """Retrieve the exact version history of a memory."""
        pass
