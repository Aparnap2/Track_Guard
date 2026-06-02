"""Tests for run_predictive_guardian activity — TDD Red phase.

Tests cover:
- Basic success path (ok=True, tenant_id matching)
- Forecast generation for MRR history
- Churn acceleration detection
- Alert generation on critical thresholds
- Empty signals handling
- Runway forecast computation
- Alert field completeness
"""
import pytest


class TestRunPredictiveGuardian:
    """Tests for run_predictive_guardian activity."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_ok(self):
        """Activity returns dict with ok=True on success."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test-tenant", {})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_returns_forecasts_list(self):
        """Returns forecasts list for MRR history."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian(
            "test", {"mrr_history": [100, 110, 120, 130]}
        )
        assert "forecasts" in result
        assert len(result["forecasts"]) >= 1

    @pytest.mark.asyncio
    async def test_detects_churn_acceleration(self):
        """Detects churn acceleration from history."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "churn_history": [0.01, 0.02, 0.03, 0.04, 0.05],
        })
        churn = result.get("churn_forecast", {})
        assert churn.get("accelerating") is True

    @pytest.mark.asyncio
    async def test_generates_alerts_on_critical_thresholds(self):
        """Generates alerts for critical runway."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "runway_days": 60,
            "burn_30d_cents": 100000,
        })
        assert len(result.get("alerts", [])) >= 1

    @pytest.mark.asyncio
    async def test_handles_empty_signals_gracefully(self):
        """Empty signals produce ok=True with no alerts."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {})
        assert result["ok"] is True
        assert result.get("alerts") == []

    @pytest.mark.asyncio
    async def test_computes_runway_forecast(self):
        """Runway forecast has correct base_runway_days."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "runway_days": 300,
            "burn_30d_cents": 50000,
        })
        forecast = result.get("runway_forecast", {})
        assert forecast.get("base_runway_days") == 300

    @pytest.mark.asyncio
    async def test_alerts_contain_required_fields(self):
        """Each alert has metric, severity, description, should_alert."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "runway_days": 60,
            "burn_30d_cents": 100000,
            "monthly_churn_pct": 0.05,
        })
        for alert in result.get("alerts", []):
            assert "metric" in alert
            assert "severity" in alert
            assert "description" in alert
            assert "should_alert" in alert

    @pytest.mark.asyncio
    async def test_includes_forecast_summary_for_mrr(self):
        """MRR forecast has improving trend for rising values."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "mrr_history": [1000, 1100, 1200, 1300, 1400],
        })
        forecasts = result.get("forecasts", [])
        mrr_forecast = next(
            (f for f in forecasts if f.get("label") == "mrr"), None
        )
        assert mrr_forecast is not None
        assert mrr_forecast["trend"] == "improving"

    @pytest.mark.asyncio
    async def test_forecasts_for_multiple_metrics(self):
        """Multiple histories produce multiple forecasts."""
        from src.activities.run_predictive_guardian import run_predictive_guardian

        result = await run_predictive_guardian("test", {
            "mrr_history": [1000, 1100, 1200],
            "burn_history": [500, 520, 540],
        })
        assert len(result.get("forecasts", [])) >= 2
