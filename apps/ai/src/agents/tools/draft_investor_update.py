"""Tool: draft_investor_update — HITL Tier: approve.

Always requires founder approval before sending. Assembles the
latest mission state metrics into an investor-facing update email.
"""
from __future__ import annotations

import logging
from typing import Any

from src.config.llm import chat_completion
from src.session.mission_state import get_mission_state

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
    state = await get_mission_state(tenant_id)
    metrics = (
        f"Runway: {state.runway_days}d | "
        f"MRR trend: {state.mrr_trend} | "
        f"Churn: {state.churn_rate} | "
        f"Trust: {state.trust_score}"
    )
    prompt = (
        f"Write a brief investor update email draft based on: {metrics}. "
        "Professional tone, 2-3 paragraphs."
    )
    draft = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.5,
    )
    return {
        "draft": draft,
        "tenant_id": tenant_id,
    }
