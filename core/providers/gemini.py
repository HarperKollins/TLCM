"""
TLCM GeminiProvider — Cloud Cognition Backend (complete implementation)
=======================================================================
Wraps gemini_judge.analyze_memory and temporal_jump Gemini calls
behind the standard CognitionProvider interface.
"""

import os
import logging
from .interfaces import CognitionProvider, JudgmentResult

logger = logging.getLogger("tlcm.gemini_provider")


class GeminiProvider(CognitionProvider):
    """Cognition backend using Google Gemini Flash Lite API."""

    def evaluate_memory(self, memory_text: str, context: str = "") -> JudgmentResult:
        """Evaluate memory using the Gemini neuro-scoring pipeline."""
        if os.environ.get("TLCM_TEST_MODE") == "1":
            h = abs(hash(memory_text))
            return JudgmentResult(
                emotional_valence=(h % 21) - 10,
                urgency_score=h % 11,
                semantic_impact=(h % 7) + 2,
                reconsolidation_flag=["append", "strengthen", "weaken", "contradicts_core"][h % 4],
            )
        from .gemini_judge import analyze_memory
        res = analyze_memory(memory_text, "default", existing_context=context)
        return JudgmentResult(
            emotional_valence=res.get("emotional_valence", 0),
            urgency_score=res.get("urgency_score", 5),
            semantic_impact=res.get("semantic_impact", 5),
            reconsolidation_flag=res.get("reconsolidation_suggestion", "append"),
        )

    def calculate_temporal_delta(self, from_state: str, to_state: str, query: str) -> str:
        """
        Use Gemini to produce a narrative analysis of the semantic delta
        between two epoch world-states. Called by TemporalJumpEngine.jump().
        """
        if os.environ.get("TLCM_TEST_MODE") == "1":
            return f"[Test] Temporal delta: query='{query}'"

        from .config import settings
        from google import genai

        api_key = settings.backend.api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "[Error] GEMINI_API_KEY not set."

        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are a temporal reasoning engine for the TLCM memory system.\n\n"
                f"ORIGIN EPOCH WORLD-STATE:\n{from_state}\n\n"
                f"TARGET EPOCH WORLD-STATE:\n{to_state}\n\n"
                f"QUERY: {query or 'How did the world-state change between these epochs?'}\n\n"
                f"Describe:\n1. What beliefs remained constant (Continuities)\n"
                f"2. What changed or evolved (Evolutions)\n"
                f"3. What is entirely new (Additions)\n"
                f"Be specific, factual, and reference the actual memory content."
            )
            response = client.models.generate_content(
                model=settings.backend.model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"[GeminiProvider] Delta calculation failed: {e}")
            return f"[Error] Gemini temporal delta failed: {e}"
