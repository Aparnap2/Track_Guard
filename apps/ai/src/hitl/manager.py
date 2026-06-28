"""HITL Manager — 3-tier human-in-the-loop routing.

Tier 1 — AUTO: severity=info, confidence>0.85
Tier 2 — REVIEW: severity=warning, confidence<0.85, or new pattern
Tier 3 — APPROVE: severity=critical, confidence<0.60, or investor update

Adds resolve_suggested_tools() to surface tools that match the routing tier.
"""
from __future__ import annotations

from src.agents.tools import get_tools_for_patterns

GUARDRAIL_STATE_MAP = {
    "auto": "informational",
    "review": "advisory",
    "approve": "reviewable",
}


class HITLManager:
    def route(self, severity: str, confidence: float,
              is_new_pattern: bool = False,
              is_investor_update: bool = False) -> str:
        if is_investor_update:
            return "approve"
        if severity == "critical" and confidence < 0.60:
            return "approve"
        if severity == "warning" or (0.60 <= confidence < 0.85):
            return "review"
        if severity == "info" and confidence > 0.85:
            return "auto"
        return "review"

    def route_extended(
        self,
        severity: str,
        confidence: float,
        is_new_pattern: bool = False,
        is_investor_update: bool = False,
        risk_tolerance: str = "standard",         # NEW: standard | conservative | aggressive
        approval_required: bool = False,          # NEW: from guardrail engine
        blocking: bool = False,                   # NEW: from guardrail engine
    ) -> str:
        """Extended routing with guardrail awareness.

        Args:
            severity: Alert severity (critical/warning/info)
            confidence: Confidence score (0.0-1.0)
            is_new_pattern: Whether this is a newly seen pattern
            is_investor_update: Whether this is investor-facing
            risk_tolerance: Agent's risk tolerance setting
            approval_required: Whether guardrail requires explicit approval
            blocking: Whether guardrail blocks the decision entirely

        Returns:
            Routing tier: "auto" | "review" | "approve" | "blocked"
        """
        # Guardrail blocking overrides everything
        if blocking:
            return "blocked"

        # Guardrail required approval escalates to at least "approve"
        if approval_required:
            return "approve"

        # Risk tolerance adjustment: conservative shifts threshold up by 0.10
        adjusted_confidence = confidence
        if risk_tolerance == "conservative":
            adjusted_confidence = max(0.0, confidence - 0.10)
        elif risk_tolerance == "aggressive":
            adjusted_confidence = min(1.0, confidence + 0.10)

        # Call the existing route() with adjusted confidence
        return self.route(
            severity=severity,
            confidence=adjusted_confidence,
            is_new_pattern=is_new_pattern,
            is_investor_update=is_investor_update,
        )

    def resolve_suggested_tools(
        self,
        triggered_patterns: list[str],
        tier: str | None = None,
    ) -> list[dict[str, str]]:
        """Find registered tools matching triggered patterns and HITL tier."""
        candidates = get_tools_for_patterns(triggered_patterns)
        if tier is not None:
            candidates = [t for t in candidates if t.hitl_tier == tier]
        return [
            {"name": t.name, "description": t.description, "hitl_tier": t.hitl_tier}
            for t in candidates
        ]
