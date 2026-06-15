"""Assembles TeamState from ERPNext HR (Employee) snapshot dict."""
from __future__ import annotations
import logging
from typing import Any, Dict
from src.states.schemas import SupportHealth, TeamState

logger = logging.getLogger(__name__)


def assemble_team_state(raw: Dict[str, Any]) -> TeamState:
    active_employees = raw.get("team_active_count", 0)
    headcount_by_department = raw.get("team_departments", {})
    new_hires_30d = raw.get("team_new_joinees_30d", 0)
    departures_30d = raw.get("team_departures_30d", 0)

    if departures_30d > 2:
        health = SupportHealth.CRITICAL
    elif departures_30d > 0:
        health = SupportHealth.ATTENTION
    else:
        health = SupportHealth.GOOD

    return TeamState(
        active_employees=active_employees,
        headcount_by_department=headcount_by_department,
        new_hires_30d=new_hires_30d,
        departures_30d=departures_30d,
        health=health,
    )
