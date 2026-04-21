"""
TLCM Gemini Judge — Structured Neuro-Weighted Analysis
Offloads all heavy semantic reasoning to Gemini 3.1 Flash Lite.
Returns structured JSON with emotional valence, urgency, impact,
and reconsolidation suggestions for every memory.

This is the "brain" of the Slim Node architecture:
Your i5 handles orchestration, Gemini handles cognition.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from .config import settings

logger = logging.getLogger("tlcm.gemini_judge")

# Read model from config (overridable via GEMINI_MODEL env var)
GEMINI_MODEL = settings.backend.model_name

# Structured output schema for Gemini
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "semantic_delta": {
            "type": "string",
            "description": "A concise summary of what this memory adds or changes in the workspace context."
        },
        "emotional_valence": {
            "type": "integer",
            "description": "Emotional intensity from -10 (extremely negative) to +10 (extremely positive). 0 = neutral factual."
        },
        "urgency_score": {
            "type": "integer",
            "description": "How time-critical is this information? 0 (trivial/background) to 10 (mission-critical/urgent)."
        },
        "semantic_impact": {
            "type": "integer",
            "description": "How much does this change the workspace's overall knowledge? 0 (redundant) to 10 (paradigm shift)."
        },
        "reconsolidation_suggestion": {
            "type": "string",
            "enum": ["strengthen", "weaken", "append", "contradicts_core"],
            "description": "How should the memory system handle this relative to existing beliefs? "
                           "'strengthen' = reinforces existing knowledge, "
                           "'weaken' = casts doubt on existing knowledge, "
                           "'append' = new independent fact, "
                           "'contradicts_core' = directly contradicts a core belief."
        }
    },
    "required": [
        "semantic_delta", "emotional_valence", "urgency_score",
        "semantic_impact", "reconsolidation_suggestion"
    ]
}


def _with_retry(func):
    """Exponential backoff retry for Gemini API rate limits."""
    def wrapper(*args, **kwargs):
        max_retries = 4
        base_delay = 8
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if any(kw in err_str for kw in ["429", "resource", "exhausted", "503", "quota"]):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Gemini rate limit hit. Retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise
    return wrapper


def _get_client():
    """Lazy-load Gemini client using config API key."""
    from google import genai
    api_key = settings.backend.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "[TLCM] GEMINI_API_KEY not set. Add it to your .env file:\n"
            "  GEMINI_API_KEY=your_key_here\n"
            "Or set COGNITION_BACKEND=ollama for air-gapped operation."
        )
    return genai.Client(api_key=api_key)


@_with_retry
def analyze_memory(
    content: str,
    workspace_name: str,
    existing_context: Optional[str] = None,
    version_history: Optional[str] = None,
) -> dict:
    """
    Analyze a new memory using Gemini structured output.
    
    Returns a dict with:
        - semantic_delta (str)
        - emotional_valence (int, -10 to +10)
        - urgency_score (int, 0 to 10)
        - semantic_impact (int, 0 to 10)
        - reconsolidation_suggestion (str enum)
    """
    # In test mode, return deterministic mock values
    if os.environ.get("TLCM_TEST_MODE") == "1":
        return _mock_analysis(content)

    client = _get_client()

    prompt = _build_analysis_prompt(content, workspace_name, existing_context, version_history)

    from google.genai.types import GenerateContentConfig

    config = GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ANALYSIS_SCHEMA,
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )

    result = json.loads(response.text)

    # Clamp values to valid ranges
    result["emotional_valence"] = max(-10, min(10, result.get("emotional_valence", 0)))
    result["urgency_score"] = max(0, min(10, result.get("urgency_score", 5)))
    result["semantic_impact"] = max(0, min(10, result.get("semantic_impact", 5)))

    valid_recon = {"strengthen", "weaken", "append", "contradicts_core"}
    if result.get("reconsolidation_suggestion") not in valid_recon:
        result["reconsolidation_suggestion"] = "append"

    logger.info(
        f"[GeminiJudge] Analyzed: emotion={result['emotional_valence']}, "
        f"urgency={result['urgency_score']}, impact={result['semantic_impact']}, "
        f"recon={result['reconsolidation_suggestion']}"
    )

    return result


def _build_analysis_prompt(
    content: str,
    workspace_name: str,
    existing_context: Optional[str] = None,
    version_history: Optional[str] = None,
) -> str:
    """Build the structured analysis prompt for Gemini."""
    prompt = f"""You are the TLCM Neuro-Analysis Engine — a cognitive architecture that processes 
memories the way the human brain does. You evaluate incoming information for emotional significance, 
urgency, semantic impact, and whether it reinforces or contradicts existing knowledge.

WORKSPACE: "{workspace_name}"

NEW MEMORY TO ANALYZE:
"{content}"
"""
    if existing_context:
        prompt += f"""
EXISTING WORKSPACE CONTEXT (recent memories in this workspace):
{existing_context}
"""
    if version_history:
        prompt += f"""
VERSION HISTORY (if this is an update to an existing belief):
{version_history}
"""
    prompt += """
Analyze this memory and return your structured evaluation. Be precise with scores:
- emotional_valence: -10 (devastating news) to +10 (euphoric breakthrough). Most factual statements are -2 to +2.
- urgency_score: 0 (background trivia) to 10 (act NOW or lose something). Most are 3-6.
- semantic_impact: 0 (redundant info) to 10 (changes everything). Most new facts are 4-6.
- reconsolidation_suggestion: How does this relate to what's already known?
  - "append" = new independent fact
  - "strengthen" = confirms/reinforces existing beliefs
  - "weaken" = introduces doubt about existing beliefs  
  - "contradicts_core" = directly opposes a fundamental belief in this workspace
"""
    return prompt.strip()


def _mock_analysis(content: str) -> dict:
    """
    Deterministic mock for test mode.
    Uses content hash to produce varied but reproducible scores.
    """
    h = abs(hash(content))
    return {
        "semantic_delta": f"New information recorded: {content[:50]}...",
        "emotional_valence": (h % 21) - 10,  # -10 to +10
        "urgency_score": h % 11,              # 0 to 10
        "semantic_impact": (h % 7) + 2,       # 2 to 8
        "reconsolidation_suggestion": ["append", "strengthen", "weaken", "contradicts_core"][h % 4],
    }
