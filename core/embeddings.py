import chromadb
from chromadb.config import Settings
from pathlib import Path
import ollama

import os
from .config import settings

CHROMA_PATH = Path(settings.store.data_dir) / "chroma"
EMBEDDING_DIM = settings.embedding.dimension
EMBEDDING_MODEL = settings.embedding.model_name


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
    """
    base = workspace_name.lower().replace(" ", "_").replace("-", "_")[:30]
    return f"ws_{base}"


def _embed(text: str) -> list[float]:
    """
    Get embedding from Ollama using the configured model.
    In test mode (TLCM_TEST_MODE=1), returns a deterministic dummy vector.
    Falls back gracefully if Ollama model is not available.
    """
    if os.environ.get("TLCM_TEST_MODE") == "1":
        h = hash(text) % 1000 / 1000.0
        return [h + 0.001 * i for i in range(EMBEDDING_DIM)]
    try:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        err_msg = str(e).lower()
        if "not found" in err_msg or "pull" in err_msg or "connection" in err_msg:
            raise RuntimeError(
                f"[TLCM] Embedding model '{EMBEDDING_MODEL}' is not available. "
                f"Please run: ollama pull {EMBEDDING_MODEL}\n"
                f"Or change EMBEDDING_MODEL in your .env file.\n"
                f"Original error: {e}"
            )
        raise


def _trigger_migration(client, collection_name: str, workspace_name: str):
    """
    Seamless Re-indexing Engine: Drops legacy collection and rebuilds 
    it cleanly from the SQLite absolute truth using the new dimension.
    """
    print(f"[Embedding] Dimension mismatch detected for '{workspace_name}'. Migrating legacy vectors to {EMBEDDING_MODEL}...")
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass  # Just in case

    collection = client.create_collection(
        name=collection_name,
        metadata={"workspace": workspace_name, "model": EMBEDDING_MODEL},
    )
    
    # Re-embed from absolute truth
    from core.database import get_connection
    conn = get_connection()
    try:
        memories = conn.execute(
            "SELECT m.id, m.content, e.name as epoch_name "
            "FROM memories m "
            "JOIN epochs e ON m.epoch_id = e.id "
            "JOIN workspaces w ON m.workspace_id = w.id "
            "WHERE w.name = ? AND m.is_current = 1", 
            (workspace_name,)
        ).fetchall()
        
        if memories:
            ids, embeddings, documents, metadatas = [], [], [], []
            for mem in memories:
                ids.append(mem["id"])
                documents.append(mem["content"])
                metadatas.append({"workspace": workspace_name, "epoch": mem["epoch_name"]})
                embeddings.append(_embed(mem["content"]))
            
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            print(f"[Embedding] Successfully re-indexed {len(memories)} memories for '{workspace_name}'.")
    finally:
        conn.close()
    return collection

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

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"workspace": workspace_name},
        )
        
        embedding = _embed(content)
        
        try:
            collection.upsert(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{"workspace": workspace_name, "epoch": epoch_name or ""}],
            )
        except Exception as e:
            if "dimension" in str(e).lower() or "expected" in str(e).lower():
                # Trigger Auto-Migration
                collection = _trigger_migration(client, collection_name, workspace_name)
                # Retry upsert once migration is finished
                collection.upsert(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{"workspace": workspace_name, "epoch": epoch_name or ""}],
                )
            else:
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

        except Exception as e:
            if "dimension" in str(e).lower() or "expected" in str(e).lower():
                collection = _trigger_migration(client, collection_name, workspace_name)
                # Retry query
                query_kwargs["n_results"] = min(limit, collection.count() or 1)
                results = collection.query(**query_kwargs)
            else:
                print(f"[Embedding] Search error: {e}")
                return []

        try:
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
            print(f"[Embedding] Search formatting error: {e}")
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
