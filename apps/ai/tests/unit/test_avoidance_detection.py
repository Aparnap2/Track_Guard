"""Tests for Avoidance Detection - TDD Red phase."""
import pytest


class TestAvoidanceDetection:
    """Avoidance pattern detection tests."""

    def test_detect_fundraising_deflection(self):
        """fundraising_deflection: founder avoiding fundraising despite short runway."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "founder_focus": "fundraising",
            "fundraising_activities": 1,
            "runway_days": 90,
        }
        result = service.detect(mission)
        names = [p.name for p in result]
        assert "fundraising_deflection" in names

    def test_detect_headcount_deflection(self):
        """headcount_deflection: founder avoiding hiring despite burn rate increase."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "runway_days": 60,
            "hiring_intent": "freeze",
            "burn_rate_trend": "increasing",
        }
        result = service.detect(mission)
        names = [p.name for p in result]
        assert "headcount_deflection" in names

    def test_detect_churn_avoidance(self):
        """churn_avoidance: founder avoiding difficult customer conversations."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "churn_rate": 0.15,
            "customer_conversation_count": 0,
            "last_customer_call_days": 30,
        }
        result = service.detect(mission)
        names = [p.name for p in result]
        assert "churn_avoidance" in names

    def test_detect_metric_avoidance(self):
        """metric_avoidance: founder avoiding metric review during critical period."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "dashboard_views_7d": 2,
            "burn_alert": True,
        }
        result = service.detect(mission)
        names = [p.name for p in result]
        assert "metric_avoidance" in names

    def test_is_founder_avoiding_true(self):
        """is_founder_avoiding returns True when any pattern detected."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "runway_days": 60,
            "hiring_intent": "freeze",
            "burn_rate_trend": "increasing",
        }
        assert service.is_founder_avoiding(mission) is True

    def test_is_founder_avoiding_false(self):
        """is_founder_avoiding returns False when no patterns detected."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "founder_focus": "product",
            "runway_days": 300,
            "churn_rate": 0.02,
            "dashboard_views_7d": 10,
        }
        assert service.is_founder_avoiding(mission) is False

    def test_get_critical_avoidances_filters(self):
        """get_critical_avoidances returns only critical severity patterns."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "founder_focus": "fundraising",
            "fundraising_activities": 1,
            "runway_days": 90,
            "churn_rate": 0.15,
            "customer_conversation_count": 0,
            "last_customer_call_days": 30,
        }
        critical = service.get_critical_avoidances(mission)
        names = [p.name for p in critical]
        assert "fundraising_deflection" in names
        assert "churn_avoidance" not in names  # warning, not critical

    def test_avoidance_pattern_has_recommendation(self):
        """AvoidancePattern should include recommendation field."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "runway_days": 60,
            "hiring_intent": "freeze",
            "burn_rate_trend": "increasing",
        }
        result = service.detect(mission)
        assert len(result) > 0
        assert result[0].recommendation != ""

    def test_no_false_positives_on_clean_state(self):
        """No avoidance detected when founder is engaged."""
        from src.agents.cofounder.avoidance import AvoidanceDetectionService
        service = AvoidanceDetectionService()
        mission = {
            "founder_focus": "fundraising",
            "fundraising_activities": 5,
            "runway_days": 200,
            "hiring_intent": "hiring",
            "burn_rate_trend": "stable",
            "churn_rate": 0.02,
            "customer_conversation_count": 5,
            "last_customer_call_days": 3,
            "dashboard_views_7d": 15,
            "burn_alert": False,
        }
        result = service.detect(mission)
        assert len(result) == 0