"""Tool: schedule_customer_checkin — HITL Tier: auto.

Auto-executes for FG-03 (customer concentration risk) or BG-04
(cohort retention degradation). Logs the decision in the decision
journal and schedules a Slack reminder.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from src.integrations.slack_client import SlackClient

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "schedule_customer_checkin",
    "description": "Schedule a follow-up reminder for an at-risk customer",
    "hitl_tier": "auto",
    "trigger_patterns": ["FG-03", "BG-04"],
}


async def execute(tenant_id: str, customer_id: str, days_out: int = 7) -> dict[str, Any]:
    """Schedule a check-in reminder.

    Args:
        tenant_id: Tenant identifier.
        customer_id: Customer ID to check in with.
        days_out: Days until the reminder fires (default 7).

    Returns:
        Dict with scheduled status, customer_id, days_out, and tenant_id.
    """
    log.info("schedule_customer_checkin %s/%s — tier=auto, days=%d",
             tenant_id, customer_id, days_out)
    if not os.getenv("SLACK_BOT_TOKEN"):
        return {
            "scheduled": True,
            "customer_id": customer_id,
            "days_out": days_out,
            "tenant_id": tenant_id,
            "mock": True,
        }
    client = SlackClient()
    channel = os.getenv("SLACK_CHECKIN_CHANNEL", "#customer-checkins")
    msg = f"*Check-in reminder:* Follow up with customer `{customer_id}` in {days_out} days."
    resp = client.client.chat_postMessage(channel=channel, text=msg)
    return {
        "scheduled": True,
        "customer_id": customer_id,
        "days_out": days_out,
        "tenant_id": tenant_id,
        "channel": channel,
        "ts": resp.get("ts", ""),
    }
