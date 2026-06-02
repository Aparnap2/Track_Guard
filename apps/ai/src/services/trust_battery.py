"""Trust Battery Service - Agent trust scoring and routing priority."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

TRUST_EVENT_DELTA = {
    "acknowledge": 0.1,
    "dispute": -0.2,
    "false_positive": -0.3,
    "schema_parse_fail": -0.1,
    # Slack button feedback events (wired via score_from_button)
    "rate_good": 0.05,
    "rate_bad": -0.10,
}
DEGRADED_THRESHOLD = 0.4
DEGRADED_PRIORITY = 999


@dataclass
class AgentTrustProfile:
    agent_name: str
    tenant_id: str
    success_rate_7d: float = 0.8
    schema_parse_rate: float = 0.9
    founder_acceptance_rate: float = 0.85
    false_positive_rate: float = 0.05
    avg_latency_ms: int = 1000
    last_failure_at: Optional[datetime] = None
    trust_score: float = 0.75
    route_priority: int = 1
    updated_at: Optional[datetime] = None
    graphiti_strategy_id: Optional[str] = None
    # ── Guardrail policy fields (Phase 2) ───────────────────────────────
    authority_limit: str = "none"                    # founder | board | none
    max_auto_approve_severity: str = "info"          # info | warning | critical | none
    investor_update_requires_approval: bool = False  # True if agent output goes to investors
    irreversible_decision_threshold: float = 0.8     # min trust score for irreversible decisions


_profiles: dict[str, AgentTrustProfile] = {}


def _profile_key(tenant_id: str, agent_name: str) -> str:
    return f"{tenant_id}:{agent_name}"


def get_profile(tenant_id: str, agent_name: str) -> AgentTrustProfile:
    """Get or create trust profile for agent."""
    key = _profile_key(tenant_id, agent_name)
    if key not in _profiles:
        _profiles[key] = AgentTrustProfile(agent_name=agent_name, tenant_id=tenant_id)
    return _profiles[key]


def update_trust_score(tenant_id: str, agent_name: str, event_type: str) -> AgentTrustProfile:
    """Update trust score based on event type."""
    profile = get_profile(tenant_id, agent_name)
    delta = TRUST_EVENT_DELTA.get(event_type, 0.0)
    profile.trust_score = max(0.0, min(1.0, profile.trust_score + delta))
    if event_type in ("dispute", "false_positive", "schema_parse_fail"):
        profile.last_failure_at = datetime.now()
    profile.route_priority = _compute_priority(profile.trust_score)
    return profile


def _compute_priority(trust_score: float) -> int:
    """Compute route priority from trust score."""
    if trust_score < DEGRADED_THRESHOLD:
        return DEGRADED_PRIORITY
    if trust_score >= 0.9:
        return 1
    if trust_score >= 0.75:
        return 2
    if trust_score >= 0.5:
        return 3
    if trust_score >= 0.4:
        return 4
    return 5


def get_route_priority(tenant_id: str, agent_name: str) -> int:
    """Get route priority for agent (1=preferred, 999=degraded/skip)."""
    profile = get_profile(tenant_id, agent_name)
    return profile.route_priority


def is_agent_degraded(tenant_id: str, agent_name: str) -> bool:
    """Check if agent is degraded (trust_score < 0.4)."""
    profile = get_profile(tenant_id, agent_name)
    return profile.trust_score < DEGRADED_THRESHOLD


def reset_profiles() -> None:
    """Reset all profiles (for testing)."""
    _profiles.clear()


# ── Guardrail policy field getters/setters (Phase 2) ────────────────────


def set_authority_limit(tenant_id: str, agent_name: str, limit: str) -> AgentTrustProfile:
    """Set the authority limit for an agent.

    Args:
        tenant_id: Tenant identifier.
        agent_name: Agent name.
        limit: Authority limit — one of "founder", "board", "none".

    Returns:
        Updated AgentTrustProfile.
    """
    profile = get_profile(tenant_id, agent_name)
    profile.authority_limit = limit
    return profile


def set_max_auto_approve_severity(
    tenant_id: str, agent_name: str, severity: str
) -> AgentTrustProfile:
    """Set the maximum severity an agent can auto-approve.

    Args:
        tenant_id: Tenant identifier.
        agent_name: Agent name.
        severity: Max severity — one of "info", "warning", "critical", "none".

    Returns:
        Updated AgentTrustProfile.
    """
    profile = get_profile(tenant_id, agent_name)
    profile.max_auto_approve_severity = severity
    return profile


def can_auto_approve(tenant_id: str, agent_name: str, severity: str) -> bool:
    """Check if an agent can auto-approve a decision at the given severity.

    Severity ranking (low to high): info < warning < critical < none.
    An agent can auto-approve if the requested severity is at or below
    its ``max_auto_approve_severity``.

    Args:
        tenant_id: Tenant identifier.
        agent_name: Agent name.
        severity: The severity to check — "info", "warning", "critical".

    Returns:
        True if the agent can auto-approve.
    """
    profile = get_profile(tenant_id, agent_name)
    severity_rank = {"info": 0, "warning": 1, "critical": 2, "none": 3}
    request_rank = severity_rank.get(severity, 99)
    max_rank = severity_rank.get(profile.max_auto_approve_severity, 0)
    return request_rank <= max_rank


def can_make_irreversible_decision(tenant_id: str, agent_name: str) -> bool:
    """Check if an agent can make irreversible decisions.

    An agent can make irreversible decisions if its current trust score
    is at or above its ``irreversible_decision_threshold``.

    Args:
        tenant_id: Tenant identifier.
        agent_name: Agent name.

    Returns:
        True if the agent can make irreversible decisions.
    """
    profile = get_profile(tenant_id, agent_name)
    return profile.trust_score >= profile.irreversible_decision_threshold