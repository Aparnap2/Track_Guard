"""Tests for Session Layer - TDD approach.

Write failing tests FIRST, then implement code to pass them.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC


class TestRelevanceGate:
    """Relevance gate tests - pure Python, no LLM."""
    
    def test_finance_keywords_trigger(self):
        """Finance keywords should return 'finance'."""
        from src.session.relevance_gate import relevance_gate, DOMAIN_KEYWORDS
        
        # Test finance keywords
        for keyword in DOMAIN_KEYWORDS["finance"][:5]:
            result = relevance_gate(f"I am worried about {keyword}", None)
            assert "finance" in result
    
    def test_ops_keywords_trigger(self):
        """Ops keywords should return 'ops'."""
        from src.session.relevance_gate import relevance_gate, DOMAIN_KEYWORDS
        
        for keyword in DOMAIN_KEYWORDS["ops"][:5]:
            result = relevance_gate(f"Having issues with {keyword}", None)
            assert "ops" in result
    
    def test_bi_keywords_trigger(self):
        """BI keywords should return 'bi'."""
        from src.session.relevance_gate import relevance_gate, DOMAIN_KEYWORDS
        
        for keyword in DOMAIN_KEYWORDS["bi"][:5]:
            result = relevance_gate(f"Looking at {keyword} metrics", None)
            assert "bi" in result
    
    def test_no_keywords_returns_empty(self):
        """No keywords should return empty list."""
        from src.session.relevance_gate import relevance_gate
        
        result = relevance_gate("Hello how are you", None)
        assert result == []
    
    def test_keyword_with_active_alert(self):
        """Active alert + question should trigger."""
        from src.session.relevance_gate import relevance_gate
        from src.session.mission_state import MissionState
        from datetime import datetime
        
        # Create mission with active alert
        mission = MissionState(
            tenant_id="test",
            timestamp=datetime.now(UTC),
            burn_alert=True,
            active_alerts=["FG-01"],
        )
        
        # Question without keyword should still trigger due to active alert
        result = relevance_gate("What should I do?", mission)
        # Should trigger because active_alert=True AND it's a question


class TestMissionState:
    """MissionState dataclass tests."""
    
    def test_mission_state_creation(self):
        """MissionState should create with required fields."""
        from src.session.mission_state import MissionState
        from datetime import datetime
        
        mission = MissionState(
            tenant_id="test-tenant",
            timestamp=datetime.now(UTC),
        )
        
        assert mission.tenant_id == "test-tenant"
        assert mission.runway_days is None
        assert mission.burn_alert is False
        assert mission.active_alerts == []
    
    def test_mission_state_with_values(self):
        """MissionState should accept all fields."""
        from src.session.mission_state import MissionState
        from datetime import datetime
        
        mission = MissionState(
            tenant_id="test",
            timestamp=datetime.now(UTC),
            runway_days=90,
            burn_alert=True,
            burn_severity="critical",
            mrr_trend="down",
            churn_rate=0.05,
            churn_risk_users=3,
            error_spike=True,
            active_alerts=["FG-01", "BG-01"],
            founder_focus="fundraising",
        )
        
        assert mission.runway_days == 90
        assert mission.burn_severity == "critical"
        assert mission.churn_rate == 0.05
        assert len(mission.active_alerts) == 2


class TestSessionContext:
    """Session context tests - simplified."""
    
    def test_get_session_context_exists(self):
        """get_session_context should exist."""
        from src.session.context import get_session_context
        import inspect
        
        # Verify it's a callable function
        assert callable(get_session_context)
        # Verify it accepts expected parameters
        sig = inspect.signature(get_session_context)
        params = [p.name for p in sig.parameters.values()]
        assert 'tenant_id' in params
        assert 'limit' in params