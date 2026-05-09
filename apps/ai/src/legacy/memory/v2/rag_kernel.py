"""RAG Kernel — assembles ≤800 tokens of context per LLM call."""
from __future__ import annotations
import json
from typing import Any


class RAGKernel:
    INTENT_TYPES = [
        "metric_lookup", "pattern_analysis", "causal_reasoning",
        "commitment_check", "pulse_generation", "anomaly_explanation",
        "investor_narrative",
    ]

    def load(self, tenant_id: str, task: str, signal: dict,
             max_tokens: int = 800) -> str:
        """Main entry point. Returns assembled context string."""
        intent = self._classify_intent(task)
        semantic = self._retrieve_semantic(tenant_id, intent)
        episodic = self._retrieve_episodic(tenant_id, task, intent)
        return self._assemble(intent, semantic, episodic, signal, task, max_tokens)

    def _classify_intent(self, task: str) -> str:
        t = task.lower()
        if "mrr" in t or "revenue" in t or "metric" in t:
            return "metric_lookup"
        if "pattern" in t or "trend" in t:
            return "pattern_analysis"
        if "caus" in t or "why" in t:
            return "causal_reasoning"
        if "commit" in t:
            return "commitment_check"
        if "pulse" in t:
            return "pulse_generation"
        if "anomal" in t:
            return "anomaly_explanation"
        if "investor" in t:
            return "investor_narrative"
        return "metric_lookup"

    def _retrieve_semantic(self, tenant_id: str, intent: str) -> str:
        return f"Tenant: {tenant_id}"

    def _retrieve_episodic(self, tenant_id: str, task: str, intent: str) -> list:
        return []

    def _rerank(self, results: list, query: str) -> list:
        return results[:5]

    def _assemble(self, intent: str, semantic: str, episodic: list,
                  signal: dict, task: str, max_tokens: int) -> str:
        sections = [
            f"[FOUNDER IDENTITY]\n{semantic}",
            f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in episodic]),
            f"[CURRENT SIGNAL]\n{json.dumps(signal, indent=2, default=str)}",
            f"[TASK]\n{task}",
        ]
        assembled = "\n\n".join(sections)
        # Enforce token budget (rough: 1 token ≈ 4 chars)
        while len(assembled) > max_tokens * 4 and episodic:
            episodic = episodic[:-1]
            sections[1] = f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in episodic])
            assembled = "\n\n".join(sections)
        return assembled
