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
    """Real OpenAI client for health checks."""
    import openai
    return openai.OpenAI()


@pytest.fixture(scope="session")
def langfuse_client():
    """Real Langfuse client for trace verification."""
    from langfuse import Langfuse
    return Langfuse()


@pytest.fixture(scope="session")
def llm_model():
    """LLM model to use for agentic tests."""
    return os.environ.get("LLM_MODEL", "gpt-4o-mini")


@pytest.fixture
def trace_context(langfuse_client):
    """Create a Langfuse trace for the test."""
    trace = langfuse_client.trace(
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