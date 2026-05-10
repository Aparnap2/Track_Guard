"""
Slack Delivery — Primary channel for decision delivery via webhook.

Sends decision results to Slack using Incoming Webhooks or Bot API.
Falls back gracefully if Slack is not configured.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

from .schemas import DeliveryChannel, DeliveryResult, DeliveryStatus, DecisionResultInput

log = logging.getLogger(__name__)

# Configuration from environment
SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL", "").strip() or None
SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN", "").strip() or None
SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#general")


class SlackDeliveryError(Exception):
    """Raised when Slack delivery fails unexpectedly."""
    pass


async def send_via_webhook(
    text: str,
    blocks: Optional[list[dict[str, Any]]] = None,
) -> DeliveryResult:
    """
    Send message to Slack via Incoming Webhook.

    Args:
        text: Plain text message
        blocks: Optional Slack Block Kit blocks

    Returns:
        DeliveryResult with delivery status
    """
    if not SLACK_WEBHOOK_URL:
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error="Webhook URL not configured"
        )

    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()

            if response.text.strip().lower() == "ok":
                log.info("Slack message sent via webhook")
                return DeliveryResult(
                    ok=True,
                    decision_id="",
                    channel=DeliveryChannel.SLACK,
                    status=DeliveryStatus.DELIVERED,
                    message_id=""
                )
            else:
                log.warning(f"Slack webhook response: {response.text}")
                return DeliveryResult(
                    ok=False,
                    decision_id="",
                    channel=DeliveryChannel.SLACK,
                    status=DeliveryStatus.FAILED,
                    error=response.text
                )

    except httpx.HTTPError as e:
        log.warning(f"Slack webhook HTTP error: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )
    except Exception as e:
        log.error(f"Unexpected error sending Slack message: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )


async def send_via_bot(
    text: str,
    blocks: Optional[list[dict[str, Any]]] = None,
    channel: str = SLACK_CHANNEL,
) -> DeliveryResult:
    """
    Send message to Slack via Bot API (chat.postMessage).

    Args:
        text: Plain text message
        blocks: Optional Slack Block Kit blocks
        channel: Target channel (default from env)

    Returns:
        DeliveryResult with delivery status
    """
    if not SLACK_BOT_TOKEN:
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error="Bot token not configured"
        )

    api_url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "channel": channel,
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                log.info("Slack message sent via bot API")
                return DeliveryResult(
                    ok=True,
                    decision_id="",
                    channel=DeliveryChannel.SLACK,
                    status=DeliveryStatus.DELIVERED,
                    message_id=result.get("ts", "")
                )
            else:
                log.warning(f"Slack bot API error: {result.get('error')}")
                return DeliveryResult(
                    ok=False,
                    decision_id="",
                    channel=DeliveryChannel.SLACK,
                    status=DeliveryStatus.FAILED,
                    error=result.get("error", "Unknown error")
                )

    except httpx.HTTPError as e:
        log.warning(f"Slack bot HTTP error: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )
    except Exception as e:
        log.error(f"Unexpected error sending Slack via bot: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.SLACK,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )


async def deliver(decision: DecisionResultInput) -> DeliveryResult:
    """
    Deliver decision result to Slack.

    Tries webhook first, falls back to bot API if webhook not configured.

    Args:
        decision: Decision result to deliver

    Returns:
        DeliveryResult with delivery status
    """
    from .formatter import format_decision_blocks, format_plain_text

    # Try webhook first
    if SLACK_WEBHOOK_URL:
        result = await send_via_webhook(
            text=format_plain_text(decision),
            blocks=format_decision_blocks(decision)
        )
        result.decision_id = decision.decision_id
        return result

    # Fall back to bot API
    if SLACK_BOT_TOKEN:
        result = await send_via_bot(
            text=format_plain_text(decision),
            blocks=format_decision_blocks(decision)
        )
        result.decision_id = decision.decision_id
        return result

    # No Slack configured - indicate failure so fallback can be used
    log.info("Slack not configured - will use fallback")
    return DeliveryResult(
        ok=False,
        decision_id=decision.decision_id,
        channel=DeliveryChannel.SLACK,
        status=DeliveryStatus.FAILED,
        error="Slack not configured"
    )


def is_configured() -> bool:
    """Check if Slack is configured (webhook or bot)."""
    return bool(SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN)