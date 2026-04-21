"""
TLCM Configuration — Single Source of Truth
=============================================
Every module reads from this config instead of hardcoding values.
Supports runtime toggling of cognition backend, vector store, and data paths.
"""

import os
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path


class BackendConfig(BaseModel):
    provider: str = Field(default="gemini", description="The cognition backend provider: gemini, ollama")
    api_key: Optional[str] = Field(default=None, description="API Key for the provider (Gemini)")
    model_name: str = Field(default="gemini-3.1-flash-lite-preview", description="Model to use for cognition")
    ollama_model: str = Field(default="gemma2:2b", description="Ollama model for air-gapped cognition")


class EmbeddingConfig(BaseModel):
    engine: str = Field(default="ollama", description="Embedding engine: ollama")
    model_name: str = Field(default="all-minilm", description="Embedding model name")
    dimension: int = Field(default=384, description="Embedding dimension for the model")


class StoreConfig(BaseModel):
    vector_store: str = Field(default="chromadb", description="Vector database provider")
    relational_store: str = Field(default="sqlite", description="Relational graph provider")
    data_dir: str = Field(
        default=str(Path(__file__).parent.parent / "data"),
        description="Directory for local store data (SQLite, ChromaDB)"
    )


class TLCMConfig(BaseModel):
    backend: BackendConfig = BackendConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    store: StoreConfig = StoreConfig()
    decay_interval_seconds: int = Field(default=86400, description="Biological decay cycle interval in seconds")
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    @classmethod
    def load_from_env(cls) -> "TLCMConfig":
        """Load configuration from environment variables."""
        data_dir = os.getenv("TLCM_DATA_DIR", str(Path(__file__).parent.parent / "data"))

        return cls(
            backend=BackendConfig(
                provider=os.getenv("COGNITION_BACKEND", "gemini"),
                api_key=os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY")),
                model_name=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview"),
                ollama_model=os.getenv("OLLAMA_COGNITION_MODEL", "gemma2:2b"),
            ),
            embedding=EmbeddingConfig(
                engine=os.getenv("EMBEDDING_ENGINE", "ollama"),
                model_name=os.getenv("EMBEDDING_MODEL", "all-minilm"),
                dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
            ),
            store=StoreConfig(
                vector_store=os.getenv("VECTOR_STORE_PROVIDER", "chromadb"),
                relational_store=os.getenv("RELATIONAL_STORE_PROVIDER", "sqlite"),
                data_dir=data_dir,
            ),
            decay_interval_seconds=int(os.getenv("TLCM_DECAY_INTERVAL_SECONDS", "86400")),
            cors_origins=os.getenv("TLCM_CORS_ORIGINS", "*").split(","),
        )


# Global singleton configuration
settings = TLCMConfig.load_from_env()
