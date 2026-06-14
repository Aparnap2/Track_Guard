import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AlertEvidenceChain:
    alert_id: str
    tenant_id: str
    trace_id: str
    workflow_run_id: str
    mission_state_snapshot_id: str
    retrieval_ids: list[str] = field(default_factory=list)
    numbers_injected: list[str] = field(default_factory=list)
    rule_anomalies: list[str] = field(default_factory=list)
    llm_model: str = "qwen3-next:80b-cloud"
    schema_version: str = "guardian.v1"
    strategy_id: str = ""
    confidence: float = 0.0
    created_at: datetime | None = None
    trust_score: float = 0.0
    routing_priority: int = 999
    trust_reason: str = ""


class AuditEnvelopeService:
    def __init__(self):
        self._chains: dict[str, AlertEvidenceChain] = {}

    def log_evidence_chain(self, evidence: AlertEvidenceChain) -> str:
        chain_id = str(uuid.uuid4())
        if evidence.created_at is None:
            evidence.created_at = datetime.now(timezone.utc)
        self._chains[chain_id] = evidence
        return chain_id

    def get_evidence_chain(self, chain_id: str) -> Optional[AlertEvidenceChain]:
        return self._chains.get(chain_id)

    def search_evidence(
        self, tenant_id: str, alert_id: Optional[str] = None
    ) -> list[AlertEvidenceChain]:
        results = []
        for chain in self._chains.values():
            if chain.tenant_id != tenant_id:
                continue
            if alert_id is not None and chain.alert_id != alert_id:
                continue
            results.append(chain)
        return results

    def get_audit_summary(self, tenant_id: str) -> dict:
        chains = self.search_evidence(tenant_id=tenant_id)
        if not chains:
            return {"count": 0, "avg_confidence": 0.0, "latest": None}

        total_confidence = sum(c.confidence for c in chains)
        avg_confidence = total_confidence / len(chains)

        latest = max(chains, key=lambda c: c.created_at or datetime.min)

        return {
            "count": len(chains),
            "avg_confidence": avg_confidence,
            "latest": latest.alert_id
        }