"""Tests for Phase 5 Learning Flywheel components — failure buckets, trace store, error feedback."""
import pytest


class TestFailureBuckets:
    """record_failure, get_failures, get_failure_summary, resolve_failure, clear_failures."""

    def setup_method(self):
        from src.llmops.failure_buckets import clear_failures
        clear_failures()

    def test_record_failure_returns_event_with_non_empty_id(self):
        from src.llmops.failure_buckets import record_failure, FailureBucket
        event = record_failure(
            tenant_id="t1",
            bucket=FailureBucket.DATA_QUALITY,
            source="test",
            operation="op",
            error_message="bad data",
        )
        assert event.id
        assert len(event.id) > 0

    def test_record_failure_stores_event_get_failures_returns_it(self):
        from src.llmops.failure_buckets import record_failure, get_failures, FailureBucket
        event = record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err")
        results = get_failures()
        ids = [e.id for e in results]
        assert event.id in ids

    def test_get_failures_with_tenant_id_filter_returns_only_matching(self):
        from src.llmops.failure_buckets import record_failure, get_failures, FailureBucket
        e1 = record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err1")
        e2 = record_failure("t2", FailureBucket.DATA_QUALITY, "src", "op", "err2")
        results = get_failures(tenant_id="t1")
        assert all(e.tenant_id == "t1" for e in results)
        assert e1.id in [e.id for e in results]
        assert e2.id not in [e.id for e in results]

    def test_get_failures_with_bucket_filter_returns_only_matching(self):
        from src.llmops.failure_buckets import record_failure, get_failures, FailureBucket
        e1 = record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err1")
        e2 = record_failure("t1", FailureBucket.REASONING_FAILURE, "src", "op", "err2")
        results = get_failures(bucket=FailureBucket.DATA_QUALITY)
        assert all(e.bucket == FailureBucket.DATA_QUALITY for e in results)
        assert e1.id in [e.id for e in results]
        assert e2.id not in [e.id for e in results]

    def test_get_failures_with_limit_returns_at_most_n_events(self):
        from src.llmops.failure_buckets import record_failure, get_failures, FailureBucket
        for i in range(10):
            record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", f"err{i}")
        results = get_failures(limit=3)
        assert len(results) == 3

    def test_get_failure_summary_returns_correct_counts_by_bucket(self):
        from src.llmops.failure_buckets import record_failure, get_failure_summary, FailureBucket
        record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err1")
        record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err2")
        record_failure("t1", FailureBucket.REASONING_FAILURE, "src", "op", "err3")
        summary = get_failure_summary()
        assert summary.get("data_quality") == 2
        assert summary.get("reasoning_failure") == 1

    def test_get_failure_summary_with_tenant_id_filters_correctly(self):
        from src.llmops.failure_buckets import record_failure, get_failure_summary, FailureBucket
        record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err1")
        record_failure("t2", FailureBucket.DATA_QUALITY, "src", "op", "err2")
        summary = get_failure_summary(tenant_id="t1")
        assert summary.get("data_quality") == 1

    def test_resolve_failure_marks_event_as_resolved_with_resolution_text(self):
        from src.llmops.failure_buckets import record_failure, resolve_failure, get_failures, FailureBucket
        event = record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err")
        result = resolve_failure(event.id, "fixed the data pipeline")
        assert result is True
        resolved = get_failures()[0]
        assert resolved.resolved is True
        assert resolved.resolution == "fixed the data pipeline"

    def test_resolve_failure_on_unknown_id_returns_false(self):
        from src.llmops.failure_buckets import resolve_failure
        result = resolve_failure("nonexistent", "nope")
        assert result is False

    def test_clear_failures_clears_all_events_and_returns_count(self):
        from src.llmops.failure_buckets import record_failure, clear_failures, get_failures, FailureBucket
        record_failure("t1", FailureBucket.DATA_QUALITY, "src", "op", "err1")
        record_failure("t1", FailureBucket.REASONING_FAILURE, "src", "op", "err2")
        count = clear_failures()
        assert count == 2
        assert get_failures() == []


