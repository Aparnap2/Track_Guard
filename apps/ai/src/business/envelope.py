"""
BusinessDecisionEnvelope — canonical typed contract for business decisions.

Composition-only contract: imports 5 existing schemas (EventEnvelope, AlertDecision,
GuardianMessage, DecisionResult, AlertEvidenceChain) and nests them as fields.

Key design principle: composition, not inheritance. Zero modifications to existing files.

This is the SINGLE object that flows through the decision pipeline:
    compute → guardrail → memory → delivery.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.event_envelope import EventEnvelope
from src.schemas.guardian import AlertDecision, GuardianMessage
from src.services.decision.schemas import DecisionResult
from src.services.audit_envelope import AlertEvidenceChain


class FinancialSnapshot(BaseModel):
    """Deterministic finance metrics — computed by finance_rules.py, never LLM.

    All values are derived from structured data sources (accounting ledgers,
    subscription tables, burn-down reports). No LLM-inferred numbers.
    """

    tenant_id: str
    mrr: float = 0.0
    burn_rate: float = 0.0
    runway_days: int = 0
    effective_runway_days: int = 0
    burn_multiple: float | None = None
    working_capital_ratio: float | None = None
    wacc_estimate: float | None = None
    npv: float | None = None
    irr: float | None = None
    rule_anomalies: list[str] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    """Output of the guardrail policy engine — deterministic, zero LLM.

    The guardrail layer enforces business rules (e.g., "never auto-approve
    refunds > ₹10,000") entirely through deterministic policy evaluation.
    """

    approval_tier: Literal["auto", "review", "blocking"]
    reversible: bool = True
    risk_type: Literal["financial", "legal", "reputational", "operational", "none"] = "none"
    authority_required: Literal["founder", "board", "none"] = "founder"
    blocking: bool = False
    privacy_sensitive: bool = False
    investor_facing: bool = False
    override_reason: str = ""


class BusinessDecisionEnvelope(BaseModel):
    """Canonical typed contract for business decisions.

    Composes 5 existing schemas (EventEnvelope, AlertDecision, GuardianMessage,
    DecisionResult, AlertEvidenceChain) with new finance + guardrail layers.

    This is the SINGLE object that flows through the pipeline:
    compute -> guardrail -> memory -> delivery.

    Pipeline stages:
        1. EventEnvelope arrives from the event bus.
        2. AlertDecision + GuardianMessage are produced by the Guardian agent.
        3. DecisionResult is produced by the Decision Engine.
        4. AlertEvidenceChain is produced by the Audit Envelope service.
        5. FinancialSnapshot is computed by finance_rules.py (deterministic).
        6. GuardrailResult is computed by the policy engine (deterministic).
    """

    # ── Composed from existing schemas (zero modifications to source files) ──
    event: EventEnvelope
    decision: AlertDecision
    message: GuardianMessage | None = None
    result: DecisionResult | None = None
    audit: AlertEvidenceChain | None = None

    # ── New: finance + guardrail layer ──
    finance_snapshot: FinancialSnapshot
    guardrail_status: GuardrailResult
    domain: Literal["finance", "bi", "ops"]
    reversible: bool = True
    approval_tier: Literal["auto", "review", "blocking"] = "auto"

    class Config:
        """Pydantic config: allow stdlib dataclass fields (AlertEvidenceChain)."""
        arbitrary_types_allowed = True
