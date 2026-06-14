"""Tests for Trust Battery Service - TDD Red phase."""
import pytest
from datetime import datetime, timezone


class TestTrustBatteryService:
    """Trust Battery Service tests."""

    def setup_method(self):
        """Reset trust battery state before each test."""
        from src.services.trust_battery import reset_profiles
        reset_profiles()

    def test_profile_creation_defaults(self):
        """Profile created with correct default values."""
        from src.services.trust_battery import get_profile
        profile = get_profile("tenant-001", "cofounder")
        
        assert profile.agent_name == "cofounder"
        assert profile.tenant_id == "tenant-001"
        assert profile.success_rate_7d == 0.8
        assert profile.schema_parse_rate == 0.9
        assert profile.founder_acceptance_rate == 0.85
        assert profile.false_positive_rate == 0.05
        assert profile.avg_latency_ms == 1000
        assert profile.last_failure_at is None
        assert profile.trust_score == 0.75
        assert profile.route_priority == 1
        assert profile.updated_at is None
        assert profile.graphiti_strategy_id is None

    def test_update_acknowledge_positive(self):
        """Acknowledge event increases trust score by +0.1."""
        from src.services.trust_battery import get_profile, update_trust_score
        profile = update_trust_score("tenant-001", "cofounder", "acknowledge")
        
        assert profile.trust_score == 0.85
        assert profile.route_priority == 2  # 0.85 is high-trust but not >= 0.9

    def test_update_dispute_negative(self):
        """Dispute event decreases trust score by -0.2."""
        from src.services.trust_battery import get_profile, update_trust_score
        profile = update_trust_score("tenant-001", "cofounder", "dispute")
        
        assert profile.trust_score == 0.55

    def test_update_false_positive_penalty(self):
        """False positive event decreases trust score by -0.3."""
        from src.services.trust_battery import get_profile, update_trust_score
        profile = update_trust_score("tenant-001", "cofounder", "false_positive")
        
        assert profile.trust_score == 0.45

    def test_update_schema_parse_fail(self):
        """Schema parse fail decreases trust score by -0.1."""
        from src.services.trust_battery import get_profile, update_trust_score
        profile = update_trust_score("tenant-001", "cofounder", "schema_parse_fail")
        
        assert profile.trust_score == 0.65

    def test_get_route_priority_high_trust(self):
        """High trust score returns priority 1."""
        from src.services.trust_battery import get_profile, get_route_priority
        get_profile("tenant-001", "cofounder")
        priority = get_route_priority("tenant-001", "cofounder")
        
        assert priority == 1

    def test_get_route_priority_low_trust_degraded(self):
        """Low trust score (<0.4) returns 999 (degraded)."""
        from src.services.trust_battery import update_trust_score, get_route_priority
        update_trust_score("tenant-001", "cofounder", "false_positive")
        update_trust_score("tenant-001", "cofounder", "false_positive")
        update_trust_score("tenant-001", "cofounder", "dispute")
        priority = get_route_priority("tenant-001", "cofounder")
        
        assert priority == 999

    def test_ranked_agents_sorted(self):
        """Agents are sorted by trust score for routing decisions."""
        from src.services.trust_battery import update_trust_score, get_profile
        
        update_trust_score("tenant-001", "agent_a", "dispute")
        update_trust_score("tenant-001", "agent_b", "acknowledge")
        update_trust_score("tenant-001", "agent_c", "false_positive")
        
        profile_a = get_profile("tenant-001", "agent_a")
        profile_b = get_profile("tenant-001", "agent_b")
        profile_c = get_profile("tenant-001", "agent_c")
        
        assert profile_b.trust_score > profile_a.trust_score > profile_c.trust_score

    def test_is_agent_degraded(self):
        """is_agent_degraded returns True for trust_score < 0.4."""
        from src.services.trust_battery import update_trust_score, is_agent_degraded
        
        assert is_agent_degraded("tenant-001", "cofounder") == False
        
        update_trust_score("tenant-001", "cofounder", "false_positive")
        update_trust_score("tenant-001", "cofounder", "false_positive")
        update_trust_score("tenant-001", "cofounder", "dispute")
        
        assert is_agent_degraded("tenant-001", "cofounder") == True


class TestTrustBatteryGuardrails:
    """Trust Battery guardrail field tests."""

    def setup_method(self):
        """Reset trust battery state before each test."""
        from src.services.trust_battery import reset_profiles
        reset_profiles()

    def test_authority_limit_default(self):
        """authority_limit defaults to 'none'."""
        from src.services.trust_battery import get_profile

        profile = get_profile("tenant-001", "agent")
        assert profile.authority_limit == "none"

    def test_set_authority_limit(self):
        """set_authority_limit updates and returns profile."""
        from src.services.trust_battery import set_authority_limit, get_profile

        profile = set_authority_limit("tenant-001", "agent", "founder")
        assert profile.authority_limit == "founder"

        retrieved = get_profile("tenant-001", "agent")
        assert retrieved.authority_limit == "founder"

    def test_max_auto_approve_severity_default(self):
        """max_auto_approve_severity defaults to 'info'."""
        from src.services.trust_battery import get_profile

        profile = get_profile("tenant-001", "agent")
        assert profile.max_auto_approve_severity == "info"

    def test_set_max_auto_approve_severity(self):
        """set_max_auto_approve_severity updates and returns profile."""
        from src.services.trust_battery import set_max_auto_approve_severity, get_profile

        profile = set_max_auto_approve_severity("tenant-001", "agent", "warning")
        assert profile.max_auto_approve_severity == "warning"

        retrieved = get_profile("tenant-001", "agent")
        assert retrieved.max_auto_approve_severity == "warning"

    def test_can_auto_approve_info_allowed(self):
        """max=info, request=info → True."""
        from src.services.trust_battery import can_auto_approve
        assert can_auto_approve("tenant-001", "agent", "info") is True

    def test_can_auto_approve_warning_blocked(self):
        """max=info, request=warning → False."""
        from src.services.trust_battery import can_auto_approve
        assert can_auto_approve("tenant-001", "agent", "warning") is False

    def test_can_auto_approve_critical_blocked(self):
        """max=warning, request=critical → False."""
        from src.services.trust_battery import set_max_auto_approve_severity, can_auto_approve
        set_max_auto_approve_severity("tenant-001", "agent", "warning")
        assert can_auto_approve("tenant-001", "agent", "critical") is False

    def test_can_make_irreversible_decision_high_trust(self):
        """trust=0.9, threshold=0.8 → True."""
        from src.services.trust_battery import update_trust_score, can_make_irreversible_decision
        update_trust_score("tenant-001", "agent", "acknowledge")
        update_trust_score("tenant-001", "agent", "acknowledge")
        assert can_make_irreversible_decision("tenant-001", "agent") is True

    def test_can_make_irreversible_decision_low_trust(self):
        """trust=0.7, threshold=0.8 → False."""
        from src.services.trust_battery import can_make_irreversible_decision
        assert can_make_irreversible_decision("tenant-001", "agent") is False
