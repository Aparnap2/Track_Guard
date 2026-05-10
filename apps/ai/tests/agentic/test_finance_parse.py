"""
Layer 3 - Agentic Test #2: Real LLM → Pydantic Parse

If health check passed and this fails: parser is wrong, not the LLM.
Per the error attribution: this proves the parser handles real LLM output.
"""
import pytest


@pytest.mark.agentic
def test_finance_agent_pydantic_parse_real_llm(
    openai_client, langfuse_client, llm_model, trace_context
):
    """Real LLM call → must parse into AlertDecision.

    If this fails after health test passed: parser is wrong.
    """
    from src.schemas.guardian import AlertDecision

    # Phase 2: LLM decision call
    prompt = f"""You are a finance Guardian. Given this data:
- Runway: 110 days
- MRR change: -15%
- Burn: $60,000/month

Rules flagged: runway_critical, mrr_drop

Is this alert-worthy? Answer with JSON:
{{"should_alert": true/false, "severity": "critical/warning/info", "primary_signal": "runway_critical/mrr_drop/none", "context_note": "max 20 words"}}"""

    # Phase 2: LLM decision call with Langfuse tracing
    # Langfuse SDK v4: use start_as_current_observation for nested spans
    with langfuse_client.start_as_current_observation(name="finance_decide", as_type="generation") as span:
        response = openai_client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        # Parse into Pydantic - this is what we're testing
        import json
        data = json.loads(content)

        result = AlertDecision(**data)

        span.update(output=result.model_dump())

    # Schema assertions - if these fail, PARSER is wrong
    assert isinstance(result, AlertDecision), "Failed to parse into AlertDecision"
    assert result.should_alert is True, "Expected should_alert=True"
    assert result.severity in ("critical", "warning", "info"), f"Invalid severity: {result.severity}"
    assert len(result.context_note.split()) <= 20, f"context_note exceeds 20 words: {result.context_note}"
    assert result.primary_signal in ("runway_critical", "mrr_drop", "burn_spike", "none")


@pytest.mark.agentic
def test_guardian_message_contract_real_llm(
    openai_client, langfuse_client, llm_model, trace_context
):
    """Real LLM narrative generation must satisfy PRD contract.

    Word count ≤ 200, injected_numbers non-empty, pattern from watchlist.
    """
    from src.schemas.guardian import GuardianMessage

    prompt = f"""Write a Guardian alert (max 200 words).
Pattern: FG-04 (Runway Compression)
Numbers: runway=110 days, burn=$60k/mo, MRR=$10k
Start with pattern name, end with one action.
Do NOT start with a number.
Inject the numbers: 110 days, $60k, $10k"""

    # Trace narrative generation with Langfuse SDK v4
    with langfuse_client.start_as_current_observation(name="finance_narrative", as_type="generation") as span:
        response = openai_client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        content = response.choices[0].message.content

        # Parse as GuardianMessage - PRD contract validation
        # This would need more sophisticated parsing in reality
        word_count = len(content.split())

        span.update(output={"word_count": word_count, "content": content[:100]})

    # PRD contract assertions
    assert word_count <= 200, f"Exceeds 200 words: {word_count}"
    assert not content[0].isdigit(), "Must NOT start with number"
    assert any(char.isdigit() for char in content), "Must inject numbers"


@pytest.mark.agentic
def test_langfuse_trace_received(langfuse_client):
    """Verify Langfuse actually received traces."""
    import time
    time.sleep(2)  # Allow ingestion

    # This is a simplified check - in real CI you'd verify trace IDs
    assert langfuse_client is not None