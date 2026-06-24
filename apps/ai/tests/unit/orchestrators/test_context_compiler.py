"""Tests for Phase 4 Context Compiler components - TDD Red phase."""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestCompiledContext:
    """Pydantic model for compiled agent context."""

    def test_compiled_context_has_all_fields(self):
        from src.orchestrators.context_compiler import CompiledContext
        field_names = set(CompiledContext.model_fields.keys())
        expected = {
            "goal", "return_format", "warnings", "mission_summary",
            "relevant_events", "active_findings", "user_request", "error_context",
        }
        assert field_names == expected

    def test_compiled_context_user_request_defaults_to_none(self):
        from src.orchestrators.context_compiler import CompiledContext
        ctx = CompiledContext(
            goal="test",
            return_format={},
            warnings=[],
            mission_summary={},
            relevant_events=[],
            active_findings=[],
        )
        assert ctx.user_request is None

    def test_compiled_context_error_context_defaults_to_none(self):
        from src.orchestrators.context_compiler import CompiledContext
        ctx = CompiledContext(
            goal="test",
            return_format={},
            warnings=[],
            mission_summary={},
            relevant_events=[],
            active_findings=[],
        )
        assert ctx.error_context is None


class TestCompileContext:
    """Async compilation of agent context from StateStore and MissionState."""

    @pytest.mark.asyncio
    async def test_compile_context_returns_compiled_context(self):
        from src.orchestrators.context_compiler import compile_context

        mock_state = MagicMock()
        mock_state.tenant_id = "test-tenant"
        mock_state.burn_alert = True
        mock_state.burn_severity = "warning"
        mock_state.runway_days = 180
        mock_state.mrr_trend = "growing"
        mock_state.churn_rate = 0.05
        mock_state.error_spike = False
        mock_state.active_alerts = "FG-01"
        mock_state.founder_focus = "revenue"

        mock_store = MagicMock()
        mock_store.get.side_effect = lambda k: (
            [{"event": f"evt-{i}"} for i in range(7)] if "events" in k
            else [{"finding": "f1"}]
        )

        with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
            with patch("src.orchestrators.context_compiler.StateStore", return_value=mock_store):
                result = await compile_context(
                    tenant_id="test-tenant",
                    goal="test-goal",
                    agent_name="test-agent",
                )

        assert isinstance(result.goal, str)
        assert result.goal == "test-goal"
        assert isinstance(result.return_format, dict)
        assert isinstance(result.warnings, list)
        assert isinstance(result.mission_summary, dict)
        assert isinstance(result.relevant_events, list)
        assert isinstance(result.active_findings, list)
        assert result.user_request is None
        assert result.error_context is None

    @pytest.mark.asyncio
    async def test_compile_context_includes_up_to_max_events(self):
        from src.orchestrators.context_compiler import compile_context

        mock_state = MagicMock()
        mock_state.tenant_id = "test-tenant"
        mock_state.burn_alert = True
        mock_state.burn_severity = "warning"
        mock_state.runway_days = 180
        mock_state.mrr_trend = "growing"
        mock_state.churn_rate = 0.05
        mock_state.error_spike = False
        mock_state.active_alerts = "FG-01"
        mock_state.founder_focus = "revenue"

        events = [{"event": f"evt-{i}"} for i in range(10)]

        mock_store = MagicMock()
        mock_store.get.side_effect = lambda k: (
            events if "events" in k
            else [{"finding": "f1"}]
        )

        with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
            with patch("src.orchestrators.context_compiler.StateStore", return_value=mock_store):
                result = await compile_context(
                    tenant_id="test-tenant",
                    goal="test-goal",
                    agent_name="test-agent",
                    max_events=5,
                )

        assert len(result.relevant_events) == 5
        assert result.relevant_events == events[-5:]

    @pytest.mark.asyncio
    async def test_compile_context_when_no_events_returns_empty_list(self):
        from src.orchestrators.context_compiler import compile_context

        mock_state = MagicMock()
        mock_state.tenant_id = "test-tenant"
        mock_state.burn_alert = True
        mock_state.burn_severity = "warning"
        mock_state.runway_days = 180
        mock_state.mrr_trend = "growing"
        mock_state.churn_rate = 0.05
        mock_state.error_spike = False
        mock_state.active_alerts = "FG-01"
        mock_state.founder_focus = "revenue"

        mock_store = MagicMock()
        mock_store.get.return_value = None

        with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
            with patch("src.orchestrators.context_compiler.StateStore", return_value=mock_store):
                result = await compile_context(
                    tenant_id="test-tenant",
                    goal="test-goal",
                    agent_name="test-agent",
                )

        assert result.relevant_events == []
        assert result.active_findings == []

    @pytest.mark.asyncio
    async def test_compile_context_when_include_errors_populates_error_context(self):
        from src.orchestrators.context_compiler import compile_context

        mock_state = MagicMock()
        mock_state.tenant_id = "test-tenant"
        mock_state.burn_alert = True
        mock_state.burn_severity = "warning"
        mock_state.runway_days = 180
        mock_state.mrr_trend = "growing"
        mock_state.churn_rate = 0.05
        mock_state.error_spike = False
        mock_state.active_alerts = "FG-01"
        mock_state.founder_focus = "revenue"

        mock_store = MagicMock()
        mock_store.get.side_effect = lambda k: (
            [{"event": "evt-1"}] if "events" in k
            else [{"finding": "f1"}] if "findings" in k
            else [{"error": "err-1"}]
        )

        with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
            with patch("src.orchestrators.context_compiler.StateStore", return_value=mock_store):
                result = await compile_context(
                    tenant_id="test-tenant",
                    goal="test-goal",
                    agent_name="test-agent",
                    include_errors=True,
                )

        assert result.error_context is not None
        assert len(result.error_context) == 1
        assert result.error_context[0]["error"] == "err-1"


