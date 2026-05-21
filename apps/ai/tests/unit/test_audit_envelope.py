from datetime import datetime
import pytest
from src.services.audit_envelope import AlertEvidenceChain, AuditEnvelopeService


class TestAlertEvidenceChain:
    def test_evidence_chain_has_all_fields(self):
        chain = AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-123",
            trace_id="trace-abc",
            workflow_run_id="workflow-xyz",
            mission_state_snapshot_id="mission-001",
            retrieval_ids=["ret-1", "ret-2"],
            numbers_injected=["num-1"],
            rule_anomalies=["anomaly-1"],
            llm_model="qwen3-next:80b-cloud",
            schema_version="guardian.v1",
            strategy_id="strategy-001",
            confidence=0.95,
            created_at=datetime(2026, 5, 12, 10, 30, 0)
        )

        assert chain.alert_id == "alert-001"
        assert chain.tenant_id == "tenant-123"
        assert chain.trace_id == "trace-abc"
        assert chain.workflow_run_id == "workflow-xyz"
        assert chain.mission_state_snapshot_id == "mission-001"
        assert chain.retrieval_ids == ["ret-1", "ret-2"]
        assert chain.numbers_injected == ["num-1"]
        assert chain.rule_anomalies == ["anomaly-1"]
        assert chain.llm_model == "qwen3-next:80b-cloud"
        assert chain.schema_version == "guardian.v1"
        assert chain.strategy_id == "strategy-001"
        assert chain.confidence == 0.95
        assert chain.created_at == datetime(2026, 5, 12, 10, 30, 0)


class TestAuditEnvelopeService:
    def setup_method(self):
        self.service = AuditEnvelopeService()

    def test_log_evidence_chain_creates_id(self):
        evidence = AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-123",
            trace_id="trace-abc",
            workflow_run_id="workflow-xyz",
            mission_state_snapshot_id="mission-001"
        )

        chain_id = self.service.log_evidence_chain(evidence)

        assert chain_id is not None
        assert isinstance(chain_id, str)
        assert len(chain_id) > 0

    def test_get_evidence_chain_retrieves(self):
        evidence = AlertEvidenceChain(
            alert_id="alert-002",
            tenant_id="tenant-456",
            trace_id="trace-def",
            workflow_run_id="workflow-uvw",
            mission_state_snapshot_id="mission-002"
        )

        chain_id = self.service.log_evidence_chain(evidence)
        retrieved = self.service.get_evidence_chain(chain_id)

        assert retrieved is not None
        assert retrieved.alert_id == "alert-002"
        assert retrieved.tenant_id == "tenant-456"

    def test_search_evidence_by_tenant(self):
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-A",
            trace_id="trace-1",
            workflow_run_id="wf-1",
            mission_state_snapshot_id="ms-1"
        ))
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-002",
            tenant_id="tenant-A",
            trace_id="trace-2",
            workflow_run_id="wf-2",
            mission_state_snapshot_id="ms-2"
        ))
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-003",
            tenant_id="tenant-B",
            trace_id="trace-3",
            workflow_run_id="wf-3",
            mission_state_snapshot_id="ms-3"
        ))

        results = self.service.search_evidence(tenant_id="tenant-A")

        assert len(results) == 2
        for r in results:
            assert r.tenant_id == "tenant-A"

    def test_search_evidence_by_alert_id(self):
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-specific",
            tenant_id="tenant-X",
            trace_id="trace-1",
            workflow_run_id="wf-1",
            mission_state_snapshot_id="ms-1"
        ))
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-other",
            tenant_id="tenant-X",
            trace_id="trace-2",
            workflow_run_id="wf-2",
            mission_state_snapshot_id="ms-2"
        ))

        results = self.service.search_evidence(tenant_id="tenant-X", alert_id="alert-specific")

        assert len(results) == 1
        assert results[0].alert_id == "alert-specific"

    def test_audit_summary_counts(self):
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-001",
            tenant_id="tenant-summary",
            trace_id="trace-1",
            workflow_run_id="wf-1",
            mission_state_snapshot_id="ms-1",
            confidence=0.8
        ))
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-002",
            tenant_id="tenant-summary",
            trace_id="trace-2",
            workflow_run_id="wf-2",
            mission_state_snapshot_id="ms-2",
            confidence=0.9
        ))
        self.service.log_evidence_chain(AlertEvidenceChain(
            alert_id="alert-003",
            tenant_id="tenant-summary",
            trace_id="trace-3",
            workflow_run_id="wf-3",
            mission_state_snapshot_id="ms-3",
            confidence=0.7
        ))

        summary = self.service.get_audit_summary(tenant_id="tenant-summary")

        assert summary["count"] == 3
        assert summary["avg_confidence"] == pytest.approx(0.8, rel=0.01)
        assert summary["latest"] is not None

    def test_get_evidence_chain_not_found(self):
        result = self.service.get_evidence_chain("non-existent-id")
        assert result is None

    def test_search_evidence_no_results(self):
        results = self.service.search_evidence(tenant_id="non-existent-tenant")
        assert results == []