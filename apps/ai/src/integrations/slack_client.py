import json
import logging
import os
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.socket_client = SocketModeClient(
            app_token=os.getenv("SLACK_APP_TOKEN"),
            web_client=self.client,
        )
        self._socket_listener_running = False

    async def start_socket_mode_listener(self) -> SocketModeClient:
        """Start listening for Slack interactive events via Socket Mode.

        Registers a listener on the existing SocketModeClient that captures
        interactive button payloads and routes them through the shared
        ``route_slack_button()`` handler from slack_buttons.py.

        Returns:
            The connected SocketModeClient instance, or the existing one
            if already running (idempotent).

        Environment:
            SLACK_APP_TOKEN  — Socket Mode app-level token (starts with ``xapp-``)
            SLACK_BOT_TOKEN  — Bot token used by the WebClient (already set in __init__)
        """
        if self._socket_listener_running:
            logger.info("Socket Mode listener already running — skipping")
            return self.socket_client

        from src.integrations.slack_buttons import route_slack_button

        def _process(client: SocketModeClient, req: SocketModeRequest) -> None:
            """Synchronous callback for incoming Socket Mode requests.

            ``route_slack_button()`` is synchronous (no IO), and the non-aiohttp
            ``SocketModeClient`` uses a sync WebSocket client, so this callback
            is intentionally sync to avoid coroutine mismatches with ``ack()``.
            """
            try:
                if req.type == "interactive":
                    payload = json.loads(req.payload)
                    result = route_slack_button(payload)
                    if result.error:
                        logger.warning("Button route returned error", extra={"error": result.error})
                # Always ack so Slack doesn't retry
                req.ack()
            except Exception:
                logger.exception("Unhandled error in Socket Mode listener")
                # Still ack even on failure to prevent Slack retries
                try:
                    req.ack()
                except Exception:
                    pass

        self.socket_client.socket_mode_request_listeners.append(_process)
        await self.socket_client.connect()
        self._socket_listener_running = True
        logger.info("Socket Mode listener connected and running")
        return self.socket_client

    async def open_decision_modal(self, trigger_id: str):
        """Open the decision logging modal"""
        modal_view = {
            "type": "modal",
            "callback_id": "decision_modal",
            "title": {
                "type": "plain_text",
                "text": "Log Decision"
            },
            "submit": {
                "type": "plain_text",
                "text": "Log Decision"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "decision_block",
                    "label": {
                        "type": "plain_text",
                        "text": "What did you decide?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "decision_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., Hire Sarah as CTO"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "alternatives_block",
                    "label": {
                        "type": "plain_text",
                        "text": "What were the alternatives?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "alternatives_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., Wait 3 months, Hire externally"
                        },
                        "multiline": True
                    },
                    "optional": True
                },
                {
                    "type": "input",
                    "block_id": "reasoning_block",
                    "label": {
                        "type": "plain_text",
                        "text": "Why did you decide this?"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reasoning_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Key factors, risks considered, etc."
                        },
                        "multiline": True
                    }
                }
            ]
        }

        try:
            response = self.client.views_open(
                trigger_id=trigger_id,
                view=modal_view
            )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def handle_modal_submit(self, payload: dict, tenant_id: str):
        """Process decision modal submission"""
        # Extract values from modal submission
        values = payload.get("view", {}).get("state", {}).get("values", {})

        decision_data = {
            "decided": values.get("decision_block", {}).get("decision_input", {}).get("value", ""),
            "alternatives": values.get("alternatives_block", {}).get("alternatives_input", {}).get("value", ""),
            "reasoning": values.get("reasoning_block", {}).get("reasoning_input", {}).get("value", ""),
        }

        # Call log_decision activity
        from src.activities.log_decision import log_decision
        result = await log_decision(decision_data, tenant_id)
        return result

    def fetch_channel_messages(self, channel_id: str, limit: int = 20) -> list[dict]:
        """Fetch recent messages from a Slack channel."""
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
            )

            messages = []
            for msg in response.get("messages", []):
                # Skip bot messages and system messages
                if msg.get("subtype") and msg["subtype"] not in (None, "file_share"):
                    continue

                messages.append({
                    "text": msg.get("text", ""),
                    "user": msg.get("user", "unknown"),
                    "channel": channel_id,
                    "timestamp": msg.get("ts", ""),
                })

            return messages
        except Exception as e:
            # Return empty list on error
            return []

    def get_channel_id_by_name(self, channel_name: str) -> str | None:
        """Get channel ID from channel name."""
        try:
            response = self.client.conversations_list()
            for channel in response.get("channels", []):
                if channel.get("name") == channel_name.lstrip("#"):
                    return channel.get("id")
            return None
        except Exception:
            return None

    async def send_guardian_alert(
        self,
        tenant_id: str,
        message: str,
        pattern_name: str,
        severity: str,
    ) -> dict:
        """Send a guardian alert to the guardian-alerts Slack channel via WebClient.

        Replaces the old Mockoon-based ``deliver_guardian_alert()`` with a real
        Slack API call. The alert is sent as a formatted message with severity
        prefix and pattern context.

        Args:
            tenant_id: Tenant identifier (included in message context).
            message: The alert body text.
            pattern_name: Name of the detected anomaly/pattern.
            severity: One of ``"info"``, ``"warning"``, ``"critical"``.

        Returns:
            Dict with ``ok``, ``channel``, and optionally ``ts`` (message timestamp)
            or ``error``.

        Environment:
            SLACK_GUARDIAN_CHANNEL — Channel to post alerts to (default: ``#guardian-alerts``).
        """
        channel = os.getenv("SLACK_GUARDIAN_CHANNEL", "#guardian-alerts")
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=f"[{severity.upper()}] *{pattern_name}* (tenant: {tenant_id}): {message}",
            )
            ts = response.get("ts", "")
            logger.info(
                "Guardian alert sent",
                extra={"channel": channel, "pattern": pattern_name, "severity": severity, "ts": ts},
            )
            return {"ok": True, "channel": channel, "ts": ts}
        except Exception as e:
            logger.error("Failed to send guardian alert", extra={"error": str(e)})
            return {"ok": False, "channel": channel, "error": str(e)}