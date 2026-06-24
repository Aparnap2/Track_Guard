from __future__ import annotations

import logging
from typing import Any

from src.orchestrators.planned_action import PlannedAction

logger = logging.getLogger(__name__)


def execute_planned_action(action: PlannedAction) -> dict[str, Any]:
    try:
        if action.action_type == "post_slack_message":
            return _execute_slack_message(action)
        elif action.action_type == "create_erpnext_issue":
            return _execute_erpnext_issue(action)
        elif action.action_type == "update_hubspot_deal":
            return _execute_hubspot_deal(action)
        elif action.action_type == "send_investor_update":
            return _execute_investor_update(action)
        elif action.action_type == "write_quickbooks_note":
            return _execute_quickbooks_note(action)
        else:
            return {"ok": False, "error": f"Unknown action_type: {action.action_type}"}
    except Exception as exc:
        logger.error("Action execution failed for %s: %s", action.id, exc)
        return {"ok": False, "error": str(exc)}


def _execute_slack_message(action: PlannedAction) -> dict[str, Any]:
    from src.integrations.slack import send_message_sync

    text = action.params.get("text", "")
    blocks = action.params.get("blocks")
    result = send_message_sync(text=text, blocks=blocks)
    return {"ok": result.get("ok", False), "result": result}


def _execute_erpnext_issue(action: PlannedAction) -> dict[str, Any]:
    from src.integrations.erpnext_client import ERPNextClient

    client = ERPNextClient()
    subject = action.params.get("subject", action.params.get("title", "No subject"))
    description = action.params.get("description", "")
    doc = {
        "subject": subject,
        "description": description,
        "status": "Open",
    }
    priority = action.params.get("priority")
    if priority:
        doc["priority"] = priority

    response = client._request("POST", "/api/resource/Issue", body=doc)
    return {"ok": True, "result": response}


def _execute_hubspot_deal(action: PlannedAction) -> dict[str, Any]:
    import os

    if not os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip():
        return {"ok": True, "result": {"mock": True, "message": "HubSpot mock update"}}

    try:
        from hubspot import HubSpot
    except ImportError:
        return {"ok": False, "error": "hubspot SDK not installed"}

    client = HubSpot(access_token=os.environ["HUBSPOT_ACCESS_TOKEN"])
    deal_id = action.params.get("deal_id", action.target_ref)
    properties = action.params.get("properties", {})
    if deal_id:
        client.crm.deals.basic_api.update(deal_id=deal_id, body={"properties": properties})
    else:
        client.crm.deals.basic_api.create(body={"properties": properties})
    return {"ok": True, "result": {"deal_id": deal_id or "new"}}


def _execute_investor_update(action: PlannedAction) -> dict[str, Any]:
    from src.integrations.slack import send_message_sync

    text = action.params.get("text", "")
    full_draft = action.params.get("full_draft")
    result = send_message_sync(text=text, full_draft=full_draft)
    return {"ok": result.get("ok", False), "result": result}


def _execute_quickbooks_note(action: PlannedAction) -> dict[str, Any]:
    import os

    if not os.getenv("QUICKBOOKS_CLIENT_ID", "").strip():
        return {"ok": True, "result": {"mock": True, "message": "QuickBooks mock note"}}

    import httpx

    note = action.params.get("note", "")
    api_url = os.getenv("QUICKBOOKS_API_URL", "http://localhost:8097")
    company_id = os.getenv("QUICKBOOKS_COMPANY_ID", "")
    access_token = os.getenv("QUICKBOOKS_ACCESS_TOKEN", "")
    payload = {"note": note, "company_id": company_id}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{api_url}/v3/company/{company_id}/note",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return {"ok": True, "result": response.json()}
