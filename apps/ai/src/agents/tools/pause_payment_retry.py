"""Tool: pause_failed_payment_retry — HITL Tier: review.

Triggered by FG-05 (3+ failed payments in 7 days). Pauses Stripe's
automatic retry schedule so the founder can investigate before
the customer is charged again.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from src.integrations.stripe import MOCK_MODE

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "pause_failed_payment_retry",
    "description": "Pause Stripe retry schedule for a customer with failed payments",
    "hitl_tier": "review",
    "trigger_patterns": ["FG-05"],
}


async def execute(tenant_id: str, subscription_id: str) -> dict[str, Any]:
    """Pause automatic retry on a failed payment.

    Args:
        tenant_id: Tenant identifier.
        subscription_id: Stripe subscription ID whose retries should be paused.

    Returns:
        Dict with status, subscription_id, and tenant_id.
    """
    log.info("pause_failed_payment_retry %s/%s — tier=review", tenant_id, subscription_id)
    if MOCK_MODE:
        return {
            "status": "paused",
            "subscription_id": subscription_id,
            "tenant_id": tenant_id,
            "mock": True,
        }
    api_key = os.getenv("STRIPE_API_KEY", "")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Stripe-Version": "2023-10-16",
    }
    url = f"https://api.stripe.com/v1/subscriptions/{subscription_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            data={"collection_method": "send_invoice"},
            headers=headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        return {
            "status": "paused",
            "subscription_id": subscription_id,
            "tenant_id": tenant_id,
            "response": resp.json(),
        }
