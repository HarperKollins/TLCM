"""
TLCM OllamaProvider — Air-Gapped Cognition Backend
====================================================
Implements CognitionProvider using local Ollama models.
Enables completely offline, privacy-preserving operation
with no external API dependency — as stated in the research paper.
"""

import json
import logging
import os
from typing import Optional
from .interfaces import CognitionProvider, JudgmentResult

logger = logging.getLogger("tlcm.ollama_provider")


class OllamaProvider(CognitionProvider):
    """
    Air-gapped cognition backend using local Ollama models.
    Fulfills the paper's claim: 'cognition_backend can be seamlessly
    toggled between gemini or ollama for total air-gapped security.'
    """

    def __init__(self, model: Optional[str] = None):
        from .config import settings
        self.model = model or settings.backend.ollama_model
        self._check_model_available()

    def _check_model_available(self):
        """Verify the configured Ollama model is pulled before use."""
        try:
            import ollama
            models = ollama.list()
            available = [m.model for m in models.models]
            # Strip tag suffix for comparison (e.g. "gemma2:2b" vs "gemma2:2b")
            if not any(self.model in m for m in available):
                logger.warning(
                    f"[OllamaProvider] Model '{self.model}' not found locally. "
                    f"Run: ollama pull {self.model}\n"
                    f"Available: {available}"
                )
        except Exception as e:
            logger.warning(f"[OllamaProvider] Could not verify model availability: {e}")

    def evaluate_memory(self, memory_text: str, context: str = "") -> JudgmentResult:
        """
        Evaluate incoming memory using a local Ollama model.
        Returns structured JudgmentResult with neuro-weighted scores.
        Falls back to safe defaults on model error.
        """
        if os.environ.get("TLCM_TEST_MODE") == "1":
            return self._mock_result(memory_text)

        try:
            import ollama
            prompt = self._build_prompt(memory_text, context)
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.1},
            )
            raw = json.loads(response["response"])
            return JudgmentResult(
                emotional_valence=max(-10, min(10, int(raw.get("emotional_valence", 0)))),
                urgency_score=max(0, min(10, int(raw.get("urgency_score", 5)))),
                semantic_impact=max(0, min(10, int(raw.get("semantic_impact", 5)))),
                reconsolidation_flag=raw.get("reconsolidation_suggestion", "append")
                if raw.get("reconsolidation_suggestion") in {"strengthen", "weaken", "append", "contradicts_core"}
                else "append",
            )
        except Exception as e:
            logger.error(f"[OllamaProvider] Evaluation failed: {e}. Using safe defaults.")
            return JudgmentResult(
                emotional_valence=0,
                urgency_score=5,
                semantic_impact=5,
                reconsolidation_flag="append",
            )

    def calculate_temporal_delta(self, from_state: str, to_state: str, query: str) -> str:
        """
        Use local Ollama model to reason about semantic delta between epochs.
        """
        if os.environ.get("TLCM_TEST_MODE") == "1":
            return f"[Test] Delta calculated between states. Query: {query}"

        try:
            import ollama
            prompt = (
                f"You are a temporal reasoning engine. Analyze how the world-state evolved.\n\n"
                f"FROM STATE:\n{from_state}\n\n"
                f"TO STATE:\n{to_state}\n\n"
                f"QUESTION: {query or 'How did the world-state evolve?'}\n\n"
                f"Provide a concise analysis of continuities, new beliefs, and evolutions."
            )
            response = ollama.generate(model=self.model, prompt=prompt)
            return response["response"]
        except Exception as e:
            logger.error(f"[OllamaProvider] Delta calculation failed: {e}")
            return f"[Error] Local model unavailable: {e}. Run: ollama pull {self.model}"

    def _build_prompt(self, memory_text: str, context: str) -> str:
        ctx_section = f"\nEXISTING CONTEXT:\n{context}" if context else ""
        return (
            f"You are a cognitive memory analyzer. Evaluate this memory and return ONLY valid JSON.\n"
            f"MEMORY: \"{memory_text}\"{ctx_section}\n\n"
            f"Return JSON with exactly these keys:\n"
            f"  emotional_valence: integer -10 to +10 (negative=bad, positive=good, 0=neutral)\n"
            f"  urgency_score: integer 0-10 (0=trivial, 10=critical)\n"
            f"  semantic_impact: integer 0-10 (0=redundant, 10=paradigm shift)\n"
            f"  reconsolidation_suggestion: one of: strengthen, weaken, append, contradicts_core\n"
            f"Example: {{\"emotional_valence\": 2, \"urgency_score\": 5, \"semantic_impact\": 6, \"reconsolidation_suggestion\": \"append\"}}"
        )

    def _mock_result(self, content: str) -> JudgmentResult:
        h = abs(hash(content))
        return JudgmentResult(
            emotional_valence=(h % 21) - 10,
            urgency_score=h % 11,
            semantic_impact=(h % 7) + 2,
            reconsolidation_flag=["append", "strengthen", "weaken", "contradicts_core"][h % 4],
        )
