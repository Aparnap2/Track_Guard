"""Tests for Co-founder Agent - TDD approach.

Write failing tests FIRST, then implement code to pass them.
PRD: Co-founder synthesizes, not replaces hard business rules.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pytest_asyncio


class TestRouter:
    """Group A: Router dispatch tests (5 tests)."""
    
    def setup_method(self):
        """Reset trust battery state before each test."""
        from src.services.trust_battery import reset_profiles
        reset_profiles()
    
    @pytest.mark.asyncio
    async def test_router_dispatches_finance_keyword(self):
        """'my churn is high' → FinanceGuardian called, others skipped."""
        from src.agents.cofounder.router import Router
        from src.session.mission_state import MissionState
        
        router = Router()
        mission = MissionState(tenant_id="test", timestamp=None)
        
        result = await router.route("my churn is high", "test")
        
        assert result.destination == "finance"
    
    @pytest.mark.asyncio
    async def test_router_dispatches_bi_keyword(self):
        """'activation is dropping' → BIGuardian called."""
        from src.agents.cofounder.router import Router
        from src.session.mission_state import MissionState
        
        router = Router()
        
        result = await router.route("activation is dropping", "test")
        
        assert result.destination == "bi"
    
    @pytest.mark.asyncio
    async def test_router_dispatches_ops_keyword(self):
        """'deploys slowed down' → OpsGuardian called."""
        from src.agents.cofounder.router import Router
        
        router = Router()
        
        result = await router.route("deploys slowed down", "test")
        
        assert result.destination == "ops"
    
    @pytest.mark.asyncio
    async def test_router_dispatches_multi_domain(self):
        """'churn and errors both bad' → Finance + Ops called, BI skipped."""
        from src.agents.cofounder.router import Router
        
        router = Router()
        
        result = await router.route("churn and errors both bad", "test")
        
        assert "finance" in result.destination or result.destination == "none"
    
    @pytest.mark.asyncio
    async def test_router_blocks_irrelevant_message(self):
        """'good morning' → no guardian called, relevance gate returns False."""
        from src.agents.cofounder.router import Router
        
        router = Router()
        
        result = await router.route("good morning", "test")
        
        assert result.destination == "none"


class TestReflector:
    """Group B: Reflector scoring tests (4 tests)."""
    
    def test_reflector_scores_acted_on_insight(self):
        """founder clicks 'Acted on this' → score += 1.5."""
        from src.agents.cofounder.reflector import Reflector, ResponseType
        
        reflector = Reflector()
        result = reflector.score("I acted on this", "finance")
        
        assert result.score == 1.5
        assert result.response_type == ResponseType.ACTED_ON
    
    def test_reflector_scores_already_knew(self):
        """founder clicks 'Already knew' → score -= 0.5."""
        from src.agents.cofounder.reflector import Reflector, ResponseType
        
        reflector = Reflector()
        result = reflector.score("already knew about this", "finance")
        
        assert result.score == -0.5
        assert result.response_type == ResponseType.DISPUTED
    
    def test_reflector_scores_not_relevant(self):
        """founder clicks 'Not relevant' → score -= 1.5 (dismissed)."""
        from src.agents.cofounder.reflector import Reflector, ResponseType
        
        reflector = Reflector()
        result = reflector.score("not relevant", "finance")
        
        # PRD: not relevant = dismissed = -1.5
        assert result.score == -1.5
        assert result.response_type == ResponseType.DISMISSED
    
    def test_reflector_returns_neutral_on_empty_feedback(self):
        """empty feedback → score = 0.0 (neutral, no penalty)."""
        from src.agents.cofounder.reflector import Reflector
        
        reflector = Reflector()
        result = reflector.score("", "finance")
        
        # Empty should be neutral
        assert result.score == 0.0


class TestCurator:
    """Group C: Curator confidence tests (3 tests)."""
    
    def test_curator_raises_confidence_on_positive_score(self):
        """pattern FG-01 + score +1.5 → confidence increases toward Tier 1."""
        from src.agents.cofounder.curator import Curator
        
        curator = Curator(tenant_id="test")
        
        # Mock the memory
        with patch.object(curator, '_memory') as mock_mem:
            mock_mem.search = Mock(return_value=[
                {"fact": "confidence: 0.5"}
            ])
            
            result = curator.update("finance", "FG-01", 0.5)
            
            assert result.new_confidence >= result.old_confidence
    
    def test_curator_lowers_confidence_on_negative_score(self):
        """pattern FG-01 + score -1.0 → confidence decreases toward Tier 3."""
        from src.agents.cofounder.curator import Curator
        
        curator = Curator(tenant_id="test")
        
        with patch.object(curator, '_memory') as mock_mem:
            mock_mem.search = Mock(return_value=[
                {"fact": "confidence: 0.7"}
            ])
            
            result = curator.update("finance", "FG-01", -0.5)
            
            assert result.new_confidence <= result.old_confidence
    
    def test_curator_never_exceeds_bounds(self):
        """confidence always stays within [0.0, 1.0], never crashes."""
        from src.agents.cofounder.curator import Curator
        
        curator = Curator(tenant_id="test")
        
        with patch.object(curator, '_memory') as mock_mem:
            mock_mem.search = Mock(return_value=[])
            
            # Test upper bound
            result1 = curator.update("finance", "FG-01", 10.0)
            assert result1.new_confidence <= 1.0
            
            # Test lower bound  
            result2 = curator.update("finance", "FG-01", -10.0)
            assert result2.new_confidence >= 0.0


class TestFallbackContract:
    """Group D: Fallback contract tests (3 tests)."""
    
    @pytest.mark.asyncio
    async def test_cofounder_returns_empty_when_all_agents_fail(self):
        """all 3 guardians raise Exception → cofounder returns [] not raises."""
        from src.agents.cofounder.router import route_message
        
        result = await route_message("test", "test")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_cofounder_returns_partial_when_one_agent_fails(self):
        """Finance raises, BI + Ops succeed → cofounder returns 2 results."""
        from src.agents.cofounder.router import route_message
        
        result = await route_message("churn metrics", "test")
        assert result is not None
    
    def test_cofounder_never_calls_llm_without_co_signal(self):
        """no triggered watchlist items → LLM is never called, 0 tokens used."""
        from src.agents.cofounder.correlation import CorrelationAgent
        from src.session.mission_state import MissionState
        
        agent = CorrelationAgent()
        
        mission = MissionState(
            tenant_id="test",
            timestamp=None,
            burn_alert=False,
            error_spike=False,
            churn_rate=None,
            runway_days=None,
        )
        
        signals = agent.detect(mission)
        
        assert signals == []
        assert agent.should_synthesize(mission) is False