"""Tests for RAG Kernel.

V3.0 TODO: rag_kernel.py unchanged from V2.0, pending migration.
See PRD Section 10 for spec.
"""
import pytest

try:
    from src.memory.rag_kernel import RAGKernel
    HAS_RAG_KERNEL = True
except ImportError:
    HAS_RAG_KERNEL = False

pytestmark = pytest.mark.skipif(not HAS_RAG_KERNEL, reason="rag_kernel.py not implemented")


class TestRAGKernel:
    def test_classify_intent_pulse(self):
        k = RAGKernel()
        assert k._classify_intent("generate daily pulse") == "pulse_generation"

    def test_classify_intent_anomaly(self):
        k = RAGKernel()
        assert k._classify_intent("explain this anomaly") == "anomaly_explanation"

    def test_classify_intent_investor(self):
        k = RAGKernel()
        assert k._classify_intent("draft investor update") == "investor_narrative"

    def test_classify_intent_metric(self):
        k = RAGKernel()
        assert k._classify_intent("what is our MRR?") == "metric_lookup"

    def test_classify_intent_causal(self):
        k = RAGKernel()
        assert k._classify_intent("why did this happen?") == "causal_reasoning"

    def test_assemble_under_800_tokens(self):
        k = RAGKernel()
        ctx = k._assemble("pulse", "Tenant: x", [], {"mrr": 9000}, "pulse", 800)
        assert len(ctx) <= 800 * 4

    def test_assemble_truncates_history_when_over_limit(self):
        k = RAGKernel()
        big_history = [{"content": "x" * 2000} for _ in range(10)]
        ctx = k._assemble("pulse", "Tenant: x", big_history, {}, "pulse", 800)
        assert len(ctx) <= 800 * 4

    def test_load_returns_string(self):
        k = RAGKernel()
        ctx = k.load("tenant-a", "generate pulse", {"mrr": 9000})
        assert isinstance(ctx, str)
        assert "[FOUNDER IDENTITY]" in ctx
        assert "[TASK]" in ctx