class TestCompileContextToMessages:
    """Conversion of CompiledContext to LLM message format."""

    def test_compile_context_to_messages_returns_two_messages(self):
        from src.orchestrators.context_compiler import (
            compile_context_to_messages, CompiledContext,
        )
        ctx = CompiledContext(
            goal="test-goal",
            return_format={"type": "json"},
            warnings=[],
            mission_summary={"tenant_id": "t1"},
            relevant_events=[],
            active_findings=[],
        )
        messages = compile_context_to_messages(ctx, "You are an agent.")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_compile_context_to_messages_system_contains_serialized_context(self):
        from src.orchestrators.context_compiler import (
            compile_context_to_messages, CompiledContext,
        )
        ctx = CompiledContext(
            goal="test-goal",
            return_format={"type": "json"},
            warnings=[],
            mission_summary={"tenant_id": "t1"},
            relevant_events=[],
            active_findings=[],
        )
        messages = compile_context_to_messages(ctx, "You are an agent.")
        assert "Compiled Context:" in messages[0]["content"]
        assert "test-goal" in messages[0]["content"]
        assert "tenant_id" in messages[0]["content"]

    def test_compile_context_to_messages_when_user_request_is_none(self):
        from src.orchestrators.context_compiler import (
            compile_context_to_messages, CompiledContext,
        )
        ctx = CompiledContext(
            goal="test-goal",
            return_format={"type": "json"},
            warnings=[],
            mission_summary={},
            relevant_events=[],
            active_findings=[],
            user_request=None,
        )
        messages = compile_context_to_messages(ctx, "System prompt")
        assert messages[1]["content"] == "Proceed with analysis"

    def test_compile_context_to_messages_when_user_request_provided(self):
        from src.orchestrators.context_compiler import (
            compile_context_to_messages, CompiledContext,
        )
        ctx = CompiledContext(
            goal="test-goal",
            return_format={"type": "json"},
            warnings=[],
            mission_summary={},
            relevant_events=[],
            active_findings=[],
            user_request="What is the burn rate?",
        )
        messages = compile_context_to_messages(ctx, "System prompt")
        assert "What is the burn rate?" in messages[1]["content"]


class TestPruneToolCalls:
    """Pruning of oldest tool call interactions when >3 exist."""

    def test_prune_tool_calls_no_tool_interactions_unchanged(self):
        from src.orchestrators.context_pruner import prune_tool_calls
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = prune_tool_calls(messages)
        assert result == messages

    def test_prune_tool_calls_three_or_fewer_tool_calls_unchanged(self):
        from src.orchestrators.context_pruner import prune_tool_calls
        messages = [
            {"role": "user", "content": "search"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "content": "res1", "tool_call_id": "c1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c2"}]},
            {"role": "tool", "content": "res2", "tool_call_id": "c2"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c3"}]},
            {"role": "tool", "content": "res3", "tool_call_id": "c3"},
            {"role": "assistant", "content": "done"},
        ]
        result = prune_tool_calls(messages)
        assert result == messages

    def test_prune_tool_calls_removes_oldest_when_more_than_three(self):
        from src.orchestrators.context_pruner import prune_tool_calls
        messages = [
            {"role": "user", "content": "search"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "content": "res1", "tool_call_id": "c1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c2"}]},
            {"role": "tool", "content": "res2", "tool_call_id": "c2"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c3"}]},
            {"role": "tool", "content": "res3", "tool_call_id": "c3"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c4"}]},
            {"role": "tool", "content": "res4", "tool_call_id": "c4"},
            {"role": "assistant", "content": "done"},
        ]
        result = prune_tool_calls(messages)
        assert len(result) == 8
        assert result[0] == messages[0]
        assert result[1] == messages[3]
        assert result[2] == messages[4]
        assert result[3] == messages[5]
        assert result[4] == messages[6]
        assert result[5] == messages[7]
        assert result[6] == messages[8]
        assert result[7] == messages[9]


class TestPruneOldestMessages:
    """Pruning of oldest messages to fit within max_messages limit."""

    def test_prune_oldest_messages_keeps_messages_when_within_limit(self):
        from src.orchestrators.context_pruner import prune_oldest_messages
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        result = prune_oldest_messages(messages, max_messages=20)
        assert result == messages

    def test_prune_oldest_messages_preserves_system_and_last_user(self):
        from src.orchestrators.context_pruner import prune_oldest_messages
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "response1"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "response2"},
            {"role": "user", "content": "last"},
        ]
        result = prune_oldest_messages(messages, max_messages=3)
        assert result[0] == messages[0]
        assert result[-1] == messages[-1]

    def test_prune_oldest_messages_max_messages_one(self):
        from src.orchestrators.context_pruner import prune_oldest_messages
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "user", "content": "last"},
        ]
        result = prune_oldest_messages(messages, max_messages=1)
        assert len(result) == 2
        assert result[0] == messages[0]
        assert result[1] == messages[2]

    def test_prune_oldest_messages_no_system_message(self):
        from src.orchestrators.context_pruner import prune_oldest_messages
        messages = [
            {"role": "user", "content": "first"},
            {"role": "user", "content": "last"},
        ]
        result = prune_oldest_messages(messages, max_messages=1)
        assert len(result) == 1
        assert result[0] == messages[1]

    def test_prune_oldest_messages_empty_list(self):
        from src.orchestrators.context_pruner import prune_oldest_messages
        result = prune_oldest_messages([], max_messages=20)
        assert result == []
