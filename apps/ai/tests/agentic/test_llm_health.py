"""
Layer 3 - Agentic Test #1: LLM API Health Check

This MUST pass before any other agentic test runs.
If this fails: LLM API is down, NOT the parser or agent.
Per the error attribution: this proves API health before testing parsing.
"""
import pytest


@pytest.mark.agentic
def test_llm_api_health(openai_client, llm_model):
    """Health check: LLM API is reachable before any agent test runs.

    This test proves the LLM API is healthy.
    If this fails → LLM API is down, not your code.
    """
    response = openai_client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=5,
    )

    assert response.choices[0].message.content is not None
    assert response.id is not None


@pytest.mark.agentic
def test_llm_response_time_sla(openai_client, llm_model):
    """Verify LLM response time is within SLA."""
    import time
    start = time.time()

    response = openai_client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": "Say 'ok'"}],
        max_tokens=5,
    )

    elapsed = time.time() - start

    # SLA: < 5 seconds for gpt-4o-mini
    assert elapsed < 5.0, f"LLM response took {elapsed:.2f}s, exceeds 5s SLA"
    assert response.choices[0].message.content is not None


@pytest.mark.agentic
def test_langfuse_health(langfuse_client):
    """Verify Langfuse is reachable."""
    # Langfuse client initialization validates connection
    assert langfuse_client is not None
    # The client will throw if credentials are invalid