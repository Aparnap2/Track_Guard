"""Tests for predictive engine — TDD Red phase.

Tests cover all 10 classes of forecasting functions:
1. linear_trend — OLS slope and intercept
2. predict_next — single-step and multi-step forecast
3. predict_series — multi-period forecast sequence
4. days_to_threshold — threshold breach timing
5. moving_average — sliding window average
6. compute_confidence_interval — CI bounds
7. compute_volatility — coefficient of variation
8. churn_acceleration_risk — churn trend detection
9. runway_depletion_date — trend-adjusted runway
10. compute_forecast_summary — complete metric summary
"""
from __future__ import annotations

import math
import pytest


# ═══════════════════════════════════════════════════════════════════════
# Test Class 1: LinearTrend
# ═══════════════════════════════════════════════════════════════════════


class TestLinearTrend:
    """Tests for linear_trend — OLS slope and intercept."""

    def test_linear_trend_positive_slope(self):
        """Rising values → positive slope ≈ 1.0, intercept ≈ 1.0."""
        from src.predictive.engine import linear_trend

        slope, intercept = linear_trend([1.0, 2.0, 3.0, 4.0, 5.0])
        assert slope == pytest.approx(1.0, abs=0.001)
        assert intercept == pytest.approx(1.0, abs=0.001)

    def test_linear_trend_negative_slope(self):
        """Falling values → negative slope ≈ -1.0."""
        from src.predictive.engine import linear_trend

        slope, intercept = linear_trend([5.0, 4.0, 3.0, 2.0, 1.0])
        assert slope == pytest.approx(-1.0, abs=0.001)

    def test_linear_trend_flat(self):
        """Flat values → slope ≈ 0.0."""
        from src.predictive.engine import linear_trend

        slope, intercept = linear_trend([3.0, 3.0, 3.0, 3.0])
        assert slope == pytest.approx(0.0, abs=0.001)
        assert intercept == pytest.approx(3.0, abs=0.001)

    def test_linear_trend_raises_on_single_point(self):
        """Single value raises ValueError."""
        from src.predictive.engine import linear_trend

        with pytest.raises(ValueError, match="at least 2 data points"):
            linear_trend([42.0])

    def test_linear_trend_raises_on_empty(self):
        """Empty list raises ValueError."""
        from src.predictive.engine import linear_trend

        with pytest.raises(ValueError, match="at least 2 data points"):
            linear_trend([])


# ═══════════════════════════════════════════════════════════════════════
# Test Class 2: PredictNext
# ═══════════════════════════════════════════════════════════════════════


class TestPredictNext:
    """Tests for predict_next — single/multi-period forecast."""

    def test_predict_next_positive_trend(self):
        """Rising values → next value ≈ 5.0."""
        from src.predictive.engine import predict_next

        result = predict_next([1.0, 2.0, 3.0, 4.0])
        assert result == pytest.approx(5.0, abs=0.1)

    def test_predict_next_negative_trend(self):
        """Falling values → next value ≈ 2.0."""
        from src.predictive.engine import predict_next

        result = predict_next([10.0, 8.0, 6.0, 4.0])
        assert result == pytest.approx(2.0, abs=0.1)

    def test_predict_next_multiple_periods(self):
        """periods_ahead=2 → ≈ 5.0."""
        from src.predictive.engine import predict_next

        result = predict_next([1.0, 2.0, 3.0], periods_ahead=2)
        assert result == pytest.approx(5.0, abs=0.1)

    def test_predict_next_single_value_raises(self):
        """Single value raises ValueError."""
        from src.predictive.engine import predict_next

        with pytest.raises(ValueError):
            predict_next([1.0])

    def test_predict_next_zero_periods_raises(self):
        """periods_ahead=0 raises ValueError."""
        from src.predictive.engine import predict_next

        with pytest.raises(ValueError):
            predict_next([1.0, 2.0, 3.0], periods_ahead=0)


# ═══════════════════════════════════════════════════════════════════════
# Test Class 3: PredictSeries
# ═══════════════════════════════════════════════════════════════════════


