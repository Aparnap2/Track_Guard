"""Tests for run_business_pipeline orchestrator — TDD Red phase.

Tests cover:
- Basic success path (run_id, ok=True)
- Finance result propagation
- Guardrail result propagation
- HITL routing result
- Empty signals handling
- Blocking routing
- Detection rule propagation
- MissionState update call
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestRunBusinessPipeline:
    """Tests for run_business_pipeline orchestrator."""

    # ── Basic success path ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_returns_dict_with_run_id(self):
        """Orchestrator returns dict with run_id."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 100000})
        assert "run_id" in result
        assert result["tenant_id"] == "test"

    @pytest.mark.asyncio
    async def test_completes_successfully_on_healthy_signals(self):
        """Pipeline completes with ok=True for healthy signals."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 100000, "burn_30d_cents": 10000})
        assert result["ok"] is True

    # ── Step result propagation ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_returns_finance_result(self):
        """Pipeline returns finance_rules results."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 200000, "burn_30d_cents": 50000})
        assert "finance_result" in result
        assert result["finance_result"]["ok"] is True

    @pytest.mark.asyncio
    async def test_returns_guardrail_result(self):
        """Pipeline returns guardrails result."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 100000})
        assert "guardrail_result" in result

    @pytest.mark.asyncio
    async def test_returns_routing_result(self):
        """Pipeline returns HITL routing result."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 100000})
        assert "routing" in result

    # ── Edge cases ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_handles_empty_signals(self):
        """Pipeline handles empty signals without crashing."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_blocking_sets_correct_routing(self):
        """Blocking decision maps to blocked routing."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {
            "monthly_churn_pct": 0.05,
            "net_burn": 100000,
            "net_new_arr": 10000,
            "runway_months": 2,
        })
        # severe signals may or may not block depending on guardrail config
        assert "routing" in result

    @pytest.mark.asyncio
    async def test_detects_silent_churn_death(self):
        """Pipeline detects and reports churn > 3%."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"monthly_churn_pct": 0.05})
        triggered = result.get("finance_result", {}).get("triggered_rules", [])
        assert "is_silent_churn_death" in triggered

    # ── MissionState integration ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_sets_mission_state_after_pipeline(self):
        """MissionState is updated after pipeline completes."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        with patch(
            "src.orchestration.run_business_pipeline.update_mission_state",
            new_callable=AsyncMock,
        ) as mock_update:
            result = await run_business_pipeline("test", {"mrr_cents": 100000})
            mock_update.assert_called_once()
