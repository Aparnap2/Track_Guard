"""
Telegram Fallback — Secondary channel when Slack fails.

Telegram is kept behind the DeliveryService interface.
It is NOT exposed in Redpanda contracts - only used internally
as a fallback when Slack delivery fails.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from .schemas import DeliveryChannel, DeliveryResult, DeliveryStatus, DecisionResultInput

log = logging.getLogger(__name__)

# Configuration from environment
TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None
TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID", "").strip() or None


async def send_message(
    text: str,
    parse_mode: str = "HTML"
) -> DeliveryResult:
    """
    Send message to Telegram.

    Args:
        text: Message text (supports HTML formatting)
        parse_mode: Telegram parse mode (HTML or Markdown)

    Returns:
        DeliveryResult with delivery status
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.TELEGRAM,
            status=DeliveryStatus.FAILED,
            error="Telegram not configured"
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                log.info("Telegram message sent successfully")
                return DeliveryResult(
                    ok=True,
                    decision_id="",
                    channel=DeliveryChannel.TELEGRAM,
                    status=DeliveryStatus.DELIVERED,
                    message_id=str(data.get("result", {}).get("message_id", ""))
                )
            else:
                log.warning(f"Telegram API error: {data}")
                return DeliveryResult(
                    ok=False,
                    decision_id="",
                    channel=DeliveryChannel.TELEGRAM,
                    status=DeliveryStatus.FAILED,
                    error=str(data)
                )

    except httpx.HTTPError as e:
        log.warning(f"Telegram HTTP error: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.TELEGRAM,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )
    except Exception as e:
        log.error(f"Unexpected error sending Telegram message: {e}")
        return DeliveryResult(
            ok=False,
            decision_id="",
            channel=DeliveryChannel.TELEGRAM,
            status=DeliveryStatus.FAILED,
            error=str(e)
        )


async def deliver(decision: DecisionResultInput) -> DeliveryResult:
    """
    Deliver decision result to Telegram as fallback.

    Args:
        decision: Decision result to deliver

    Returns:
        DeliveryResult with delivery status
    """
    from .formatter import format_plain_text

    result = await send_message(format_plain_text(decision))
    result.decision_id = decision.decision_id

    if result.ok:
        result.status = DeliveryStatus.DELIVERED
    else:
        result.status = DeliveryStatus.FAILED

    return result


def is_configured() -> bool:
    """Check if Telegram is configured."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)