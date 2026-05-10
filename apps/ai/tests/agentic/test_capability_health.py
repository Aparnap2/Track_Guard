"""
Layer 3 - Agentic Test: Capability Registry Health Checks

Every capability must be healthy before the router invokes it.
This tests the control plane layer.
"""
import pytest


CAPABILITIES = [
    "finance.runway_risk",
    "bi.cohort_retention",
    "ops.error_correlation",
    "memory.similar_alerts",
    "graphiti.strategy_lookup",
    "service.api-gateway",
    "service.workflow",
]


@pytest.mark.agentic
@pytest.mark.parametrize("capability", CAPABILITIES)
def test_capability_registered_and_healthy(capability):
    """Every capability in the registry must be healthy."""
    import sys
    sys.path.insert(0, "src")

    from src.registry import CapabilityRegistry

    reg = CapabilityRegistry()
    reg._load_defaults()

    cap = reg.get(capability)
    assert cap is not None, f"{capability} not registered"

    # Health check
    health = reg.health_check(capability)
    assert health in ("ok", "degraded"), f"{capability} is down: {health}"

    # Policy checks
    assert cap.policy.tenant_scoped is True, f"{capability} missing tenant isolation"
    assert cap.policy.fallback is not None, f"{capability} missing fallback"


@pytest.mark.agentic
def test_capability_domain_filtering():
    """Verify domain filtering works."""
    import sys
    sys.path.insert(0, "src")

    from src.registry import CapabilityRegistry

    reg = CapabilityRegistry()
    reg._load_defaults()

    finance_caps = reg.find_by_domain("finance")
    assert len(finance_caps) > 0, "No finance capabilities found"

    # Verify all have finance tag
    for cap in finance_caps:
        assert "finance" in cap.policy.tags, f"{cap.capability} missing finance tag"


@pytest.mark.agentic
def test_capability_policy_metadata():
    """Verify policy metadata is correct."""
    import sys
    sys.path.insert(0, "src")

    from src.registry import CapabilityRegistry

    reg = CapabilityRegistry()
    reg._load_defaults()

    cap = reg.get("finance.runway_risk")
    assert cap.policy.pii_class == "restricted", "Finance should be restricted PII"
    assert cap.policy.latency_slo_ms == 1500, "Finance should have 1500ms SLA"
    assert cap.policy.fallback == "return_no_alert", "Finance should fallback to no alert"

    cap = reg.get("memory.similar_alerts")
    assert cap.policy.latency_slo_ms == 500, "Memory should be fast (<500ms)"