class TestPredictSeries:
    """Tests for predict_series — multi-period forecast sequence."""

    def test_predict_series_returns_correct_length(self):
        """Returns correct number of predicted values."""
        from src.predictive.engine import predict_series

        result = predict_series([1.0, 2.0, 3.0], periods_ahead=3)
        assert len(result) == 3

    def test_predict_series_values(self):
        """Values increase stepwise ≈ [5.0, 6.0]."""
        from src.predictive.engine import predict_series

        result = predict_series([1.0, 2.0, 3.0, 4.0], periods_ahead=2)
        assert result[0] == pytest.approx(5.0, abs=0.1)
        assert result[1] == pytest.approx(6.0, abs=0.1)

    def test_predict_series_zero_periods_raises(self):
        """periods_ahead=0 raises ValueError."""
        from src.predictive.engine import predict_series

        with pytest.raises(ValueError):
            predict_series([1.0, 2.0, 3.0], periods_ahead=0)


# ═══════════════════════════════════════════════════════════════════════
# Test Class 4: DaysToThreshold
# ═══════════════════════════════════════════════════════════════════════


class TestDaysToThreshold:
    """Tests for days_to_threshold — threshold breach timing."""

    def test_days_to_threshold_above(self):
        """Rising trend crossing above threshold → 5 periods."""
        from src.predictive.engine import days_to_threshold

        result = days_to_threshold(
            current_value=10.0,
            historical_values=[5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            threshold=15.0,
            above=True,
        )
        assert result == 5

    def test_days_to_threshold_below(self):
        """Falling trend crossing below threshold → 5 periods."""
        from src.predictive.engine import days_to_threshold

        result = days_to_threshold(
            current_value=10.0,
            historical_values=[15.0, 14.0, 13.0, 12.0, 11.0, 10.0],
            threshold=5.0,
            above=False,
        )
        assert result == 5

    def test_days_to_threshold_never_crosses(self):
        """Trend moving away from threshold → None."""
        from src.predictive.engine import days_to_threshold

        # Declining values, threshold above
        result = days_to_threshold(
            current_value=5.0,
            historical_values=[10.0, 9.0, 8.0, 7.0, 6.0, 5.0],
            threshold=15.0,
            above=True,
        )
        assert result is None

    def test_days_to_threshold_already_past_above(self):
        """Already above threshold → 0."""
        from src.predictive.engine import days_to_threshold

        result = days_to_threshold(
            current_value=20.0,
            historical_values=[5.0, 10.0, 15.0, 20.0],
            threshold=15.0,
            above=True,
        )
        assert result == 0

    def test_days_to_threshold_already_past_below(self):
        """Already below threshold → 0."""
        from src.predictive.engine import days_to_threshold

        result = days_to_threshold(
            current_value=2.0,
            historical_values=[10.0, 8.0, 6.0, 4.0, 2.0],
            threshold=5.0,
            above=False,
        )
        assert result == 0

    def test_days_to_threshold_insufficient_data(self):
        """Less than 2 historical points → None."""
        from src.predictive.engine import days_to_threshold

        result = days_to_threshold(
            current_value=10.0,
            historical_values=[10.0],
            threshold=15.0,
            above=True,
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Test Class 5: MovingAverage
# ═══════════════════════════════════════════════════════════════════════


class TestMovingAverage:
    """Tests for moving_average — sliding window average."""

    def test_moving_average_basic(self):
        """Window=3 on 5 values → 3 averaged values."""
        from src.predictive.engine import moving_average

        result = moving_average([1.0, 2.0, 3.0, 4.0, 5.0], window=3)
        assert result == pytest.approx([2.0, 3.0, 4.0], abs=0.001)

    def test_moving_average_window_too_large(self):
        """Window larger than data → empty list."""
        from src.predictive.engine import moving_average

        result = moving_average([1.0, 2.0], window=3)
        assert result == []

    def test_moving_average_window_equals_length(self):
        """Window == len(values) → single average value."""
        from src.predictive.engine import moving_average

        result = moving_average([1.0, 2.0, 3.0], window=3)
        assert result == pytest.approx([2.0], abs=0.001)

    def test_moving_average_window_one(self):
        """Window=1 returns original values."""
        from src.predictive.engine import moving_average

        result = moving_average([10.0, 20.0, 30.0], window=1)
        assert result == pytest.approx([10.0, 20.0, 30.0], abs=0.001)


# ═══════════════════════════════════════════════════════════════════════
# Test Class 6: ConfidenceInterval
# ═══════════════════════════════════════════════════════════════════════


class TestConfidenceInterval:
    """Tests for compute_confidence_interval — CI bounds."""

    def test_confidence_interval_basic(self):
        """95% CI on sample data → lower < mean < upper."""
        from src.predictive.engine import compute_confidence_interval

        lower, upper = compute_confidence_interval([10.0, 12.0, 11.0, 13.0, 10.0])
        mean = 11.2
        assert lower < mean < upper
        assert lower < upper

    def test_confidence_interval_single_value(self):
        """Single value → (value, value)."""
        from src.predictive.engine import compute_confidence_interval

        lower, upper = compute_confidence_interval([5.0])
        assert lower == 5.0
        assert upper == 5.0

    def test_confidence_interval_empty(self):
        """Empty list → (0.0, 0.0)."""
        from src.predictive.engine import compute_confidence_interval

        lower, upper = compute_confidence_interval([])
        assert lower == 0.0
        assert upper == 0.0

    def test_confidence_interval_80_pct(self):
        """80% CI uses z=1.282 → narrower than 95%."""
        from src.predictive.engine import compute_confidence_interval

        lower80, upper80 = compute_confidence_interval(
            [10.0, 12.0, 11.0, 13.0, 10.0], confidence=0.80
        )
        lower95, upper95 = compute_confidence_interval(
            [10.0, 12.0, 11.0, 13.0, 10.0], confidence=0.95
        )
        # 80% CI should be narrower than 95% CI
        assert (upper80 - lower80) < (upper95 - lower95)


# ═══════════════════════════════════════════════════════════════════════
# Test Class 7: Volatility
# ═══════════════════════════════════════════════════════════════════════


class TestVolatility:
    """Tests for compute_volatility — coefficient of variation."""

    def test_volatility_low(self):
        """Values close to mean → low CV."""
        from src.predictive.engine import compute_volatility

        vol = compute_volatility([100.0, 101.0, 99.0, 100.0, 100.5])
        assert vol < 0.01

    def test_volatility_high(self):
        """Values with high variance → high CV."""
        from src.predictive.engine import compute_volatility

        vol = compute_volatility([50.0, 150.0, 80.0, 120.0, 100.0])
        assert vol > 0.1

    def test_volatility_zero_mean(self):
        """All zeros → 0.0."""
        from src.predictive.engine import compute_volatility

        vol = compute_volatility([0.0, 0.0, 0.0])
        assert vol == 0.0

    def test_volatility_single_value(self):
        """Single value → 0.0."""
        from src.predictive.engine import compute_volatility

        vol = compute_volatility([42.0])
        assert vol == 0.0

    def test_volatility_empty(self):
        """Empty list → 0.0."""
        from src.predictive.engine import compute_volatility

        vol = compute_volatility([])
        assert vol == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Test Class 8: ChurnAccelerationRisk
# ═══════════════════════════════════════════════════════════════════════


class TestChurnAccelerationRisk:
    """Tests for churn_acceleration_risk — churn trend detection."""

    def test_churn_acceleration_detected(self):
        """Accelerating churn → risk_level at least medium."""
        from src.predictive.engine import churn_acceleration_risk

        result = churn_acceleration_risk(
            [0.01, 0.015, 0.02, 0.025, 0.03, 0.035]
        )
        assert result["risk_level"] in ("medium", "high", "critical")
        assert result["overall_slope"] > 0

    def test_churn_no_acceleration(self):
        """Declining churn → risk_level is low."""
        from src.predictive.engine import churn_acceleration_risk

        result = churn_acceleration_risk(
            [0.03, 0.025, 0.02, 0.015]
        )
        assert result["risk_level"] == "low"
        assert result["accelerating"] is False

    def test_churn_insufficient_data(self):
        """Less than 4 points → risk_level is low."""
        from src.predictive.engine import churn_acceleration_risk

        result = churn_acceleration_risk([0.01, 0.02, 0.03])
        assert result["risk_level"] == "low"

    def test_churn_returns_all_expected_keys(self):
        """Result dict has all required fields."""
        from src.predictive.engine import churn_acceleration_risk

        result = churn_acceleration_risk([0.01, 0.02, 0.03, 0.04])
        assert "accelerating" in result
        assert "overall_slope" in result
        assert "recent_slope" in result
        assert "risk_level" in result
        assert "description" in result


# ═══════════════════════════════════════════════════════════════════════
# Test Class 9: RunwayDepletionDate
# ═══════════════════════════════════════════════════════════════════════


class TestRunwayDepletionDate:
    """Tests for runway_depletion_date — trend-adjusted runway."""

    def test_runway_depletion_basic(self):
        """No trends → base_runway_days matches input."""
        from src.predictive.engine import runway_depletion_date

        result = runway_depletion_date(
            current_burn_rate=10000.0,
            current_runway_days=300,
        )
        assert result["base_runway_days"] == 300
        assert "adjusted_runway_days" in result
        assert "confidence" in result

    def test_runway_depletion_with_growth(self):
        """MRR growing → adjusted_runway >= base_runway."""
        from src.predictive.engine import runway_depletion_date

        result = runway_depletion_date(
            current_burn_rate=50000.0,
            current_runway_days=300,
            mrr_growth_trend=[1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
        )
        assert result["adjusted_runway_days"] >= result["base_runway_days"]

    def test_runway_depletion_with_burn_acceleration(self):
        """Burn accelerating → adjusted_runway <= base_runway."""
        from src.predictive.engine import runway_depletion_date

        result = runway_depletion_date(
            current_burn_rate=50000.0,
            current_runway_days=300,
            burn_growth_trend=[10000.0, 11000.0, 12000.0, 13000.0],
        )
        assert result["adjusted_runway_days"] <= result["base_runway_days"]

    def test_runway_depletion_returns_expected_keys(self):
        """Result dict has all required fields."""
        from src.predictive.engine import runway_depletion_date

        result = runway_depletion_date(
            current_burn_rate=10000.0,
            current_runway_days=300,
        )
        assert "base_runway_days" in result
        assert "adjusted_runway_days" in result
        assert "depletion_date_description" in result
        assert "confidence" in result
        assert "burn_trend" in result
        assert "mrr_trend" in result


# ═══════════════════════════════════════════════════════════════════════
# Test Class 10: ForecastSummary
# ═══════════════════════════════════════════════════════════════════════


class TestForecastSummary:
    """Tests for compute_forecast_summary — complete metric summary."""

    def test_forecast_summary_basic(self):
        """Returns dict with all expected keys."""
        from src.predictive.engine import compute_forecast_summary

        result = compute_forecast_summary([10.0, 20.0, 30.0, 40.0], label="mrr")
        assert "label" in result
        assert "current" in result
        assert "trend" in result
        assert "next_prediction" in result
        assert "confidence_interval" in result
        assert "volatility" in result
        assert "moving_average" in result
        assert "data_points" in result
        assert result["label"] == "mrr"

    def test_forecast_summary_trend_improving(self):
        """Rising values → trend='improving'."""
        from src.predictive.engine import compute_forecast_summary

        result = compute_forecast_summary([10.0, 20.0, 30.0, 40.0, 50.0])
        assert result["trend"] == "improving"

    def test_forecast_summary_trend_declining(self):
        """Falling values → trend='declining'."""
        from src.predictive.engine import compute_forecast_summary

        result = compute_forecast_summary([50.0, 40.0, 30.0, 20.0, 10.0])
        assert result["trend"] == "declining"

    def test_forecast_summary_data_points(self):
        """data_points matches input length."""
        from src.predictive.engine import compute_forecast_summary

        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        result = compute_forecast_summary(values)
        assert result["data_points"] == len(values)

    def test_forecast_summary_current_is_last_value(self):
        """current equals the last value in the series."""
        from src.predictive.engine import compute_forecast_summary

        result = compute_forecast_summary([10.0, 25.0, 35.0])
        assert result["current"] == 35.0
