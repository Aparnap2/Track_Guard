"""
Agentic Test Configuration - Real LLM + Real Docker + Langfuse

Per the TDD strategy: Layer 3 tests prove the real system works.
These tests require OPENAI_API_KEY and LANGFUSE_SECRET_KEY.
"""
import os
import pytest
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Load .env for OLLAMA_BASE_URL, OLLAMA_API_KEY, etc.

from ollama import Client as _OllamaClient


@pytest.fixture(scope="session")
def ollama_client():
    """Real Ollama Client — uses OLLAMA_BASE_URL + OLLAMA_API_KEY from .env."""
    import os
    base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")
    api_key = os.environ.get("OLLAMA_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return _OllamaClient(host=base_url, headers=headers)


@pytest.fixture(scope="session")
def llm_model():
    """Model name — reads OLLAMA_CHAT_MODEL from .env."""
    import os
    return os.environ.get("OLLAMA_CHAT_MODEL", "qwen3-next:80b-cloud")


@pytest.fixture(scope="session")
def langfuse_client():
    """Real Langfuse client for trace verification."""
    from langfuse import Langfuse
    # New Langfuse SDK auto-reads env vars: LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST
    return Langfuse()


@pytest.fixture
def trace_context(langfuse_client):
    """Create a Langfuse trace context for the test.

    Langfuse SDK v4: Traces are implicit - start an observation to begin a trace.
    The root span IS the trace. Use langfuse_client.start_as_current_observation().
    
    This fixture provides a parent span that all test spans nest under.
    """
    trace = langfuse_client.start_as_current_observation(
        name=f"test_{datetime.utcnow().isoformat()}",
        metadata={"test": "agentic"}
    )
    yield trace
    # Trace auto-closes on context exit


# Markers for different test layers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: Unit tests - pure Python, no Docker/LLM"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - real Docker, mocked LLM"
    )
    config.addinivalue_line(
        "markers", "agentic: Agentic tests - real Docker + real LLM + Langfuse"
    )
