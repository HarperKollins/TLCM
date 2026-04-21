"""
TLCM Provider Factory — Runtime Backend Selection
==================================================
This module fulfills the paper's claim:
  'cognition_backend can be seamlessly toggled between gemini or ollama'

Call get_cognition_provider() anywhere in the engine to get the
correct backend based on the COGNITION_BACKEND env var / config.
"""

import logging
from typing import Optional
from ..interfaces import CognitionProvider
from ..config import settings

logger = logging.getLogger("tlcm.provider_factory")

# Module-level singleton cache
_cognition_provider: Optional[CognitionProvider] = None


def get_cognition_provider() -> CognitionProvider:
    """
    Return the singleton cognition provider based on runtime config.
    
    COGNITION_BACKEND=gemini → GeminiProvider (default, cloud-based)
    COGNITION_BACKEND=ollama → OllamaProvider (air-gapped, local)
    """
    global _cognition_provider
    if _cognition_provider is not None:
        return _cognition_provider

    provider_name = settings.backend.provider.lower().strip()
    logger.info(f"[TLCM] Initialising cognition provider: '{provider_name}'")

    if provider_name == "gemini":
        from .gemini import GeminiProvider
        _cognition_provider = GeminiProvider()
    elif provider_name == "ollama":
        from .ollama_provider import OllamaProvider
        _cognition_provider = OllamaProvider()
    else:
        logger.warning(
            f"[TLCM] Unknown COGNITION_BACKEND='{provider_name}'. Defaulting to Gemini."
        )
        from .gemini import GeminiProvider
        _cognition_provider = GeminiProvider()

    return _cognition_provider


def reset_provider():
    """Force re-initialisation of the provider singleton. Used in tests."""
    global _cognition_provider
    _cognition_provider = None
