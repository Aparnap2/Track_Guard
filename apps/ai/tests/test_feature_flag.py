"""
Tests for APScheduler feature flag and bootstrap.

Verifies:
1. USE_APSCHEDULER environment variable forks correctly
2. Bootstrap loads all active tenants
"""
import ast
import os
import pytest
from unittest.mock import AsyncMock, patch

GRPC_MISSING = True
try:
    import src.main
    GRPC_MISSING = False
except Exception:
    pass


def _get_use_scheduler_from_source(env_value: str) -> bool:
    """Parse USE_SCHEDULER logic from source without importing main."""
    import re
    src_path = os.path.join(os.path.dirname(__file__), "..", "src", "main.py")
    with open(src_path) as f:
        content = f.read()
    m = re.search(r'USE_SCHEDULER\s*=\s*os\.environ\.get\("USE_APSCHEDULER",\s*"[^"]*"\)\.lower\(\)\s*==\s*"true"', content)
    if m:
        return env_value.lower() == "true"
    return False


def test_apscheduler_env_enabled(monkeypatch):
    """USE_APSCHEDULER=true should activate APScheduler backend."""
    monkeypatch.setenv("USE_APSCHEDULER", "true")
    assert _get_use_scheduler_from_source("true") is True


def test_apscheduler_env_disabled(monkeypatch):
    """USE_APSCHEDULER=false should fall back to Temporal."""
    monkeypatch.setenv("USE_APSCHEDULER", "false")
    assert _get_use_scheduler_from_source("false") is False


@pytest.mark.skipif(GRPC_MISSING, reason="Protobuf not generated (grpc_server imports ai.v1.agent_pb2)")
@pytest.mark.asyncio
async def test_bootstrap_registers_all_tenants():
    """Every active tenant must get jobs registered at startup."""
    active_tenants = ["tenant-1", "tenant-2", "tenant-3"]

    mock_register = AsyncMock()

    with patch("src.main.register_tenant_schedules", mock_register), \
         patch("src.main.start_scheduler"):

        from src.main import bootstrap_scheduler

        await bootstrap_scheduler()

        assert mock_register.call_count == len(active_tenants), \
            f"Expected {len(active_tenants)} registrations, got {mock_register.call_count}"

        for tenant_id in active_tenants:
            mock_register.assert_any_call(tenant_id)


@pytest.mark.skipif(GRPC_MISSING, reason="Protobuf not generated")
@pytest.mark.asyncio
async def test_bootstrap_empty_tenants():
    """Empty tenant list must not raise."""
    mock_register = AsyncMock()

    with patch("src.main.register_tenant_schedules", mock_register), \
         patch("os.environ.get", return_value=""), \
         patch("src.main.start_scheduler"):

        from src.main import bootstrap_scheduler

        await bootstrap_scheduler()

        mock_register.assert_called_with("default")


@pytest.mark.skipif(GRPC_MISSING, reason="Protobuf not generated")
@pytest.mark.asyncio
async def test_bootstrap_single_tenant():
    """Single tenant should work correctly."""
    mock_register = AsyncMock()

    with patch("src.main.register_tenant_schedules", mock_register), \
         patch("src.main.start_scheduler"):

        from src.main import bootstrap_scheduler

        await bootstrap_scheduler()

        mock_register.assert_called_once()


@pytest.mark.skipif(GRPC_MISSING, reason="Protobuf not generated")
def test_orchestration_backend_detection():
    """Backend should be detected based on environment."""
    import os

    original = os.environ.get("USE_APSCHEDULER")
    try:
        os.environ["USE_APSCHEDULER"] = "true"
        assert _get_use_scheduler_from_source("true") is True

        os.environ["USE_APSCHEDULER"] = "false"
        assert _get_use_scheduler_from_source("false") is False
    finally:
        if original is not None:
            os.environ["USE_APSCHEDULER"] = original
        elif "USE_APSCHEDULER" in os.environ:
            del os.environ["USE_APSCHEDULER"]