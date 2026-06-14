"""Assembles ExecutionState from ERPNext Projects/Tasks snapshot dict."""
from __future__ import annotations
import logging
from typing import Any, Dict
from src.states.schemas import ExecutionHealth, ExecutionState

logger = logging.getLogger(__name__)


def assemble_execution_state(raw: Dict[str, Any]) -> ExecutionState:
    active_projects = raw.get("execution_active_projects", 0)
    overdue_tasks = raw.get("execution_overdue_tasks", 0)
    open_tasks = raw.get("execution_milestones_total", 0)
    completed_tasks_30d = raw.get("execution_milestones_completed", 0)
    avg_completion_pct = raw.get("execution_avg_completion")

    if overdue_tasks > 3:
        health = ExecutionHealth.BLOCKED
    elif overdue_tasks > 0:
        health = ExecutionHealth.AT_RISK
    else:
        health = ExecutionHealth.ON_TRACK

    return ExecutionState(
        active_projects=active_projects,
        overdue_tasks=overdue_tasks,
        open_tasks=open_tasks,
        completed_tasks_30d=completed_tasks_30d,
        avg_completion_pct=avg_completion_pct,
        health=health,
    )
