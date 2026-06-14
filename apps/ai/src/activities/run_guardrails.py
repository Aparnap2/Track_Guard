"""
Guardrails Activity for Temporal.

Wraps the deterministic guardrails policy engine (``src.business.guardrails``)
as a Temporal activity.

Takes a serialized BusinessDecisionEnvelope (dict), reconstructs it, runs
all 7 guardrail evaluation stages, and returns the result.

Pure deterministic logic — no LLM calls.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from temporalio import activity

from src.business.envelope import (
    BusinessDecisionEnvelope,
    FinancialSnapshot,
    GuardrailResult,
)
from src.business.guardrails import evaluate_envelope
from src.schemas.event_envelope import EventEnvelope
from src.schemas.guardian import AlertDecision

log = logging.getLogger(__name__)


def _safe_heartbeat(message: str) -> None:
    """Safely call activity.heartbeat, ignoring errors outside activity context."""
    try:
        activity.heartbeat(message)
    except RuntimeError:
        log.debug("Heartbeat (no context): %s", message)


def _parse_datetime(value: Any) -> datetime:
    """Parse a datetime value from either a datetime object or ISO string."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.utcnow()


def _reconstruct_event(event_data: dict) -> EventEnvelope:
    """Reconstruct an EventEnvelope from a dict, handling datetime parsing."""
    data = dict(event_data)
    data["occurred_at"] = _parse_datetime(data.get("occurred_at"))
    data["received_at"] = _parse_datetime(data.get("received_at"))
    return EventEnvelope(**data)


def _reconstruct_decision(decision_data: dict) -> AlertDecision:
    """Reconstruct an AlertDecision from a dict."""
    return AlertDecision(**decision_data)


def _reconstruct_snapshot(snapshot_data: dict) -> FinancialSnapshot:
    """Reconstruct a FinancialSnapshot from a dict."""
    return FinancialSnapshot(**snapshot_data)


def _reconstruct_guardrail_status(status_data: dict) -> GuardrailResult:
    """Reconstruct a GuardrailResult from a dict."""
    return GuardrailResult(**status_data)


@activity.defn(name="run_guardrails")
async def run_guardrails(tenant_id: str, envelope_dict: dict) -> dict[str, Any]:
    """Evaluate BusinessDecisionEnvelope through all 7 guardrail stages.

    Reconstructs a ``BusinessDecisionEnvelope`` from its dict representation,
    runs ``evaluate_envelope()``, and returns the result.

    Args:
        tenant_id: Tenant identifier.
        envelope_dict: Serialized BusinessDecisionEnvelope (dict-compatible)
            with keys: event, decision, finance_snapshot, guardrail_status,
            domain, reversible, approval_tier.

    Returns:
        dict with:
        - ok: bool
        - tenant_id: str
        - guardrail_result: dict (GuardrailResult-compatible)
        - error: str (only if ok=False)

    Note:
        Never raises — catches exceptions and returns {"ok": False, "error": "..."}
    """
    if not tenant_id or not tenant_id.strip():
        return {"ok": False, "error": "tenant_id is required and cannot be empty", "tenant_id": ""}

    if not isinstance(envelope_dict, dict) or "event" not in envelope_dict:
        return {"ok": False, "error": "envelope_dict must contain 'event' key", "tenant_id": tenant_id}

    try:
        _safe_heartbeat(f"Running guardrails for tenant {tenant_id}")

        # ── Reconstruct envelope from dict ─────────────────────────────────
        event = _reconstruct_event(envelope_dict["event"])
        decision = _reconstruct_decision(envelope_dict["decision"])
        snapshot = _reconstruct_snapshot(envelope_dict.get("finance_snapshot", {}))
        guardrail_status = _reconstruct_guardrail_status(
            envelope_dict.get("guardrail_status", {"approval_tier": "auto"})
        )

        domain = envelope_dict.get("domain", "finance")
        reversible = envelope_dict.get("reversible", True)
        approval_tier = envelope_dict.get("approval_tier", "auto")

        envelope = BusinessDecisionEnvelope(
            event=event,
            decision=decision,
            finance_snapshot=snapshot,
            guardrail_status=guardrail_status,
            domain=domain,
            reversible=reversible,
            approval_tier=approval_tier,
        )

        # ── Evaluate all 7 stages ─────────────────────────────────────────
        result = evaluate_envelope(envelope)

        _safe_heartbeat(f"Guardrails complete for tenant {tenant_id}")

        return {
            "ok": True,
            "tenant_id": tenant_id,
            "guardrail_result": result.model_dump(),
        }

    except Exception as e:
        _safe_heartbeat(f"Guardrails failed for tenant {tenant_id}: {e}")
        log.exception("Guardrails error for tenant %s", tenant_id)
        return {"ok": False, "error": str(e), "tenant_id": tenant_id}
