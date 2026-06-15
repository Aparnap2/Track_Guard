"""End-to-end integration test for Startup Guardian.
Requires: mockoon containers running (docker-compose.startup-guardian.yml).
"""
import os
import pytest

_skip = pytest.mark.skipif(
    not os.getenv("ERPNEXT_URL", "").startswith("http://"),
    reason="Requires mockoon containers: ERPNEXT_URL not set"
)


@_skip
@pytest.mark.asyncio
async def test_full_pipeline():
    from src.orchestration.run_startup_guardian import run_startup_guardian
    result = await run_startup_guardian("e2e-test-tenant")
    assert result["tenant_id"] == "e2e-test-tenant"
    assert result["run_id"] != ""
    assert result["support"]["open_issues"] >= 0
    assert result["execution"]["active_projects"] >= 0
    assert result["team"]["active_employees"] >= 0
    assert result["finance"]["total_outstanding_cents"] >= 0
    assert result["connectors_ok"]["erpnext"] is True


@_skip
@pytest.mark.asyncio
async def test_overall_health_present():
    from src.orchestration.run_startup_guardian import run_startup_guardian
    result = await run_startup_guardian("e2e-test-tenant")
    assert result["overall_health"] in ("good", "attention", "critical")
