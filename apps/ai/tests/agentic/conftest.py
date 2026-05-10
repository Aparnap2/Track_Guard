"""
Agentic Test Configuration - Real LLM + Real Docker + Langfuse

Per the TDD strategy: Layer 3 tests prove the real system works.
These tests require OPENAI_API_KEY and LANGFUSE_SECRET_KEY.
"""
import os
import pytest
from datetime import datetime


@pytest.fixture(scope="session")
def openai_client():
    """Real OpenAI-compatible client for health checks (supports Ollama, Groq, Azure)."""
    import openai
    
    # Check if Ollama is configured
    if os.environ.get("OLLAMA_BASE_URL"):
        base_url = os.environ["OLLAMA_BASE_URL"]
        # Cloud uses https://ollama.com, local uses http://localhost:11434
        # Add /v1 suffix for OpenAI-compatible SDK
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/")
            if "/api" in base_url:
                base_url = base_url.replace("/api", "/v1")
            elif not "/v1" in base_url:
                base_url = base_url + "/v1"
        return openai.OpenAI(
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
        )
    
    # Fallback to original behavior for OpenAI/Azure/Groq
    return openai.OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "dummy-key"),
    )


@pytest.fixture(scope="session")
def langfuse_client():
    """Real Langfuse client for trace verification."""
    from langfuse import Langfuse
    # New Langfuse SDK auto-reads env vars: LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST
    return Langfuse()


@pytest.fixture(scope="session")
def llm_model():
    """LLM model to use for agentic tests."""
    # For Ollama, use OLLAMA_CHAT_MODEL if set, otherwise fallback
    if os.environ.get("OLLAMA_BASE_URL"):
        return os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:0.6b")
    return os.environ.get("LLM_MODEL", "gpt-4o-mini")


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
