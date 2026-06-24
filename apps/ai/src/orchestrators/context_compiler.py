from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from src.services.state_store import StateStore


class CompiledContext(BaseModel):
    goal: str
    return_format: dict
    warnings: list[str]
    mission_summary: dict
    relevant_events: list[dict]
    active_findings: list[dict]
    user_request: str | None = None
    error_context: list[dict] | None = None


async def compile_context(
    tenant_id: str,
    goal: str,
    agent_name: str,
    user_request: str | None = None,
    include_errors: bool = False,
    max_events: int = 5,
) -> CompiledContext:
    from src.session.mission_state import get_mission_state

    state = await get_mission_state(tenant_id)

    store = StateStore(prefix=f"ctx:{tenant_id}")

    events_raw = store.get(f"events:{agent_name}")
    events = events_raw[-max_events:] if events_raw else []

    findings_raw = store.get(f"findings:{agent_name}")
    findings = findings_raw if findings_raw else []

    mission_summary = {
        "tenant_id": state.tenant_id,
        "burn_alert": state.burn_alert,
        "burn_severity": state.burn_severity,
        "runway_days": state.runway_days,
        "mrr_trend": state.mrr_trend,
        "churn_rate": state.churn_rate,
        "error_spike": state.error_spike,
        "active_alerts": state.active_alerts,
        "founder_focus": state.founder_focus,
    }

    error_ctx = None
    if include_errors:
        errors_raw = store.get(f"errors:{agent_name}")
        error_ctx = errors_raw if errors_raw else None

    return CompiledContext(
        goal=goal,
        return_format={"type": "json"},
        warnings=[],
        mission_summary=mission_summary,
        relevant_events=events,
        active_findings=findings,
        user_request=user_request,
        error_context=error_ctx,
    )


def compile_context_to_messages(
    context: CompiledContext,
    system_prompt: str,
) -> list[dict[str, str]]:
    serialized = json.dumps(context.model_dump(), default=str, indent=2)
    system_content = f"{system_prompt}\n\n---\nCompiled Context:\n{serialized}"
    user_content = context.user_request or "Proceed with analysis"
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
