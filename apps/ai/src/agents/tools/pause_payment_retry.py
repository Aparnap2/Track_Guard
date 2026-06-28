"""Tool: pause_failed_payment_retry — HITL Tier: review.

Triggered by FG-05 (3+ failed payments in 7 days). Pauses Stripe's
automatic retry schedule so the founder can investigate before
the customer is charged again.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

tool_def: dict[str, Any] = {
    "name": "pause_failed_payment_retry",
    "description": "Pause Stripe retry schedule for a customer with failed payments",
    "hitl_tier": "review",
    "trigger_patterns": ["FG-05"],
}


async def execute(tenant_id: str, customer_id: str) -> dict[str, Any]:
    """Pause automatic retry on a failed payment.

    Args:
        tenant_id: Tenant identifier.
        customer_id: Stripe customer ID whose retries should be paused.

    Returns:
        Dict with status, customer_id, and tenant_id.
    """
    log.info("pause_failed_payment_retry %s/%s — tier=review", tenant_id, customer_id)
    # TODO: Wire to Stripe API — call stripe.customers.update with
    #       invoice_settings.default_payment_method removal or pause
    #       collection via stripe.customers.update(customer, collection_method='send_invoice')
    return {
        "status": "paused",
        "customer_id": customer_id,
        "tenant_id": tenant_id,
    }
