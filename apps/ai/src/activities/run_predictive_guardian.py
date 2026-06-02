"""Predictive Guardian activity — forecasts finance metric trends.

Wraps the forecasting engine as a Temporal activity.

V4 scope: deterministic trend extrapolation — no LLM, no ML.
"""
from __future__ import annotations

import logging
from typing import Any

from temporalio import activity

from src.predictive.engine import (
    churn_acceleration_risk,
    compute_forecast_summary,
    runway_depletion_date,
)

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        log.debug("Heartbeat (no context): %s", message)


def _extract_float_list(signals: dict, key: str) -> list[float]:
    """Extract a list of floats from signals dict with safe default."""
    val = signals.get(key, [])
    if not isinstance(val, list):
        return []
    return [float(v) for v in val if isinstance(v, (int, float))]


def _extract_float(signals: dict, key: str, default: float = 0.0) -> float:
    """Extract a float value from signals dict with safe default."""
    val = signals.get(key, default)
    if val is None:
        return default
    return float(val)


def _extract_int(signals: dict, key: str, default: int = 0) -> int:
    """Extract an int value from signals dict with safe default."""
    val = signals.get(key, default)
    if val is None:
        return default
    return int(val)


def _build_alert(
    metric: str,
    severity: str,
    current_value: float,
    predicted_value: float | None = None,
    threshold: float | None = None,
    days_until: int | None = None,
    description: str = "",
    confidence: str = "medium",
) -> dict[str, Any]:
    """Build a PredictiveAlert-compatible dict."""
    return {
        "should_alert": True,
        "metric": metric,
        "severity": severity,
        "current_value": current_value,
        "predicted_value": predicted_value or current_value,
        "threshold": threshold,
        "days_until_crossing": days_until,
        "description": description,
        "confidence": confidence,
    }


