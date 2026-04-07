"""
TLCM Embedding Engine
Uses Ollama's nomic-embed-text (or llama3.2) for local embeddings.
ChromaDB stores vectors per workspace/epoch for isolated semantic search.
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import ollama

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma"


def _get_chroma_client():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def _collection_name(workspace_name: str, epoch_name: str = None) -> str:
    """
    Each workspace+epoch gets its own ChromaDB collection.
    This is the technical implementation of workspace isolation.
    """
    base = workspace_name.lower().replace(" ", "_").replace("-", "_")[:30]
    if epoch_name:
        epoch = epoch_name.lower().replace(" ", "_").replace("-", "_")[:20]
        return f"ws_{base}_ep_{epoch}"
    return f"ws_{base}"


def _embed(text: str) -> list[float]:
    """
    Get embedding from Ollama using llama3.2.
    nomic-embed-text needs 16GB+ RAM dedicated — too heavy for this machine.
    llama3.2 at 2GB fits comfortably and produces quality embeddings.
    """
    response = ollama.embeddings(model="llama3.2", prompt=text)
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
        collection_name = _collection_name(workspace_name, epoch_name or None)

        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"workspace": workspace_name, "epoch": epoch_name},
            )
            embedding = _embed(content)
            collection.upsert(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"workspace": workspace_name, "epoch": epoch_name}],
            )
        except Exception as e:
            print(f"[Embedding] Warning: Could not store embedding: {e}")

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
        collection_name = _collection_name(workspace_name, epoch_name)

        try:
            collection = client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist yet — no memories stored
            return []

        try:
            query_embedding = _embed(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit, collection.count() or 1),
            )

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
        collection_name = _collection_name(workspace_name, epoch_name)
        try:
            collection = client.get_collection(collection_name)
            collection.delete(ids=[memory_id])
        except Exception:
            pass  # Already gone or never stored
