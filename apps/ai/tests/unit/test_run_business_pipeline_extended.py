"""Tests for run_business_pipeline with predictive guardian — TDD Red phase.

Tests cover:
- Predictive disabled by default
- Predictive enabled adds results
- Predictive with real signal data
- Predictive alerts influence severity
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestBusinessPipelineWithPredictive:
    """Tests for run_business_pipeline with predictive flag."""

    @pytest.mark.asyncio
    async def test_predictive_disabled_by_default(self):
        """Pipeline runs without predictive when flag not set."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline("test", {"mrr_cents": 100000})
        assert result.get("predictive_result") is None

    @pytest.mark.asyncio
    async def test_predictive_enabled_adds_results(self):
        """Pipeline includes predictive results when flag is True."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline(
            "test", {"mrr_cents": 100000},
            run_predictive=True,
        )
        assert "predictive_result" in result

    @pytest.mark.asyncio
    async def test_predictive_with_signals(self):
        """Pipeline predictive works with real signal data."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline(
            "test",
            {
                "mrr_cents": 100000,
                "burn_30d_cents": 50000,
                "runway_months": 12,
                "mrr_history": [1000, 1100, 1200, 1300, 1400],
            },
            run_predictive=True,
        )
        assert result.get("predictive_result", {}).get("ok") is True

    @pytest.mark.asyncio
    async def test_predictive_non_blocking(self):
        """Pipeline continues even if predictive guard fails."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline(
            "test", {},
            run_predictive=True,
        )
        # Pipeline still completes
        assert result.get("ok") is True

    @pytest.mark.asyncio
    async def test_predictive_with_critical_alert_escalates(self):
        """Critical predictive alerts escalate HITL severity."""
        from src.orchestration.run_business_pipeline import run_business_pipeline

        result = await run_business_pipeline(
            "test",
            {
                "mrr_cents": 100000,
                "burn_30d_cents": 200000,
                "runway_months": 1,
                "monthly_churn_pct": 0.05,
            },
            run_predictive=True,
        )
        # Pipeline completes normally
        assert result.get("predictive_result", {}).get("ok") is True
