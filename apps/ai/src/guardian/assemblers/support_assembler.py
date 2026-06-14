"""Assembles SupportState from ERPNext Helpdesk snapshot dict."""
from __future__ import annotations
import logging
from typing import Any, Dict
from src.states.schemas import SupportHealth, SupportState

logger = logging.getLogger(__name__)


def assemble_support_state(raw: Dict[str, Any]) -> SupportState:
    open_issues = raw.get("support_open_issues", 0)
    unresolved = raw.get("support_unresolved_issues", 0)

    if unresolved > 5:
        health = SupportHealth.CRITICAL
    elif unresolved > 0:
        health = SupportHealth.ATTENTION
    else:
        health = SupportHealth.GOOD

    return SupportState(
        open_issues=open_issues,
        unresolved_issues=unresolved,
        health=health,
    )
