"""
Finance Rules Activity for Temporal.

Wraps the 17 detection functions and 7 MBA primitives from
``src.business.finance_rules`` as a Temporal activity.

Pure deterministic logic — no LLM calls. Computes a FinancialSnapshot-compatible
dict from structured metrics signals.
"""
from __future__ import annotations

import logging
from typing import Any

from temporalio import activity

from src.business.finance_rules import (
    # Detection functions
    is_silent_churn_death,
    is_burn_multiple_creep,
    is_customer_concentration_risk,
    is_runway_compression_acceleration,
    is_failed_payment_cluster,
    is_payroll_revenue_breach,
    is_leaky_bucket_activation,
    is_power_user_mrr_masking,
    is_feature_adoption_drop,
    is_cohort_retention_degradation,
    is_nrr_below_100,
    is_trial_activation_wall,
    is_error_segment_correlation,
    is_support_outpacing_growth,
    is_cross_channel_bug_convergence,
    is_deploy_frequency_collapse,
    is_infra_unit_economics_divergence,
    # MBA primitives
    compute_burn_multiple,
    compute_runway_days,
    compute_effective_runway_days,
    compute_npv,
    compute_irr,
    compute_wacc,
    compute_working_capital_pressure,
)

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        log.debug("Heartbeat (no context): %s", message)


# ── Signal extraction helpers ─────────────────────────────────────────────


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


# ── Activity ──────────────────────────────────────────────────────────────


