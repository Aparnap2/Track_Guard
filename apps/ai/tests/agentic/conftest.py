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