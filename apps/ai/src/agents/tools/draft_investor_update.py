"""Tool: draft_investor_update — HITL Tier: approve.

Always requires founder approval before sending. Assembles the
latest mission state metrics into an investor-facing update email.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "draft_investor_update",
    "description": "Draft an investor update email for founder approval",
    "hitl_tier": "approve",
    "trigger_patterns": ["schedule", "manual"],
}


async def execute(tenant_id: str) -> dict[str, Any]:
    """Draft investor update from latest mission state.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Dict with draft text and tenant_id.
    """
    log.info("draft_investor_update %s — tier=approve", tenant_id)
    # TODO: Wire to InvestorAgent — call InvestorAgent to gather
    #       metrics from MissionState and generate email copy.
    return {
        "draft": "",
        "tenant_id": tenant_id,
    }