@activity.defn(name="run_finance_rules")
async def run_finance_rules(tenant_id: str, signals: dict) -> dict[str, Any]:
    """Compute FinancialSnapshot from structured metrics signals.

    Takes a signals dict (same format as guardian_signals from PulseAgent)
    and runs:

    1. All 17 detection functions against the signals.
    2. All 7 MBA primitives where data is available.
    3. Returns a FinancialSnapshot-compatible dict.

    Args:
        tenant_id: Tenant identifier.
        signals: dict with keys such as ``mrr_cents``, ``burn_30d_cents``,
            ``prev_burn_cents``, ``runway_months``, ``churn_pct``,
            ``monthly_churn_pct``, ``total_mrr``, ``top_customer_mrr``,
            ``net_burn``, ``net_new_arr``, etc.

    Returns:
        dict with:
        - ok: bool
        - tenant_id: str
        - snapshot: dict (FinancialSnapshot-compatible)
        - triggered_rules: list[str] (names of triggered detection functions)
        - error: str (only if ok=False)

    Note:
        Never raises — catches exceptions and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty", "tenant_id": ""}

    if not isinstance(signals, dict):
        return {"ok": False, "error": "signals must be a dict", "tenant_id": tenant_id}

    try:
        _safe_heartbeat(f"Running finance rules for tenant {tenant_id}")

        # ── 1. Extract key metrics with safe defaults ─────────────────────
        mrr_cents = _extract_float(signals, "mrr_cents", 0.0)
        burn_30d_cents = _extract_float(signals, "burn_30d_cents", 0.0)
        prev_burn_cents = _extract_float(signals, "prev_burn_cents", 0.0)
        runway_months = _extract_float(signals, "runway_months", 999.0)
        churn_pct = _extract_float(signals, "churn_pct", 0.0)
        monthly_churn_pct = _extract_float(signals, "monthly_churn_pct", churn_pct)
        total_mrr = _extract_float(signals, "total_mrr", mrr_cents)
        top_customer_mrr = _extract_float(signals, "top_customer_mrr", 0.0)
        net_burn = _extract_float(signals, "net_burn", burn_30d_cents)
        net_new_arr = _extract_float(signals, "net_new_arr", 0.0)
        burn_rate = _extract_float(signals, "burn_rate", burn_30d_cents)
        prev_burn_rate = _extract_float(signals, "prev_burn_rate", prev_burn_cents)

        # Extended metrics
        failed_payments_7d = _extract_int(signals, "failed_payments_7d", 0)
        payroll_monthly = _extract_float(signals, "payroll_monthly", 0.0)
        mrr_value = _extract_float(signals, "mrr", mrr_cents / 100.0)
        new_signups = _extract_int(signals, "new_signups", 0)
        activation_rate = _extract_float(signals, "activation_rate", 0.0)
        mrr_growth_pct = _extract_float(signals, "mrr_growth_pct", 0.0)
        top_10pct_mrr = _extract_float(signals, "top_10pct_mrr", 0.0)
        avg_mrr_new = _extract_float(signals, "avg_mrr_new", 0.0)
        avg_mrr_all = _extract_float(signals, "avg_mrr_all", 0.0)
        adoption_pre = _extract_float(signals, "adoption_pre", 0.0)
        adoption_post = _extract_float(signals, "adoption_post", 0.0)
        recent_retention = _extract_float(signals, "recent_retention", 0.0)
        prior_retention = _extract_float(signals, "prior_retention", 0.0)
        nrr = _extract_float(signals, "nrr", 100.0)
        support_growth_pct = _extract_float(signals, "support_growth_pct", 0.0)
        user_growth_pct = _extract_float(signals, "user_growth_pct", 0.0)
        deploys_this_month = _extract_int(signals, "deploys_this_month", 0)
        deploys_last_month = _extract_int(signals, "deploys_last_month", 0)
        aws_cost_growth_pct = _extract_float(signals, "aws_cost_growth_pct", 0.0)

        # Complex signal types
        trial_step_dropoffs = signals.get("trial_step_dropoffs", [])
        if not isinstance(trial_step_dropoffs, list):
            trial_step_dropoffs = []
        errors_by_segment = signals.get("errors_by_segment", [])
        if not isinstance(errors_by_segment, list):
            errors_by_segment = []
        bug_mentions_by_channel = signals.get("bug_mentions_by_channel", {})
        if not isinstance(bug_mentions_by_channel, dict):
            bug_mentions_by_channel = {}

        # Computed values
        computed_runway_days = int(runway_months * 30)

        # ── 2. Run detection functions ──────────────────────────────────
        triggered: list[str] = []

        if is_silent_churn_death(monthly_churn_pct):
            triggered.append("is_silent_churn_death")

        if is_burn_multiple_creep(net_burn, net_new_arr):
            triggered.append("is_burn_multiple_creep")

        if is_customer_concentration_risk(top_customer_mrr, total_mrr):
            triggered.append("is_customer_concentration_risk")

        if is_runway_compression_acceleration(burn_rate, prev_burn_rate, computed_runway_days):
            triggered.append("is_runway_compression_acceleration")

        if is_failed_payment_cluster(failed_payments_7d):
            triggered.append("is_failed_payment_cluster")

        if is_payroll_revenue_breach(payroll_monthly, mrr_value):
            triggered.append("is_payroll_revenue_breach")

        if is_leaky_bucket_activation(new_signups, activation_rate, mrr_growth_pct):
            triggered.append("is_leaky_bucket_activation")

        if is_power_user_mrr_masking(top_10pct_mrr, total_mrr, avg_mrr_new, avg_mrr_all):
            triggered.append("is_power_user_mrr_masking")

        if is_feature_adoption_drop(adoption_pre, adoption_post):
            triggered.append("is_feature_adoption_drop")

        if is_cohort_retention_degradation(recent_retention, prior_retention):
            triggered.append("is_cohort_retention_degradation")

        if is_nrr_below_100(nrr):
            triggered.append("is_nrr_below_100")

        if is_trial_activation_wall(trial_step_dropoffs):
            triggered.append("is_trial_activation_wall")

        if is_error_segment_correlation(errors_by_segment):
            triggered.append("is_error_segment_correlation")

        if is_support_outpacing_growth(support_growth_pct, user_growth_pct):
            triggered.append("is_support_outpacing_growth")

        if is_cross_channel_bug_convergence(bug_mentions_by_channel):
            triggered.append("is_cross_channel_bug_convergence")

        if is_deploy_frequency_collapse(deploys_this_month, deploys_last_month):
            triggered.append("is_deploy_frequency_collapse")

        if is_infra_unit_economics_divergence(aws_cost_growth_pct, user_growth_pct):
            triggered.append("is_infra_unit_economics_divergence")

        # ── 3. Compute MBA primitives ─────────────────────────────────────
        burn_multiple = compute_burn_multiple(net_burn, net_new_arr)

        bank_balance = _extract_float(signals, "bank_balance", 0.0)
        monthly_burn = burn_30d_cents / 100.0 if burn_30d_cents > 0 else 1.0
        basic_runway_days = compute_runway_days(bank_balance, monthly_burn)

        effective_runway_days = compute_effective_runway_days(
            computed_runway_days,
            int(signals.get("fundraising_months", 3)),
        )

        wacc_estimate = None
        if all(k in signals for k in ("equity_weight", "cost_of_equity", "debt_weight", "cost_of_debt", "tax_rate")):
            wacc_estimate = compute_wacc(
                _extract_float(signals, "equity_weight"),
                _extract_float(signals, "cost_of_equity"),
                _extract_float(signals, "debt_weight"),
                _extract_float(signals, "cost_of_debt"),
                _extract_float(signals, "tax_rate"),
            )

        npv_value = None
        cash_flows = signals.get("cash_flows", [])
        if isinstance(cash_flows, list) and len(cash_flows) > 0:
            discount_rate = _extract_float(signals, "discount_rate", 0.10)
            npv_value = compute_npv(cash_flows, discount_rate)

        irr_value = None
        if isinstance(cash_flows, list) and len(cash_flows) > 0:
            irr_value = compute_irr(cash_flows)

        wc_result = compute_working_capital_pressure(
            _extract_float(signals, "current_assets", 0.0),
            _extract_float(signals, "current_liabilities", 0.0),
            monthly_burn,
        )

        # ── 4. Build FinancialSnapshot-compatible dict ───────────────────
        mrr = mrr_cents / 100.0
        burn_rate_dollars = burn_30d_cents / 100.0

        snapshot = {
            "tenant_id": tenant_id,
            "mrr": round(mrr, 2),
            "burn_rate": round(burn_rate_dollars, 2),
            "runway_days": computed_runway_days,
            "effective_runway_days": effective_runway_days,
            "burn_multiple": round(burn_multiple, 2) if burn_multiple != float("inf") else None,
            "working_capital_ratio": round(wc_result["ratio"], 2),
            "wacc_estimate": round(wacc_estimate, 4) if wacc_estimate is not None else None,
            "npv": round(npv_value, 2) if npv_value is not None else None,
            "irr": round(irr_value, 6) if irr_value is not None else None,
            "basic_runway_days": basic_runway_days,
            "rule_anomalies": triggered,
        }

        _safe_heartbeat(f"Finance rules complete for tenant {tenant_id}")

        return {
            "ok": True,
            "tenant_id": tenant_id,
            "snapshot": snapshot,
            "triggered_rules": triggered,
        }

    except Exception as e:
        _safe_heartbeat(f"Finance rules failed for tenant {tenant_id}: {e}")
        log.exception("Finance rules error for tenant %s", tenant_id)
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
