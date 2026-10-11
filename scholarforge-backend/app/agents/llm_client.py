import logging
import threading
from typing import List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable
from app.core.config import settings

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Thread-safe OpenRouter API key manager.
    Tracks all available keys and marks exhausted/invalid keys to seamlessly
    rotate and failover to the next healthy key in the pool.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._exhausted_keys: set[str] = set()

    def get_ordered_keys(self) -> list[str]:
        all_keys = settings.ALL_OPENROUTER_KEYS
        if not all_keys:
            if settings.OPENROUTER_API_KEY:
                return [settings.OPENROUTER_API_KEY]
            return []

        with self._lock:
            active = [k for k in all_keys if k not in self._exhausted_keys]
            exhausted = [k for k in all_keys if k in self._exhausted_keys]
            if not active:
                # If all keys were marked exhausted, reset to give retry chance
                self._exhausted_keys.clear()
                return list(all_keys)
            return active + exhausted

    def mark_exhausted(self, key: str):
        with self._lock:
            self._exhausted_keys.add(key)
            logger.warning(
                "Marked OpenRouter key ending in ...%s as exhausted.",
                key[-6:] if len(key) >= 6 else "***"
            )


key_manager = KeyManager()


def _create_single_chat_model(
    api_key: str,
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 1200
) -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=0,  # Failover immediately without hanging on an exhausted key!
        request_timeout=60.0,
        default_headers={
            "HTTP-Referer": "https://github.com/scholarforge/scholarforge",
            "X-Title": "ScholarForge AI",
        },
    )


def get_llm(
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 1200
) -> Runnable:
    """
    Returns a LangChain model configured with OpenRouter multi-key failover.
    If Key 1 exhausts credits (402) or is rate-limited (429), it automatically
    fails over to Key 2, Key 3, Key 4, and free-tier fallback models.
    """
    keys = key_manager.get_ordered_keys()
    if not keys:
        logger.error("No OpenRouter API key found in configuration!")
        return _create_single_chat_model("missing-key", model_name, temperature, max_tokens)

    # Primary model using the first active key
    primary_model = _create_single_chat_model(keys[0], model_name, temperature, max_tokens)

    fallbacks: list[Runnable] = []

    # Fallback models with subsequent keys in the pool
    for k in keys[1:]:
        fallbacks.append(_create_single_chat_model(k, model_name, temperature, max_tokens))

    # Free tier safety-net fallbacks for each key (in case all paid credits are depleted)
    free_fallback_models = ["openrouter/free", "google/gemma-4-31b-it:free"]
    if not any(model_name.endswith(sfx) for sfx in [":free", "openrouter/free"]):
        for free_model in free_fallback_models:
            for k in keys:
                fallbacks.append(_create_single_chat_model(k, free_model, temperature, min(max_tokens, 600)))

    if not fallbacks:
        return primary_model

    return primary_model.with_fallbacks(fallbacks)