# Custom Providers (LLM, Vector Store, SQL)

TLCM's primary strength for enterprise deployment is its **Modular Provider Architecture**. Out of the box, it uses Gemini Flash, ChromaDB, and SQLite. However, you can subclass the standard interfaces in `core/interfaces.py` to adapt the memory system to your exact needs.

## The Cognitive Provider
The Cognitive Provider is the "Judge" that performs the neuro-weighted decay scoring, extraction, and semantic deltas. 

To create an OpenAI Judge, implement `CognitionProvider`:
```python
from core.interfaces import CognitionProvider, JudgmentResult
import openai

class OpenAIProvider(CognitionProvider):
    def evaluate_memory(self, memory_text: str, context: str = "") -> JudgmentResult:
        # 1. Prompt GPT-4o-mini heavily for JSON output.
        # 2. Map its output to the JudgmentResult struct.
        return JudgmentResult(
            emotional_valence=0,
            urgency_score=5,
            semantic_impact=5,
            reconsolidation_flag="append"
        )
```

## The Vector & Relational Providers
Similarly, `VectorStoreProvider` handles Semantic Isolation, and `RelationalStoreProvider` maintains the Git-like exact parent-child trees of memories. 

When configuring your engine, you simply pass the concrete providers to your configuration loop:
```python
from tlcm_app import TLCMApp
from my_custom_providers import OpenAIProvider, PostgresStore

app = TLCMApp()
app.config.backend.provider = "openai"
# The system relies on standard Interface subclassing
```