@activity.defn(name="run_predictive_guardian")
async def run_predictive_guardian(
    tenant_id: str,
    signals: dict,
) -> dict[str, Any]:
    """Run predictive guardian — forecast metric trends and generate alerts.

    Takes structured signals (same format as finance_rules) and computes:
    1. Trend forecasts for each available metric
    2. Runway depletion projection
    3. Churn acceleration detection
    4. Predictive alerts for metrics approaching critical thresholds

    Args:
        tenant_id: Tenant identifier.
        signals: dict with historical values keyed by metric name.
                Supports: mrr_history (list), burn_history (list),
                churn_history (list), runway_days (int), burn_30d_cents (float),
                monthly_churn_pct (float).

    Returns:
        dict with:
        - ok: bool
        - tenant_id: str
        - forecasts: list of MetricForecast-compatible dicts
        - alerts: list of PredictiveAlert-compatible dicts
        - runway_forecast: RunwayForecast-compatible dict or None
        - churn_forecast: ChurnForecast-compatible dict or None
        - error: str (only if ok=False)

    Note:
        Never raises — catches exceptions and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {
            "ok": False,
            "error": "tenant_id is required and cannot be empty",
            "tenant_id": "",
        }

    try:
        _safe_heartbeat(f"Running predictive guardian for tenant {tenant_id}")

        # ── 1. Extract historical series ────────────────────────────────────
        mrr_history = _extract_float_list(signals, "mrr_history")
        burn_history = _extract_float_list(signals, "burn_history")
        churn_history = _extract_float_list(signals, "churn_history")

        runway_days = _extract_int(signals, "runway_days", 0)
        burn_30d = _extract_float(signals, "burn_30d_cents", 0.0)
        monthly_churn = _extract_float(signals, "monthly_churn_pct", 0.0)
        current_mrr = _extract_float(signals, "mrr_cents", 0.0)

        # ── 2. Compute forecasts for each available metric ──────────────────
        forecasts: list[dict[str, Any]] = []

        if len(mrr_history) >= 2:
            mrr_summary = compute_forecast_summary(mrr_history, label="mrr")
            forecasts.append(mrr_summary)

        if len(burn_history) >= 2:
            burn_summary = compute_forecast_summary(burn_history, label="burn")
            forecasts.append(burn_summary)

        if len(churn_history) >= 2:
            churn_summary = compute_forecast_summary(churn_history, label="churn")
            forecasts.append(churn_summary)

        # ── 3. Churn acceleration detection ─────────────────────────────────
        churn_result = None
        if len(churn_history) >= 4:
            churn_result = churn_acceleration_risk(churn_history)
        elif len(churn_history) >= 2:
            # Basic churn assessment with limited data
            overall_slope, _ = _safe_trend(churn_history)
            churn_result = {
                "accelerating": False,
                "overall_slope": round(overall_slope, 10),
                "recent_slope": 0.0,
                "risk_level": "low" if overall_slope <= 0 else "medium",
                "description": (
                    "Churn trend positive but insufficient data for acceleration analysis."
                    if overall_slope > 0
                    else "Insufficient churn data for full acceleration analysis."
                ),
            }

        # ── 4. Runway depletion projection ─────────────────────────────────
        runway_result = None
        if burn_30d > 0 and runway_days > 0:
            mrr_trend_raw = mrr_history if len(mrr_history) >= 2 else None
            burn_trend_raw = burn_history if len(burn_history) >= 2 else None

            runway_result = runway_depletion_date(
                current_burn_rate=burn_30d,
                current_runway_days=runway_days,
                mrr_growth_trend=mrr_trend_raw,
                burn_growth_trend=burn_trend_raw,
            )

        # ── 5. Generate alerts for critical thresholds ─────────────────────
        alerts: list[dict[str, Any]] = []

        # Check runway threshold (< 90 days = critical, < 180 = warning)
        if runway_days > 0:
            if runway_days < 90:
                alerts.append(_build_alert(
                    metric="runway",
                    severity="critical",
                    current_value=float(runway_days),
                    threshold=90.0,
                    days_until=0,
                    description=f"Runway critically low: {runway_days} days (< 90).",
                    confidence="high",
                ))
            elif runway_days < 180:
                alerts.append(_build_alert(
                    metric="runway",
                    severity="warning",
                    current_value=float(runway_days),
                    threshold=180.0,
                    days_until=runway_days - 90,
                    description=f"Runway running low: {runway_days} days (< 180).",
                    confidence="high",
                ))

        # Check burn rate vs MRR (burn > 2x revenue)
        if burn_30d > 0 and current_mrr > 0:
            burn_ratio = burn_30d / current_mrr
            if burn_ratio > 2.0:
                alerts.append(_build_alert(
                    metric="burn_multiple",
                    severity="critical",
                    current_value=burn_30d,
                    predicted_value=burn_30d,
                    threshold=current_mrr * 2,
                    description=f"Burn ({burn_30d:.0f}) exceeds 2x MRR ({current_mrr:.0f}).",
                    confidence="high",
                ))

        # Check churn > 3% threshold
        if monthly_churn > 0.03:
            alerts.append(_build_alert(
                metric="monthly_churn",
                severity="critical",
                current_value=monthly_churn,
                threshold=0.03,
                description=f"Monthly churn {monthly_churn:.1%} exceeds 3% threshold.",
                confidence="high",
            ))

        # Check churn acceleration alerts
        if churn_result and churn_result.get("accelerating"):
            alerts.append(_build_alert(
                metric="churn_acceleration",
                severity="warning",
                current_value=churn_result.get("recent_slope", 0.0),
                threshold=churn_result.get("overall_slope", 0.0) * 1.5,
                description=churn_result.get("description", "Churn is accelerating."),
                confidence="medium",
            ))

        # Check MRR decline forecast
        mrr_forecast = next(
            (f for f in forecasts if f.get("label") == "mrr"), None
        )
        if mrr_forecast and mrr_forecast.get("trend") == "declining":
            alerts.append(_build_alert(
                metric="mrr_trend",
                severity="warning",
                current_value=mrr_forecast.get("current", 0.0),
                predicted_value=mrr_forecast.get("next_prediction", 0.0),
                description="MRR trending downward — forecast predicts continued decline.",
                confidence="medium",
            ))

        _safe_heartbeat(f"Predictive guardian complete for tenant {tenant_id}")

        return {
            "ok": True,
            "tenant_id": tenant_id,
            "forecasts": forecasts,
            "alerts": alerts,
            "runway_forecast": runway_result,
            "churn_forecast": churn_result,
        }

    except Exception as e:
        _safe_heartbeat(f"Predictive guardian failed for tenant {tenant_id}: {e}")
        log.exception("Predictive guardian error for tenant %s", tenant_id)
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}


def _safe_trend(
    values: list[float],
) -> tuple[float, float]:
    """Compute linear trend safely, returning (0, 0) on error."""
    try:
        from src.predictive.engine import linear_trend

        return linear_trend(values)
    except (ValueError, ZeroDivisionError):
        return (0.0, 0.0)
