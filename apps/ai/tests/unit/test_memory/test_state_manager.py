"""Tests for AgentStateManager.

V3.0 TODO: spine.py orchestration not yet implemented.
See PRD Section 10 for spec.
"""
import pytest
pytestmark = pytest.mark.skip(reason="V3.0 memory spine not yet implemented")

from src.memory.state_manager import AgentStateManager


class TestStateManager:
    def test_default_state_has_beliefs(self):
        sm = AgentStateManager("tenant-a")
        state = sm.get_beliefs()
        assert "beliefs" in state
        assert "founder_archetype" in state["beliefs"]

    def test_update_belief(self):
        sm = AgentStateManager("tenant-a")
        sm.update_belief("pricing", "subscription", 0.8, "pulse_agent")
        state = sm.get_beliefs()
        assert state["beliefs"]["pricing"]["value"] == "subscription"
        assert state["beliefs"]["pricing"]["confidence"] == 0.8

    def test_get_uncertainties_returns_low_confidence(self):
        sm = AgentStateManager("tenant-a")
        sm.update_belief("risk", "unknown", 0.2, "default")
        uncertainties = sm.get_uncertainties()
        assert len(uncertainties) >= 1

    def test_get_uncertainties_excludes_high_confidence(self):
        sm = AgentStateManager("tenant-a")
        sm.update_belief("certainty", "known", 0.9, "default")
        uncertainties = sm.get_uncertainties()
        topics = [u["topic"] for u in uncertainties]
        assert "certainty" not in topics

    def test_tenant_isolation(self):
        sm1 = AgentStateManager("tenant-a")
        sm2 = AgentStateManager("tenant-b")
        sm1.update_belief("topic", "value-a", 0.8, "test")
        sm2.update_belief("topic", "value-b", 0.8, "test")
        assert sm1.get_beliefs()["beliefs"]["topic"]["value"] == "value-a"
        assert sm2.get_beliefs()["beliefs"]["topic"]["value"] == "value-b"
