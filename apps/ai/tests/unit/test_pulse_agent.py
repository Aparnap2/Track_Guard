"""
Unit tests for PulseAgent stub.

Tests cover:
  - PulseState dataclass structure
  - PulseGraph dataclass structure
  - pulse_graph() function
  - Stub verification (no LLM calls)
"""
import pytest


TENANT = "test-pulse-tenant-unit"


class TestPulseState:
    """Tests for PulseState dataclass."""

    def test_pulse_state_requires_tenant_id(self):
        """PulseState requires tenant_id field."""
        from src.agents.pulse import PulseState

        state = PulseState(tenant_id=TENANT)
        assert state.tenant_id == TENANT

    def test_pulse_state_has_messages_default(self):
        """PulseState has messages list that defaults to empty list."""
        from src.agents.pulse import PulseState

        state = PulseState(tenant_id=TENANT)
        assert state.messages == []
        assert isinstance(state.messages, list)

    def test_pulse_state_accepts_messages(self):
        """PulseState accepts optional messages list."""
        from src.agents.pulse import PulseState

        state = PulseState(tenant_id=TENANT, messages=["test"])
        assert state.messages == ["test"]


class TestPulseGraph:
    """Tests for PulseGraph dataclass."""

    def test_pulse_graph_has_tenant_id(self):
        """PulseGraph has tenant_id field."""
        from src.agents.pulse.graph import PulseGraph

        graph = PulseGraph(tenant_id=TENANT)
        assert graph.tenant_id == TENANT


class TestPulseGraphInstance:
    """Tests for the pulse_graph singleton instance."""

    def test_pulse_graph_instance_exists(self):
        """pulse_graph instance exists in graph module."""
        from src.agents.pulse.graph import pulse_graph

        assert pulse_graph is not None
        assert hasattr(pulse_graph, "tenant_id")


class TestPulseGraphFunction:
    """Tests for pulse_graph() function."""

    def test_pulse_graph_function_returns_none(self):
        """pulse_graph() returns None (placeholder stub)."""
        from src.agents.pulse import pulse_graph

        result = pulse_graph()
        assert result is None


class TestStubVerification:
    """Verify stub has no LLM dependencies or real implementations."""

    def test_no_nodes_module(self):
        """pulse.nodes module does not exist."""
        import src.agents.pulse

        assert not hasattr(src.agents.pulse, "nodes")

    def test_no_llm_imports_in_pulse(self):
        """pulse module has no LLM-related imports."""
        import src.agents.pulse

        module_attrs = dir(src.agents.pulse)
        llm_keywords = ["openai", "anthropic", "llm", "client", "model"]
        for keyword in llm_keywords:
            assert not any(keyword in attr.lower() for attr in module_attrs), f"Found LLM-related import: {keyword}"
