from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel


class PlannedAction(BaseModel):
    tenant_id: str
    actor: str
    action_type: Literal[
        "post_slack_message",
        "create_erpnext_issue",
        "update_hubspot_deal",
        "send_investor_update",
        "write_quickbooks_note",
    ]
    target_ref: str | None = None
    params: dict = {}
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_approval: bool = False
    approval_reason: str | None = None
    id: str = ""
    status: Literal["planned", "approved", "rejected", "executed", "failed"] = "planned"
    created_at: str = ""
    executed_at: str | None = None
    error: str | None = None

    def model_post_init(self, __context) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
