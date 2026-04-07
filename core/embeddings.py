"""
TLCM Embedding Engine
Uses Ollama's nomic-embed-text (or llama3.2) for local embeddings.
ChromaDB stores vectors per workspace/epoch for isolated semantic search.
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import ollama

import os

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma"
EMBEDDING_DIM = 768


# Singleton client cache (avoid recreating on every call)
_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    if os.environ.get("TLCM_TEST_MODE") == "1":
        _chroma_client = chromadb.EphemeralClient()
    else:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client


def _collection_name(workspace_name: str) -> str:
    """
    Each workspace gets its own ChromaDB collection.
    This is the technical implementation of workspace isolation.
    Epoch filtering is done via metadata (where="epoch") to prevent
    creating 100s of tiny SQLite files and crashing Chroma.
    """
    base = workspace_name.lower().replace(" ", "_").replace("-", "_")[:30]
    return f"ws_{base}"


def _embed(text: str) -> list[float]:
    """
    Get embedding from Ollama using gemma2:2b.
    In test mode (TLCM_TEST_MODE=1), returns a deterministic dummy vector.
    """
    if os.environ.get("TLCM_TEST_MODE") == "1":
        # Deterministic mock: hash the text to get slightly varied vectors
        h = hash(text) % 1000 / 1000.0
        return [h + 0.001 * i for i in range(EMBEDDING_DIM)]
    response = ollama.embeddings(model="gemma2:2b", prompt=text)
    return response["embedding"]


class EmbeddingEngine:
    def embed_and_store(
        self,
        memory_id: str,
        content: str,
        workspace_name: str,
        epoch_name: str = "",
    ):
        """Store an embedding in the workspace's isolated ChromaDB collection."""
        client = _get_chroma_client()
        collection_name = _collection_name(workspace_name)

        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"workspace": workspace_name},
            )
            embedding = _embed(content)
            collection.upsert(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"workspace": workspace_name, "epoch": epoch_name or ""}],
            )
        except Exception as e:
            print(f"[Embedding] ERR: Could not store embedding: {e}")
            raise e

    def search(
        self,
        query: str,
        workspace_name: str,
        epoch_name: str = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Semantic search ONLY within the specified workspace (+ optional epoch).
        NEVER searches across workspace boundaries.
        """
        client = _get_chroma_client()
        collection_name = _collection_name(workspace_name)

        try:
            collection = client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist yet — no memories stored
            return []

        try:
            query_embedding = _embed(query)
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": min(limit, collection.count() or 1),
            }
            if epoch_name:
                query_kwargs["where"] = {"epoch": epoch_name}
                
            results = collection.query(**query_kwargs)

            output = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    output.append({
                        "memory_id": memory_id,
                        "content": results["documents"][0][i],
                        "score": 1 - (results["distances"][0][i] if results.get("distances") else 0),
                    })
            return output
        except Exception as e:
            print(f"[Embedding] Search error: {e}")
            return []

    def delete(self, memory_id: str, workspace_name: str, epoch_name: str = ""):
        """Remove an embedding (called when archiving old versions)."""
        client = _get_chroma_client()
        collection_name = _collection_name(workspace_name)
        try:
            collection = client.get_collection(collection_name)
            collection.delete(ids=[memory_id])
        except Exception:
            pass  # Already gone or never stored
