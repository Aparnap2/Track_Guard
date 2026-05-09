"""
CommsTriageAgent Node Functions.

Each node:
  - Accepts state: CommsTriageState
  - Returns dict of only fields it changes
  - Never raises — errors written to state["error"] + state["error_node"]
  - Uses try/except with logging
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from src.agents.comms.state import CommsTriageState
from src.agents.comms.prompts import message_classifier, digest_generator

logger = logging.getLogger(__name__)


def fetch_messages(state: CommsTriageState) -> dict:
    """
    Fetch recent messages from specified Slack channels.

    Populates:
      - messages: List of message dicts with text, sender, channel, timestamp

    Uses Slack API to fetch messages from each channel.
    """
    result: dict = {
        "messages": [],
        "data_sources": [],
    }

    tenant_id = state.get("tenant_id", "unknown")
    channels = state.get("channels", [])

    if not channels:
        result["error"] = "No channels specified"
        result["error_node"] = "fetch_messages"
        return result

    try:
        # Import Slack client
        from src.integrations.slack_client import SlackClient

        slack_client = SlackClient()
        all_messages = []

        for channel in channels:
            try:
                # Fetch messages from channel
                messages = slack_client.fetch_channel_messages(channel, limit=20)
                all_messages.extend(messages)
                logger.info(f"Fetched {len(messages)} messages from {channel}")
            except Exception as e:
                logger.warning(f"Failed to fetch from {channel}: {e}")

        result["messages"] = all_messages
        result["data_sources"].append("slack")

    except Exception as e:
        logger.error(f"Message fetch failed: {e}")
        result["error"] = str(e)
        result["error_node"] = "fetch_messages"

    return result


def classify_messages(state: CommsTriageState) -> dict:
    """
    Classify each message using DSPy MessageClassifier.

    Populates:
      - classified_messages: Messages with category, priority, summary
      - urgent_messages: High priority messages
      - action_items: Messages requiring action
    """
    result: dict = {
        "classified_messages": [],
        "urgent_messages": [],
        "action_items": [],
    }

    messages = state.get("messages", [])

    if not messages:
        return result

    try:
        classified = []

        for msg in messages:
            try:
                response = message_classifier(
                    message_text=msg.get("text", ""),
                    sender=msg.get("user", "unknown"),
                    channel=msg.get("channel", "unknown"),
                )

                classified_msg = {
                    "original": msg,
                    "category": str(response.get("category", "informational")).lower(),
                    "priority": str(response.get("priority", "low")).lower(),
                    "summary": str(response.get("summary", "")),
                    "action_items": str(response.get("action_items", "none")),
                }
                classified.append(classified_msg)

                # Track urgent and action items
                if classified_msg["priority"] == "high":
                    result["urgent_messages"].append(classified_msg)
                if classified_msg["action_items"] != "none":
                    result["action_items"].append(classified_msg)

            except Exception as e:
                logger.warning(f"Classification failed for message: {e}")
                # Add with default classification
                classified.append({
                    "original": msg,
                    "category": "informational",
                    "priority": "low",
                    "summary": msg.get("text", "")[:50],
                    "action_items": "none",
                })

        result["classified_messages"] = classified
        logger.info(f"Classified {len(classified)} messages")

    except Exception as e:
        logger.error(f"Message classification failed: {e}")
        result["error"] = str(e)
        result["error_node"] = "classify_messages"

    return result


def generate_digest(state: CommsTriageState) -> dict:
    """
    Generate a daily comms digest using DSPy DigestGenerator.

    Populates:
      - digest: Formatted digest text
    """
    result: dict = {
        "digest": "",
    }

    try:
        classified = state.get("classified_messages", [])
        if not classified:
            result["digest"] = "No messages to digest."
            return result

        # Convert to JSON string for DSPy
        import json
        messages_json = json.dumps([
            {
                "sender": msg.get("original", {}).get("user", "unknown"),
                "channel": msg.get("original", {}).get("channel", "unknown"),
                "category": msg.get("category"),
                "priority": msg.get("priority"),
                "summary": msg.get("summary"),
                "action_items": msg.get("action_items"),
            }
            for msg in classified
        ])

        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        response = digest_generator(
            classified_messages=messages_json,
            date=date_str,
        )

        result["digest"] = str(response.get("digest", ""))
        logger.info(f"Generated digest: {len(result['digest'])} chars")

    except Exception as e:
        logger.error(f"Digest generation failed: {e}")
        # Fallback: simple text digest
        urgent = state.get("urgent_messages", [])
        action_items = state.get("action_items", [])

        result["digest"] = f"📬 Comms Digest — {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        if urgent:
            result["digest"] += f"🔴 Urgent: {len(urgent)} messages\n"
        if action_items:
            result["digest"] += f"✅ Action Items: {len(action_items)} messages\n"
        if not urgent and not action_items:
            result["digest"] += "No urgent items or action required."

    return result


def build_slack_message(state: CommsTriageState) -> dict:
    """
    Build Slack Block Kit message from digest.

    Populates:
      - slack_blocks: Block Kit JSON
    """
    result: dict = {
        "slack_blocks": [],
    }

    try:
        digest = state.get("digest", "No digest generated")
        urgent_count = len(state.get("urgent_messages", []))
        action_count = len(state.get("action_items", []))

        blocks: list[dict] = []

        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📬 Daily Comms Digest",
            },
        })

        # Stats row
        stats_text = []
        if urgent_count > 0:
            stats_text.append(f"🔴 {urgent_count} urgent")
        if action_count > 0:
            stats_text.append(f"✅ {action_count} action items")
        if not stats_text:
            stats_text.append("All clear")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": " | ".join(stats_text),
            },
        })

        # Divider
        blocks.append({"type": "divider"})

        # Digest content
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": digest,
            },
        })

        # Footer
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"Generated {timestamp}",
                }
            ],
        })

        result["slack_blocks"] = blocks
        logger.info(f"Built Slack message: {len(blocks)} blocks")

    except Exception as e:
        logger.error(f"Slack message build failed: {e}")
        result["slack_blocks"] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📬 Daily Comms Digest\n{state.get('digest', 'N/A')}",
                },
            }
        ]

    return result