"""Integration tests for orchestrator context compilation + failure/trace stores with real Redis."""

from unittest.mock import MagicMock, patch

import pytest


class TestOrchestratorStateDocker:
    """Integration tests requiring a running Redis instance."""

    @pytest.mark.asyncio
    async def test_compile_context_events_from_redis(self):
        from src.services.state_store import StateStore, reset_redis_client

        reset_redis_client()
        store = StateStore(prefix="ctx:test-tenant")
        try:
            store.set("events:test-agent", [{"event": "evt-0"}, {"event": "evt-1"}, {"event": "evt-2"}])
            store.set("findings:test-agent", [{"finding": "f0"}, {"finding": "f1"}])

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

            with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
                from src.orchestrators.context_compiler import compile_context

                ctx = await compile_context(
                    tenant_id="test-tenant",
                    goal="test",
                    agent_name="test-agent",
                )

            assert len(ctx.relevant_events) == 3
            assert len(ctx.active_findings) == 2
            assert ctx.mission_summary["tenant_id"] == "test-tenant"
        finally:
            store.clear_prefix()

    @pytest.mark.asyncio
    async def test_compile_context_max_events_from_redis(self):
        from src.services.state_store import StateStore, reset_redis_client

        reset_redis_client()
        store = StateStore(prefix="ctx:maxtest-tenant")
        try:
            events = [{"event": f"evt-{i}"} for i in range(10)]
            store.set("events:test-agent", events)

            mock_state = MagicMock()
            mock_state.tenant_id = "maxtest-tenant"
            mock_state.burn_alert = False
            mock_state.burn_severity = None
            mock_state.runway_days = 90
            mock_state.mrr_trend = "stable"
            mock_state.churn_rate = 0.03
            mock_state.error_spike = False
            mock_state.active_alerts = None
            mock_state.founder_focus = None

            with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
                from src.orchestrators.context_compiler import compile_context

                ctx = await compile_context(
                    tenant_id="maxtest-tenant",
                    goal="test",
                    agent_name="test-agent",
                    max_events=3,
                )

            assert len(ctx.relevant_events) == 3
            assert ctx.relevant_events[0]["event"] == "evt-7"
            assert ctx.relevant_events[1]["event"] == "evt-8"
            assert ctx.relevant_events[2]["event"] == "evt-9"
        finally:
            store.clear_prefix()

    @pytest.mark.asyncio
    async def test_compile_context_empty_state(self):
        from src.services.state_store import reset_redis_client

        reset_redis_client()

        mock_state = MagicMock()
        mock_state.tenant_id = "empty-tenant"
        mock_state.burn_alert = False
        mock_state.burn_severity = None
        mock_state.runway_days = 0
        mock_state.mrr_trend = None
        mock_state.churn_rate = None
        mock_state.error_spike = False
        mock_state.active_alerts = None
        mock_state.founder_focus = None

        with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
            from src.orchestrators.context_compiler import compile_context

            ctx = await compile_context(
                tenant_id="empty-tenant",
                goal="test",
                agent_name="test-agent",
            )

        assert ctx.relevant_events == []
        assert ctx.active_findings == []

    @pytest.mark.asyncio
    async def test_compile_context_with_errors(self):
        from src.services.state_store import StateStore, reset_redis_client

        reset_redis_client()
        store = StateStore(prefix="ctx:errtest-tenant")
        try:
            store.set("events:test-agent", [{"event": "evt-0"}])
            store.set("findings:test-agent", [{"finding": "f0"}])
            store.set("errors:test-agent", [{"error": "err-0"}, {"error": "err-1"}])

            mock_state = MagicMock()
            mock_state.tenant_id = "errtest-tenant"
            mock_state.burn_alert = False
            mock_state.burn_severity = None
            mock_state.runway_days = 60
            mock_state.mrr_trend = None
            mock_state.churn_rate = None
            mock_state.error_spike = True
            mock_state.active_alerts = None
            mock_state.founder_focus = None

            with patch("src.session.mission_state.get_mission_state", return_value=mock_state):
                from src.orchestrators.context_compiler import compile_context

                ctx = await compile_context(
                    tenant_id="errtest-tenant",
                    goal="test",
                    agent_name="test-agent",
                    include_errors=True,
                )

            assert ctx.error_context is not None
            assert len(ctx.error_context) == 2
        finally:
            store.clear_prefix()

    def test_compile_context_to_messages(self):
        from src.orchestrators.context_compiler import CompiledContext, compile_context_to_messages

        ctx = CompiledContext(
            goal="test-goal",
            return_format={"type": "json"},
            warnings=["warn-1"],
            mission_summary={"tenant_id": "t1"},
            relevant_events=[],
            active_findings=[],
        )
        messages = compile_context_to_messages(ctx, "System prompt")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Compiled Context:" in messages[0]["content"]
        assert "System prompt" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Proceed with analysis"

    def test_failure_bucket_classify_error(self):
        from src.llmops.failure_buckets import FailureBucket, _classify_error, clear_failures

        clear_failures()
        assert _classify_error(ConnectionError("refused")) == FailureBucket.DATA_QUALITY
        assert _classify_error(ValueError("threshold exceeded")) == FailureBucket.RULES_INTERPRETATION
        assert _classify_error(PermissionError("denied")) == FailureBucket.APPROVAL_POLICY_ERROR
        clear_failures()

    def test_failure_event_lifecycle(self):
        from src.llmops.failure_buckets import FailureBucket, clear_failures, get_failures, get_failure_summary, record_failure, resolve_failure

        clear_failures()
        try:
            event = record_failure(
                tenant_id="t1",
                bucket=FailureBucket.DATA_QUALITY,
                source="test",
                operation="test_op",
                error_message="test error",
                trace_id="trace-1",
            )
            assert event.id is not None

            failures = get_failures(tenant_id="t1")
            assert len(failures) == 1
            assert failures[0].id == event.id

            resolved = resolve_failure(event.id, "fixed")
            assert resolved is True

            failures = get_failures(tenant_id="t1")
            assert failures[0].resolved is True

            summary = get_failure_summary(tenant_id="t1")
            assert summary.get("data_quality") == 1
        finally:
            clear_failures()

    def test_trace_store_record_and_summary(self):
        from src.llmops.failure_buckets import FailureBucket
        from src.llmops.trace_store import AgentTrace, _trace_store, get_trace_summary, get_traces

        _trace_store.clear()
        try:
            trace_ok = AgentTrace(
                trace_id="tr-1",
                tenant_id="t1",
                agent_name="agent-a",
                action="act-1",
                duration_ms=100.0,
                llm_calls=1,
                llm_tokens=50,
                llm_cost_usd=0.01,
                status="success",
            )
            trace_fail = AgentTrace(
                trace_id="tr-2",
                tenant_id="t1",
                agent_name="agent-a",
                action="act-2",
                duration_ms=200.0,
                llm_calls=2,
                llm_tokens=100,
                llm_cost_usd=0.02,
                status="failed",
                failure_bucket=FailureBucket.DATA_QUALITY,
                error="connection refused",
            )
            _trace_store.append(trace_ok)
            _trace_store.append(trace_fail)

            traces = get_traces(tenant_id="t1")
            assert len(traces) == 2

            summary = get_trace_summary(tenant_id="t1")
            assert summary["total_traces"] == 2
            assert summary["success_rate"] == 0.5
            assert "data_quality" in summary["failure_buckets"]
            assert summary["failure_buckets"]["data_quality"] == 1
        finally:
            _trace_store.clear()

    def test_capture_execution_error_integration(self):
        from src.llmops.failure_buckets import clear_failures
        from src.llmops.trace_store import _trace_store
        from src.orchestrators.error_feedback import capture_execution_error

        clear_failures()
        _trace_store.clear()
        try:
            result = capture_execution_error(
                action_type="test_action",
                error=ConnectionError("connection refused"),
                tenant_id="t1",
            )

            assert result["bucket"] == "data_quality"
            assert "error_type" in result
            assert "error_message" in result
            assert "trace_id" in result
            assert "timestamp" in result

            from src.llmops.failure_buckets import get_failures
            from src.llmops.trace_store import get_traces

            failures = get_failures(tenant_id="t1")
            assert len(failures) >= 1

            traces = get_traces(tenant_id="t1")
            assert len(traces) >= 1
        finally:
            clear_failures()
            _trace_store.clear()

    def test_format_errors_for_context(self):
        from src.orchestrators.error_feedback import format_errors_for_context

        errors = [
            {"error_type": "E1", "error_message": "msg1", "bucket": "data_quality", "trace_id": "t1", "timestamp": "2025-01-01T00:00:00"},
            {"error_type": "E2", "error_message": "msg2", "bucket": "rules_interpretation", "trace_id": "t2", "timestamp": "2025-01-03T00:00:00"},
            {"error_type": "E3", "error_message": "msg3", "bucket": "unknown", "trace_id": "t3", "timestamp": "2025-01-02T00:00:00"},
            {"error_type": "E4", "error_message": "msg4", "bucket": "data_quality", "trace_id": "t4", "timestamp": "2025-01-04T00:00:00"},
        ]

        result = format_errors_for_context(errors, max_errors=2)

        assert len(result) == 2
        assert result[0]["timestamp"] > result[1]["timestamp"]
        assert result[0]["error_type"] == "E4"
        assert result[1]["error_type"] == "E2"
