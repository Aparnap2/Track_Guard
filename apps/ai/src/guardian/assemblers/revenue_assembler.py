"""Assembles RevenueState from HubSpot CRM + Stripe MRR snapshot dict."""
from __future__ import annotations
import logging
from typing import Any, Dict
from src.states.schemas import RevenueState, RevenueTrend

logger = logging.getLogger(__name__)


def _compute_revenue_trend(won_deals_30d_cents: int, pipeline_deals_cents: int) -> RevenueTrend:
    if won_deals_30d_cents > pipeline_deals_cents * 0.3:
        return RevenueTrend.GROWING
    if won_deals_30d_cents == 0 and pipeline_deals_cents > 0:
        return RevenueTrend.DECLINING
    return RevenueTrend.STABLE


def assemble_revenue_state(raw: Dict[str, Any]) -> RevenueState:
    total_deals_cents = raw.get("revenue_total_deals_cents", 0)
    won_deals_30d_cents = raw.get("revenue_won_deals_30d_cents", 0)
    pipeline_deals_cents = raw.get("revenue_pipeline_deals_cents", 0)
    active_customers = raw.get("revenue_active_customers", 0)
    mrr_cents = raw.get("revenue_mrr_cents")

    trend = _compute_revenue_trend(
        won_deals_30d_cents=won_deals_30d_cents,
        pipeline_deals_cents=pipeline_deals_cents,
    )

    return RevenueState(
        total_deals_cents=total_deals_cents,
        won_deals_30d_cents=won_deals_30d_cents,
        pipeline_deals_cents=pipeline_deals_cents,
        active_customers=active_customers,
        mrr_cents=mrr_cents,
        trend=trend,
    )
