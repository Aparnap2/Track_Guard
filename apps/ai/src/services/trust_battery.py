"""Trust Battery Service - Agent trust scoring and routing priority."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

TRUST_EVENT_DELTA = {
    "acknowledge": 0.1,
    "dispute": -0.2,
    "false_positive": -0.3,
    "schema_parse_fail": -0.1,
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