from __future__ import annotations

from typing import Literal

_RISK_MAP: dict[str, tuple[Literal["low", "medium", "high"], bool, str | None]] = {
    "post_slack_message": ("low", False, None),
    "create_erpnext_issue": ("medium", True, "Creates a record in ERPNext helpdesk"),
    "update_hubspot_deal": ("high", True, "Modifies CRM deal data in HubSpot"),
    "send_investor_update": ("high", True, "Sends external communication to investors"),
    "write_quickbooks_note": ("medium", True, "Writes a note to QuickBooks accounting"),
}


def classify_risk(
    action_type: str,
    params: dict | None = None,
) -> tuple[Literal["low", "medium", "high"], bool, str | None]:
    params = params or {}
    base = _RISK_MAP.get(action_type)
    if base is None:
        return ("high", True, f"Unknown action type: {action_type}")

    risk_level, requires_approval, approval_reason = base

    if "delete" in action_type or "remove" in action_type:
        return ("high", True, "Destructive operation requires approval")

    monetary_amount = params.get("monetary_amount")
    if monetary_amount is not None:
        try:
            if int(monetary_amount) > 1000000:
                if risk_level == "low":
                    risk_level = "medium"
                elif risk_level == "medium":
                    risk_level = "high"
        except (ValueError, TypeError):
            pass

    if not requires_approval and risk_level in ("medium", "high"):
        requires_approval = True
        approval_reason = approval_reason or f"{risk_level} risk action requires approval"

    return (risk_level, requires_approval, approval_reason)
