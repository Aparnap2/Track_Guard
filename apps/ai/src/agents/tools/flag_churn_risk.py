"""Tool: flag_churn_risk_customer — HITL Tier: auto.

Auto-executes for BG-06 (trial activation wall) or BG-04 (cohort
retention degradation). Flags the segment in the customer DB so
the dashboard and alerting pipeline can prioritize monitoring.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "flag_churn_risk_customer",
    "description": "Flag a customer segment as churn risk in the database",
    "hitl_tier": "auto",
    "trigger_patterns": ["BG-06", "BG-04"],
}


async def execute(tenant_id: str, segment_id: str) -> dict[str, Any]:
    """Flag a segment for churn risk monitoring.

    Args:
        tenant_id: Tenant identifier.
        segment_id: Customer segment ID to flag.

    Returns:
        Dict with flagged status, segment_id, and tenant_id.
    """
    log.info("flag_churn_risk_customer %s/%s — tier=auto",
             tenant_id, segment_id)
    # TODO: Wire to customer DB update — set churn_risk_flag = true
    #       on the segment record so dashboard filters pick it up.
    return {
        "flagged": True,
        "segment_id": segment_id,
        "tenant_id": tenant_id,
    }
