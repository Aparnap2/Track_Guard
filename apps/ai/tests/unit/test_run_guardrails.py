"""Tests for run_guardrails activity — TDD Red phase.

Tests cover:
- Basic success path (ok=True)
- GuardrailResult field coverage
- Healthy envelope auto-approval
- Critical severity blocking
- Investor-facing flagging
- Malformed envelope handling
- Risk classification
"""
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Test Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_minimal_envelope_dict() -> dict:
    """Create a minimal healthy envelope dict for testing."""
    return {
        "event": {
            "tenant_id": "test",
            "event_type": "test",
            "source": "stripe",
            "payload_ref": "pg:test",
            "payload_hash": "abc",
            "idempotency_key": "k1",
            "occurred_at": "2025-01-01T00:00:00",
            "received_at": "2025-01-01T00:00:00",
            "trace_id": "t1",
        },
        "decision": {
            "should_alert": True,
            "severity": "info",
            "primary_signal": "test signal",
            "context_note": "test context",
        },
        "finance_snapshot": {
            "tenant_id": "test",
            "mrr": 100000,
            "burn_rate": 10000,
            "runway_days": 300,
            "effective_runway_days": 210,
            "burn_multiple": 1.0,
            "working_capital_ratio": 2.0,
            "wacc_estimate": 0.1,
        },
        "guardrail_status": {
            "approval_tier": "auto",
            "reversible": True,
            "risk_type": "none",
            "authority_required": "none",
            "blocking": False,
            "privacy_sensitive": False,
            "investor_facing": False,
        },
        "domain": "finance",
        "reversible": True,
        "approval_tier": "auto",
    }


def _make_critical_envelope_dict() -> dict:
    """Create a critical-severity envelope dict with high burn."""
    d = _make_minimal_envelope_dict()
    d["decision"]["severity"] = "critical"
    d["finance_snapshot"]["burn_multiple"] = 3.0
    d["finance_snapshot"]["runway_days"] = 90
    return d


def _make_healthy_envelope_dict() -> dict:
    """Create a healthy envelope that should auto-approve."""
    return _make_minimal_envelope_dict()


def _make_investor_facing_envelope_dict() -> dict:
    """Create an envelope with investor-facing conditions."""
    d = _make_minimal_envelope_dict()
    d["decision"]["severity"] = "warning"
    d["finance_snapshot"]["burn_multiple"] = 2.5
    d["finance_snapshot"]["runway_days"] = 150
    return d


def _make_finance_risk_envelope_dict() -> dict:
    """Create an envelope that should classify as financial risk."""
    d = _make_critical_envelope_dict()
    d["finance_snapshot"]["burn_rate"] = 50000
    return d


# ═══════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRunGuardrails:
    """Tests for run_guardrails activity."""

    # ── Basic success path ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_returns_dict_with_ok(self):
        """Activity returns ok=True on success."""
        from src.activities.run_guardrails import run_guardrails

        envelope = _make_minimal_envelope_dict()
        result = await run_guardrails("test", envelope)
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_returns_guardrail_result_with_all_fields(self):
        """Returns GuardrailResult-compatible dict."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", _make_minimal_envelope_dict())
        gr = result["guardrail_result"]
        assert "approval_tier" in gr
        assert "reversible" in gr
        assert "risk_type" in gr
        assert "blocking" in gr
        assert "authority_required" in gr

    # ── Approval tier behavior ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_equal_weight_envelope_auto_approves(self):
        """Healthy envelope passes with auto approval."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", _make_healthy_envelope_dict())
        assert result["guardrail_result"]["approval_tier"] == "auto"
        assert result["guardrail_result"]["blocking"] is False

    @pytest.mark.asyncio
    async def test_critical_severity_blocking(self):
        """Critical severity + high burn triggers blocking."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", _make_critical_envelope_dict())
        assert result["guardrail_result"]["approval_tier"] == "blocking"

    # ── Investor-facing flag ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_investor_facing_flagged(self):
        """Finance warning with high burn marks investor_facing."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", _make_investor_facing_envelope_dict())
        assert result["guardrail_result"]["investor_facing"] is True

    # ── Error handling ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_handles_malformed_envelope(self):
        """Returns ok=False for bad input instead of crashing."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", {"bad": "data"})
        assert result["ok"] is False

    # ── Risk classification ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_risk_classification_financial(self):
        """Finance domain with burn alert gets risk_type=financial."""
        from src.activities.run_guardrails import run_guardrails

        result = await run_guardrails("test", _make_finance_risk_envelope_dict())
        assert result["guardrail_result"]["risk_type"] == "financial"
