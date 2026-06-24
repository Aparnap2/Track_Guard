from __future__ import annotations

import logging
from typing import Any

from src.states.schemas import MissionStateV2, SupportHealth
from src.services.state_store import StateStore

logger = logging.getLogger(__name__)

_ALERT_TTL = 3600
_DEDUP_PREFIX = "alert:sent"

_HEALTH_LABELS: dict[SupportHealth, str] = {
    SupportHealth.CRITICAL: "CRITICAL",
    SupportHealth.ATTENTION: "ATTENTION",
    SupportHealth.GOOD: "GOOD",
}

_EMOJI_MAP: dict[SupportHealth, str] = {
    SupportHealth.CRITICAL: ":red_circle:",
    SupportHealth.ATTENTION: ":large_yellow_circle:",
    SupportHealth.GOOD: ":large_green_circle:",
}

_SEVERITY_ORDER: list[SupportHealth] = [
    SupportHealth.CRITICAL,
    SupportHealth.ATTENTION,
    SupportHealth.GOOD,
]

_DOMAIN_LABELS: dict[str, str] = {
    "support": "Support",
    "execution": "Execution",
    "team": "Team",
    "finance": "Finance",
    "revenue": "Revenue",
}


class SlackAlertForwarder:
    def __init__(self, store: StateStore | None = None):
        self.store = store or StateStore(prefix="alert")

    def forward_mission_alert(self, state: MissionStateV2) -> dict[str, Any]:
        if not self._should_alert(state):
            return {"ok": True, "skipped": True, "reason": "health not critical or attention"}

        dk = self._dedup_key(state)
        if self.store.exists(dk):
            logger.info("Alert already sent for key=%s, skipping", dk)
            return {"ok": True, "skipped": True, "reason": "duplicate"}

        text = self._format_text(state)
        blocks = self._format_blocks(state)
        result = self._deliver(text=text, blocks=blocks)

        if result.get("ok"):
            self.store.set(dk, state.overall_health.value, ttl=_ALERT_TTL)
            logger.info("Alert delivered for tenant=%s health=%s", state.tenant_id, state.overall_health.value)
        else:
            logger.warning("Alert delivery failed for tenant=%s: %s", state.tenant_id, result.get("error"))

        return result

    def _should_alert(self, state: MissionStateV2) -> bool:
        return state.overall_health in (SupportHealth.CRITICAL, SupportHealth.ATTENTION)

    def _dedup_key(self, state: MissionStateV2) -> str:
        return f"{_DEDUP_PREFIX}:{state.tenant_id}:{state.overall_health.value}"

    def _deliver(self, text: str, blocks: list[dict] | None = None) -> dict[str, Any]:
        from src.integrations.slack import send_message_sync

        return send_message_sync(text=text, blocks=blocks)

    def _format_text(self, state: MissionStateV2) -> str:
        emoji = _EMOJI_MAP.get(state.overall_health, ":white_circle:")
        label = _HEALTH_LABELS.get(state.overall_health, "UNKNOWN")
        lines = [
            f"{emoji} Startup Guardian - {label}",
            f"Tenant: `{state.tenant_id}` | Run: `{state.run_id[:8]}`",
            "",
            "Domain Health:",
        ]

        for short, display in _DOMAIN_LABELS.items():
            domain = getattr(state, short, None)
            if domain is not None:
                health = getattr(domain, "health", None)
                lines.append(f"  - {display}: {health.value if health else 'unknown'}")

        failed = [k for k, v in state.connectors_ok.items() if not v]
        if failed:
            lines.append("")
            lines.append(f"Failed connectors: {', '.join(failed)}")

        return "\n".join(lines)

    def _format_blocks(self, state: MissionStateV2) -> list[dict]:
        emoji = _EMOJI_MAP.get(state.overall_health, ":white_circle:")
        label = _HEALTH_LABELS.get(state.overall_health, "UNKNOWN")
        blocks: list[dict] = []

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Startup Guardian - {label}",
            },
        })

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tenant:* `{state.tenant_id}` | *Run:* `{state.run_id[:8]}`",
            },
        })

        domain_lines = []
        for short, display in _DOMAIN_LABELS.items():
            domain = getattr(state, short, None)
            if domain is not None:
                health = getattr(domain, "health", None)
                h = health.value if health else "unknown"
                d_emoji = {SupportHealth.CRITICAL: ":red_circle:", SupportHealth.ATTENTION: ":large_yellow_circle:", SupportHealth.GOOD: ":large_green_circle:"}.get(
                    health, ":white_circle:"
                ) if health else ":white_circle:"
                domain_lines.append(f"{d_emoji} *{display}:* {h}")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Domain Health:*\n" + "\n".join(domain_lines),
            },
        })

        failed = [k for k, v in state.connectors_ok.items() if not v]
        if failed:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *Failed connectors:* {', '.join(failed)}",
                },
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": f"Run: {state.run_id[:8]} | {state.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if state.timestamp else 'N/A'}",
                },
            ],
        })

        return blocks
