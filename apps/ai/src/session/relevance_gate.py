"""
Relevance Gate — Pure code keyword router.

Per PRD Section 7: "Agent responds only if: keyword_hit OR (active_alert AND question)"
This is pure Python — zero LLM tokens. Fast and deterministic.

Key insight from PRD:
- Never responds to every message — that is noise
- Self-activates when domain keyword is triggered

V3.0: Integrates Trust Battery to skip degraded agents.
HARD GATE: When trust_score < 0.4, agent is hard-blocked from firing.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Import Trust Battery service
# Lazy import to avoid circular dependencies
_trust_battery = None


def _get_trust_battery():
    """Lazy load Trust Battery to avoid circular import."""
    global _trust_battery
    if _trust_battery is None:
        try:
            from src.services.trust_battery import (
                is_agent_degraded,
                get_route_priority,
            )
            _trust_battery = {
                "is_agent_degraded": is_agent_degraded,
                "get_route_priority": get_route_priority,
            }
        except ImportError:
            _trust_battery = None
    return _trust_battery


@dataclass
class RelevanceDecision:
    """Result of relevance gate evaluation."""

    should_respond: bool
    triggered_domains: list[str]
    reason: str
    skipped_agents: list[str] = field(default_factory=list)  # V3.0: Trust Battery integration


# Per PRD Section 7
DOMAIN_KEYWORDS = {
    "finance": [
        "burn", "runway", "revenue", "mrr", "budget", "cost",
        "raise", "invest", "plan", "price", "₹", "$", "spend",
        "churn", "arr", " ARR", "pricing", "payment",
    ],
    "ops": [
        "support", "ticket", "bug", "error", "churn", "usage",
        "feature", "feedback", "sentry", "user", "product",
        "deploy", "infrastructure", "aws", "cloud",
    ],
    "bi": [
        "metric", "dau", "mau", "retention", "cohort", "growth",
        "data", "dashboard", "report", "trend", "last month",
        "analytics", "activation", "adoption",
    ],
}


def _check_trust_battery(
    domain: str,
    tenant_id: str | None = None,
) -> tuple[bool, str]:
    """Check if agent should be skipped due to Trust Battery.

    Per PRD V3.0: Skip degraded agents (trust_score < 0.4).

    Args:
        domain: Domain to check (finance, bi, ops)
        tenant_id: Tenant ID for trust profile lookup

    Returns:
        Tuple of (should_skip, skip_reason)
    """
    tb = _get_trust_battery()
    if tb is None:
        return False, ""  # Trust battery not available, don't skip

    domain_to_agent = {
        "finance": "Finance Guardian",
        "bi": "BI Analyst",
        "ops": "Ops Watch",
    }

    agent_name = domain_to_agent.get(domain)
    if not agent_name:
        return False, ""

    # Default tenant if not provided (for testing)
    if not tenant_id:
        tenant_id = os.environ.get("DEFAULT_TENANT_ID", "test-tenant")

    try:
        if tb["is_agent_degraded"](tenant_id, agent_name):
            priority = tb["get_route_priority"](tenant_id, agent_name)
            log.warning(
                "Trust Battery HARD-BLOCK: agent degraded, skipping",
                extra={
                    "domain": domain,
                    "agent_name": agent_name,
                    "tenant_id": tenant_id,
                    "route_priority": priority,
                },
            )
            return True, f"degraded (priority: {priority})"
    except Exception as exc:
        # Trust battery check failed — remain permissive, do not block
        log.debug(
            "Trust Battery check unavailable, remaining permissive",
            extra={"domain": domain, "tenant_id": tenant_id, "error": str(exc)},
        )

    return False, ""


def evaluate_relevance(
    message: str,
    active_alerts: list[str] | None = None,
    mission_context: dict | None = None,
    tenant_id: str | None = None,
) -> RelevanceDecision:
    """Evaluate if a message triggers any domain agents.

    Per PRD Section 7:
    - Agent responds only if: keyword_hit OR (active_alert AND question)
    - Never responds to every message — that is noise

    V3.0: Also checks Trust Battery to skip degraded agents.

    Args:
        message: The founder's message to evaluate
        active_alerts: List of currently active alert IDs
        mission_context: Current MissionState (for contextual triggers)
        tenant_id: Tenant ID for Trust Battery integration

    Returns:
        RelevanceDecision with triggered domains and reasoning
    """
    message_lower = message.lower()
    triggered = []
    skipped = []

    # Check keyword matches
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in message_lower:
                # V3.0: Check Trust Battery before triggering
                should_skip, skip_reason = _check_trust_battery(domain, tenant_id)
                if should_skip:
                    skipped.append(f"{domain}: {skip_reason}")
                else:
                    triggered.append(domain)
                break

    # Per PRD: if active alert AND question asked, trigger domain
    # Question detection: "what", "how", "why", "should", "?"
    has_question = any(q in message_lower for q in ["what", "how", "why", "should", "?"])

    if active_alerts and has_question:
        # Add related domains based on active alerts
        for alert_id in active_alerts:
            if alert_id.startswith("FG-"):
                if "finance" not in triggered:
                    should_skip, skip_reason = _check_trust_battery("finance", tenant_id)
                    if should_skip:
                        skipped.append(f"finance: {skip_reason}")
                    else:
                        triggered.append("finance")
            elif alert_id.startswith("BG-"):
                if "bi" not in triggered:
                    should_skip, skip_reason = _check_trust_battery("bi", tenant_id)
                    if should_skip:
                        skipped.append(f"bi: {skip_reason}")
                    else:
                        triggered.append("bi")
            elif alert_id.startswith("OG-"):
                if "ops" not in triggered:
                    should_skip, skip_reason = _check_trust_battery("ops", tenant_id)
                    if should_skip:
                        skipped.append(f"ops: {skip_reason}")
                    else:
                        triggered.append("ops")

    # Deduplicate while preserving order
    triggered = list(dict.fromkeys(triggered))

    if triggered or skipped:
        reason_parts = []
        if triggered:
            reason_parts.append(f"Keywords matched: {', '.join(triggered)}")
        if skipped:
            reason_parts.append(f"Skipped: {', '.join(skipped)}")
        if active_alerts and has_question:
            reason_parts.append(f"({len(active_alerts)} active alerts)")
        return RelevanceDecision(
            should_respond=len(triggered) > 0,
            triggered_domains=triggered,
            reason=" | ".join(reason_parts),
            skipped_agents=skipped,
        )

    return RelevanceDecision(
        should_respond=False,
        triggered_domains=[],
        reason="No domain keywords matched",
        skipped_agents=[],
    )


def get_triggered_agents(
    message: str,
    active_alerts: list[str] | None = None,
    tenant_id: str | None = None,
) -> list[str]:
    """Get list of agent names that should respond to this message.

    Maps domain → agent name per PRD Section 7:

    | Domain | Agent |
    |--------|-------|
    | finance | Finance Guardian |
    | bi | BI Analyst |
    | ops | Ops Watch |

    V3.0: Filters out degraded agents via Trust Battery.

    Args:
        message: The founder's message
        active_alerts: Currently active alerts
        tenant_id: Tenant ID for Trust Battery lookup

    Returns:
        List of agent names to trigger
    """
    decision = evaluate_relevance(message, active_alerts, tenant_id=tenant_id)

    domain_to_agent = {
        "finance": "Finance Guardian",
        "bi": "BI Analyst",
        "ops": "Ops Watch",
    }

    return [domain_to_agent[d] for d in decision.triggered_domains]