"""LLM client for Sarthi v4.2 - OpenRouter."""
from __future__ import annotations
import os
import json
import httpx

_client: httpx.Client | None = None


def get_llm_client() -> httpx.Client:
    """Returns OpenRouter httpx Client singleton."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        _client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    return _client


def get_chat_model() -> str:
    """Returns default chat model."""
    return os.environ.get("OPENROUTER_LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")


def get_embedding_model() -> str:
    """Returns default embedding model."""
    return os.environ.get("OPENROUTER_EMBED_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2:free")


def reset_client() -> None:
    """Reset cached client."""
    global _client
    if _client:
        _client.close()
    _client = None


get_model = get_chat_model