class TestClassifyError:
    """_classify_error maps exception types to FailureBucket."""

    def test_connection_error_returns_data_quality(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(ConnectionError("connection refused"))
        assert result == FailureBucket.DATA_QUALITY

    def test_timeout_error_returns_data_quality(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(TimeoutError("request timed out"))
        assert result == FailureBucket.DATA_QUALITY

    def test_key_error_returns_context_assembly_error(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(KeyError("missing_key"))
        assert result == FailureBucket.CONTEXT_ASSEMBLY_ERROR

    def test_value_error_threshold_exceeded_returns_rules_interpretation(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(ValueError("threshold exceeded"))
        assert result == FailureBucket.RULES_INTERPRETATION

    def test_generic_value_error_returns_unknown(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(ValueError("some generic error"))
        assert result == FailureBucket.UNKNOWN

    def test_permission_error_returns_approval_policy_error(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(PermissionError("access denied"))
        assert result == FailureBucket.APPROVAL_POLICY_ERROR

    def test_zero_division_error_returns_reasoning_failure(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(ZeroDivisionError("division by zero"))
        assert result == FailureBucket.REASONING_FAILURE

    def test_not_implemented_error_returns_wrong_tool_selection(self):
        from src.llmops.failure_buckets import _classify_error, FailureBucket
        result = _classify_error(NotImplementedError("not implemented"))
        assert result == FailureBucket.WRONG_TOOL_SELECTION


class TestTraceStore:
    """record_trace, get_traces, get_trace_summary."""

    def setup_method(self):
        from src.llmops.failure_buckets import clear_failures
        from src.llmops.trace_store import _trace_store
        clear_failures()
        _trace_store.clear()

    def make_trace(self, **kwargs):
        from src.llmops.trace_store import AgentTrace
        from src.llmops.failure_buckets import FailureBucket
        defaults = dict(
            trace_id="tr-1",
            tenant_id="t1",
            agent_name="agent-a",
            action="act",
            duration_ms=100.0,
            llm_calls=2,
            llm_tokens=500,
            llm_cost_usd=0.01,
            status="success",
            failure_bucket=None,
            error=None,
            created_at="2026-06-01T00:00:00Z",
        )
        defaults.update(kwargs)
        return AgentTrace(**defaults)

    def test_record_trace_appends_trace_get_traces_returns_it(self):
        from src.llmops.trace_store import record_trace, get_traces
        trace = self.make_trace(trace_id="tr-abc")
        record_trace(trace)
        results = get_traces()
        assert len(results) == 1
        assert results[0].trace_id == "tr-abc"

    def test_get_traces_with_tenant_id_filter_returns_only_matching(self):
        from src.llmops.trace_store import record_trace, get_traces
        record_trace(self.make_trace(trace_id="t1", tenant_id="t1"))
        record_trace(self.make_trace(trace_id="t2", tenant_id="t2"))
        results = get_traces(tenant_id="t1")
        assert all(t.tenant_id == "t1" for t in results)
        assert len(results) == 1

    def test_get_traces_with_agent_name_filter_returns_only_matching(self):
        from src.llmops.trace_store import record_trace, get_traces
        record_trace(self.make_trace(trace_id="t1", agent_name="agent-a"))
        record_trace(self.make_trace(trace_id="t2", agent_name="agent-b"))
        results = get_traces(agent_name="agent-a")
        assert all(t.agent_name == "agent-a" for t in results)
        assert len(results) == 1

    def test_get_traces_with_status_filter_returns_only_matching(self):
        from src.llmops.trace_store import record_trace, get_traces
        record_trace(self.make_trace(trace_id="t1", status="success"))
        record_trace(self.make_trace(trace_id="t2", status="failed"))
        results = get_traces(status="success")
        assert all(t.status == "success" for t in results)
        assert len(results) == 1

    def test_get_traces_with_limit_returns_at_most_n_traces(self):
        from src.llmops.trace_store import record_trace, get_traces
        for i in range(10):
            record_trace(self.make_trace(trace_id=f"t{i}"))
        results = get_traces(limit=4)
        assert len(results) == 4

    def test_get_trace_summary_with_no_traces_returns_zeros(self):
        from src.llmops.trace_store import get_trace_summary
        summary = get_trace_summary()
        assert summary["total_traces"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["avg_duration_ms"] == 0.0
        assert summary["total_cost_usd"] == 0.0
        assert summary["failure_buckets"] == {}

    def test_get_trace_summary_computes_correct_success_rate(self):
        from src.llmops.trace_store import record_trace, get_trace_summary
        record_trace(self.make_trace(trace_id="t1", status="success"))
        record_trace(self.make_trace(trace_id="t2", status="success"))
        record_trace(self.make_trace(trace_id="t3", status="failed"))
        summary = get_trace_summary()
        assert summary["total_traces"] == 3
        assert summary["success_rate"] == round(2 / 3, 4)

    def test_get_trace_summary_computes_correct_avg_duration_ms(self):
        from src.llmops.trace_store import record_trace, get_trace_summary
        record_trace(self.make_trace(trace_id="t1", duration_ms=50.0))
        record_trace(self.make_trace(trace_id="t2", duration_ms=150.0))
        summary = get_trace_summary()
        assert summary["avg_duration_ms"] == 100.0

    def test_get_trace_summary_computes_correct_total_cost_usd(self):
        from src.llmops.trace_store import record_trace, get_trace_summary
        record_trace(self.make_trace(trace_id="t1", llm_cost_usd=0.02))
        record_trace(self.make_trace(trace_id="t2", llm_cost_usd=0.03))
        summary = get_trace_summary()
        assert summary["total_cost_usd"] == 0.05

    def test_get_trace_summary_computes_correct_failure_buckets_dict(self):
        from src.llmops.trace_store import record_trace, get_trace_summary
        from src.llmops.failure_buckets import FailureBucket
        record_trace(self.make_trace(trace_id="t1", status="failed", failure_bucket=FailureBucket.DATA_QUALITY))
        record_trace(self.make_trace(trace_id="t2", status="failed", failure_bucket=FailureBucket.DATA_QUALITY))
        record_trace(self.make_trace(trace_id="t3", status="failed", failure_bucket=FailureBucket.REASONING_FAILURE))
        record_trace(self.make_trace(trace_id="t4", status="success", failure_bucket=None))
        summary = get_trace_summary()
        assert summary["failure_buckets"]["data_quality"] == 2
        assert summary["failure_buckets"]["reasoning_failure"] == 1

    def test_get_trace_summary_with_tenant_id_filters_correctly(self):
        from src.llmops.trace_store import record_trace, get_trace_summary
        record_trace(self.make_trace(trace_id="t1", tenant_id="t1", status="success"))
        record_trace(self.make_trace(trace_id="t2", tenant_id="t2", status="failed"))
        summary = get_trace_summary(tenant_id="t1")
        assert summary["total_traces"] == 1
        assert summary["success_rate"] == 1.0

    def test_record_trace_auto_sets_created_at_when_empty(self):
        from src.llmops.trace_store import record_trace, get_traces
        trace = self.make_trace(trace_id="t1", created_at="")
        record_trace(trace)
        results = get_traces()
        assert results[0].created_at != ""
        assert results[0].created_at is not None


class TestErrorFeedback:
    """capture_execution_error."""

    def setup_method(self):
        from src.llmops.failure_buckets import clear_failures
        from src.llmops.trace_store import _trace_store
        clear_failures()
        _trace_store.clear()

    def test_capture_execution_error_returns_dict_with_expected_keys(self):
        from src.orchestrators.error_feedback import capture_execution_error
        result = capture_execution_error(
            action_type="test_action",
            error=ValueError("something broke"),
            tenant_id="t1",
        )
        assert isinstance(result, dict)
        assert "error_type" in result
        assert "error_message" in result
        assert "bucket" in result
        assert "trace_id" in result
        assert "timestamp" in result

    def test_capture_execution_error_records_failure_event(self):
        from src.orchestrators.error_feedback import capture_execution_error
        from src.llmops.failure_buckets import get_failures
        capture_execution_error("act", ValueError("fail"), "t1")
        failures = get_failures()
        assert len(failures) >= 1

    def test_capture_execution_error_records_trace(self):
        from src.orchestrators.error_feedback import capture_execution_error
        from src.llmops.trace_store import get_traces
        capture_execution_error("act", ValueError("fail"), "t1")
        traces = get_traces()
        assert len(traces) >= 1
        assert traces[0].status == "failed"

    def test_capture_execution_error_with_connection_error_classifies_as_data_quality(self):
        from src.orchestrators.error_feedback import capture_execution_error
        result = capture_execution_error("act", ConnectionError("refused"), "t1")
        assert result["bucket"] == "data_quality"


class TestFormatErrorsForContext:
    """format_errors_for_context."""

    def test_format_errors_for_context_returns_empty_list_when_input_empty(self):
        from src.orchestrators.error_feedback import format_errors_for_context
        result = format_errors_for_context([])
        assert result == []

    def test_format_errors_for_context_limits_to_max_errors(self):
        from src.orchestrators.error_feedback import format_errors_for_context
        errors = [
            {"error_type": "E1", "error_message": "msg1", "bucket": "b1", "trace_id": "t1", "timestamp": "2026-01-01T00:00:0Z"},
            {"error_type": "E2", "error_message": "msg2", "bucket": "b2", "trace_id": "t2", "timestamp": "2026-01-02T00:00:0Z"},
            {"error_type": "E3", "error_message": "msg3", "bucket": "b3", "trace_id": "t3", "timestamp": "2026-01-03T00:00:0Z"},
            {"error_type": "E4", "error_message": "msg4", "bucket": "b4", "trace_id": "t4", "timestamp": "2026-01-04T00:00:0Z"},
        ]
        result = format_errors_for_context(errors, max_errors=2)
        assert len(result) == 2

    def test_format_errors_for_context_sorts_by_timestamp_descending(self):
        from src.orchestrators.error_feedback import format_errors_for_context
        errors = [
            {"error_type": "E1", "error_message": "old", "bucket": "b1", "trace_id": "t1", "timestamp": "2026-01-01T00:00:00Z"},
            {"error_type": "E2", "error_message": "new", "bucket": "b2", "trace_id": "t2", "timestamp": "2026-01-03T00:00:00Z"},
            {"error_type": "E3", "error_message": "mid", "bucket": "b3", "trace_id": "t3", "timestamp": "2026-01-02T00:00:00Z"},
        ]
        result = format_errors_for_context(errors)
        timestamps = [e["timestamp"] for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_format_errors_for_context_truncates_messages_longer_than_500_chars(self):
        from src.orchestrators.error_feedback import format_errors_for_context
        long_msg = "x" * 600
        errors = [
            {"error_type": "E1", "error_message": long_msg, "bucket": "b1", "trace_id": "t1", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = format_errors_for_context(errors, max_errors=5)
        assert len(result[0]["error_message"]) == 500
        assert result[0]["error_message"].endswith("...")
