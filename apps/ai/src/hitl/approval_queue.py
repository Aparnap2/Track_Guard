from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.orchestrators.planned_action import PlannedAction
from src.services.state_store import StateStore

logger = logging.getLogger(__name__)

_pending_approvals: dict[str, dict[str, Any]] = {}
_store = StateStore(prefix="approval")


def request_approval(action: PlannedAction) -> dict[str, Any]:
    from src.integrations.slack import send_message_sync

    action_dict = action.model_dump()
    _pending_approvals[action.id] = action_dict
    _store.set(f"pending:{action.id}", action_dict, ttl=86400)

    risk_label = action.risk_level.upper()
    reason = action.approval_reason or "No reason provided"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Approval Required — {risk_label}*\n"
                    f"*Action:* `{action.action_type}`\n"
                    f"*Actor:* `{action.actor}`\n"
                    f"*Tenant:* `{action.tenant_id}`\n"
                    f"*Reason:* {reason}\n"
                    f"*Params:* ```{action.params}```"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "value": f"approve:{action.id}",
                    "action_id": f"approve_action_{action.id}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "value": f"reject:{action.id}",
                    "action_id": f"reject_action_{action.id}",
                },
            ],
        },
    ]

    result = send_message_sync(
        text=f"[Approval Required] {action.action_type} by {action.actor}",
        blocks=blocks,
    )

    return {
        "ok": result.get("ok", False),
        "action": action_dict,
        "delivery": result,
    }


def handle_approval_response(action_id: str, approved: bool) -> dict[str, Any]:
    entry = _pending_approvals.get(action_id)
    if entry is None:
        entry = _store.get(f"pending:{action_id}")

    if entry is None:
        return {"ok": False, "error": f"Approval request not found: {action_id}"}

    new_status = "approved" if approved else "rejected"
    entry["status"] = new_status
    if approved:
        entry["executed_at"] = datetime.now(timezone.utc).isoformat()

    _pending_approvals[action_id] = entry
    _store.set(f"pending:{action_id}", entry, ttl=86400)

    logger.info("Approval %s for action %s", new_status, action_id)
    return {"ok": True, "action": entry}


def get_pending_approvals(tenant_id: str | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entry in _pending_approvals.values():
        if tenant_id is None or entry.get("tenant_id") == tenant_id:
            results.append(entry)
    return results
