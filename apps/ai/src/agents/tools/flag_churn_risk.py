"""Tool: flag_churn_risk_customer — HITL Tier: auto.

Auto-executes for BG-06 (trial activation wall) or BG-04 (cohort
retention degradation). Flags the segment in the customer DB so
the dashboard and alerting pipeline can prioritize monitoring.
"""
from __future__ import annotations

import logging
from typing import Any

from src.session.mission_state import get_mission_state, update_mission_state

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
    state = await get_mission_state(tenant_id)
    existing = state.churn_risk_users or ""
    if segment_id not in existing:
        state.churn_risk_users = (existing + "," + segment_id).strip(",")
        state.last_updated_by = "flag_churn_risk_tool"
        await update_mission_state(state)
    log.info({"action": "flag_churn_risk", "segment_id": segment_id})
    return {
        "flagged": True,
        "segment_id": segment_id,
        "tenant_id": tenant_id,
    }
