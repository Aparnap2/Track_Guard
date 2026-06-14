"""Tests for Trust Battery Durable Storage - TDD phase."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock


class TestTrustBatteryDurable:
    """Trust Battery durable storage tests."""

    def setup_method(self):
        """Reset trust battery state before each test."""
        from src.services.trust_battery import reset_profiles
        reset_profiles()

    def test_profile_has_durability_fields(self):
        """AgentTrustProfile has durability fields for DB persistence."""
        from src.services.trust_battery import AgentTrustProfile

        profile = AgentTrustProfile(
            agent_name="cofounder",
            tenant_id="tenant-001",
            updated_at=datetime.now(timezone.utc),
            graphiti_strategy_id="strategy-123",
        )

        assert profile.updated_at is not None
        assert profile.graphiti_strategy_id == "strategy-123"

    @pytest.mark.asyncio
    async def test_save_trust_profile_to_db(self):
        """save_trust_profile writes to Postgres."""
        from src.services.trust_battery import AgentTrustProfile
        from src.services.trust_battery_db import save_trust_profile

        profile = AgentTrustProfile(
            agent_name="cofounder",
            tenant_id="tenant-001",
            trust_score=0.85,
            route_priority=2,
        )

        with patch("src.services.trust_battery_db.asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn

            result = await save_trust_profile(profile)

            assert result is True
            mock_conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_load_trust_profile_from_db(self):
        """load_trust_profile reads from Postgres."""
        from src.services.trust_battery import AgentTrustProfile
        from src.services.trust_battery_db import load_trust_profile

        with patch("src.services.trust_battery_db.asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "agent_name": "cofounder",
                "tenant_id": "tenant-001",
                "trust_score": 0.85,
                "route_priority": 2,
                "success_rate_7d": 0.8,
                "schema_parse_rate": 0.9,
                "founder_acceptance_rate": 0.85,
                "false_positive_rate": 0.05,
                "avg_latency_ms": 1000,
                "last_failure_at": None,
                "updated_at": datetime.now(timezone.utc),
            })
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn

            profile = await load_trust_profile("tenant-001", "cofounder")

            assert profile.agent_name == "cofounder"
            assert profile.tenant_id == "tenant-001"
            assert profile.trust_score == 0.85
            assert profile.route_priority == 2

    @pytest.mark.asyncio
    async def test_load_trust_profile_fallback_to_default(self):
        """load_trust_profile returns defaults if DB row not found."""
        from src.services.trust_battery import AgentTrustProfile
        from src.services.trust_battery_db import load_trust_profile

        with patch("src.services.trust_battery_db.asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn

            profile = await load_trust_profile("tenant-001", "cofounder")

            assert profile.agent_name == "cofounder"
            assert profile.tenant_id == "tenant-001"
            assert profile.trust_score == 0.75

    @pytest.mark.asyncio
    async def test_get_trust_leaderboard(self):
        """get_trust_leaderboard returns profiles sorted by trust score."""
        from src.services.trust_battery import AgentTrustProfile
        from src.services.trust_battery_db import get_trust_leaderboard

        now = datetime.now(timezone.utc)
        with patch("src.services.trust_battery_db.asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    "agent_name": "agent_b",
                    "tenant_id": "tenant-001",
                    "trust_score": 0.9,
                    "route_priority": 1,
                    "success_rate_7d": 0.8,
                    "schema_parse_rate": 0.9,
                    "founder_acceptance_rate": 0.85,
                    "false_positive_rate": 0.05,
                    "avg_latency_ms": 1000,
                    "last_failure_at": None,
                    "updated_at": now,
                },
                {
                    "agent_name": "agent_a",
                    "tenant_id": "tenant-001",
                    "trust_score": 0.5,
                    "route_priority": 3,
                    "success_rate_7d": 0.8,
                    "schema_parse_rate": 0.9,
                    "founder_acceptance_rate": 0.85,
                    "false_positive_rate": 0.05,
                    "avg_latency_ms": 1000,
                    "last_failure_at": None,
                    "updated_at": now,
                },
            ])
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn

            leaderboard = await get_trust_leaderboard("tenant-001")

            assert len(leaderboard) == 2
            assert leaderboard[0].trust_score == 0.9
            assert leaderboard[1].trust_score == 0.5


class TestTrustBatteryRouter:
    """Trust Battery routing integration tests."""

    def setup_method(self):
        """Reset trust battery state before each test."""
        from src.services.trust_battery import reset_profiles
        reset_profiles()

    @pytest.mark.asyncio
    async def test_route_uses_trust_score_high_trust(self):
        """High trust agent uses full pipeline."""
        from src.services.trust_battery import update_trust_score
        from src.agents.cofounder.router import Router

        update_trust_score("tenant-001", "finance", "acknowledge")
        update_trust_score("tenant-001", "finance", "acknowledge")

        router = Router()
        decision = await router.route(
            "What is my runway?",
            "tenant-001",
        )

        assert decision.trust_score > 0.6
        assert decision.routing_priority < 999
        assert decision.trust_reason in ("full_trust_pipeline", "default_routing")

    @pytest.mark.asyncio
    async def test_route_degraded_mode_low_trust(self):
        """Low trust agent uses degraded mode."""
        from src.services.trust_battery import update_trust_score
        from src.agents.cofounder.router import Router

        update_trust_score("tenant-001", "Finance Guardian", "false_positive")
        update_trust_score("tenant-001", "Finance Guardian", "false_positive")
        update_trust_score("tenant-001", "Finance Guardian", "dispute")

        router = Router()
        decision = await router.route(
            "Check the burn rate",
            "tenant-001",
        )

        assert decision.trust_score < 0.4
        assert decision.routing_priority == 999
        assert decision.trust_reason == "degraded_mode_active"

    @pytest.mark.asyncio
    async def test_route_medium_trust_caveat(self):
        """Medium trust agent adds caveat to routing."""
        from src.services.trust_battery import update_trust_score
        from src.agents.cofounder.router import Router

        update_trust_score("tenant-001", "BI Analyst", "acknowledge")
        profile = update_trust_score("tenant-001", "BI Analyst", "dispute")
        profile.trust_score = 0.55
        profile.route_priority = 3

        router = Router()
        decision = await router.route(
            "Show me cohort retention",
            "tenant-001",
        )

        assert 0.4 < decision.trust_score < 0.6
        assert decision.trust_reason == "medium_trust_caveat"


class TestAlertEvidenceChainTrust:
    """AlertEvidenceChain trust integration tests."""

    def test_alert_evidence_chain_has_trust_fields(self):
        """AlertEvidenceChain includes trust fields."""
        from src.services.audit_envelope import AlertEvidenceChain

        chain = AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-001",
            trace_id="trace-001",
            workflow_run_id="wf-001",
            mission_state_snapshot_id="ms-001",
            trust_score=0.85,
            routing_priority=2,
            trust_reason="full_trust_pipeline",
        )

        assert chain.trust_score == 0.85
        assert chain.routing_priority == 2
        assert chain.trust_reason == "full_trust_pipeline"

    def test_audit_envelope_includes_trust_in_chain(self):
        """AuditEnvelopeService logs trust data in evidence chain."""
        from src.services.audit_envelope import AlertEvidenceChain, AuditEnvelopeService

        service = AuditEnvelopeService()

        chain = AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-001",
            trace_id="trace-001",
            workflow_run_id="wf-001",
            mission_state_snapshot_id="ms-001",
            trust_score=0.75,
            routing_priority=3,
            trust_reason="medium_trust_caveat",
        )

        chain_id = service.log_evidence_chain(chain)
        retrieved = service.get_evidence_chain(chain_id)

        assert retrieved is not None
        assert retrieved.trust_score == 0.75
        assert retrieved.routing_priority == 3
        assert retrieved.trust_reason == "medium_trust_caveat"