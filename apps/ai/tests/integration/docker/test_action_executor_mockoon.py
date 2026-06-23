"""Integration tests for action_executor with real Mockoon containers.

Tests verify Mockoon health endpoints, data queries, and action executor
dispatch (mocked external calls, mock mode, error handling).

Requires: sg-mock-erpnext (:8099), sg-mock-hubspot (:8098),
          sg-mock-quickbooks (:8097)
Run: uv run pytest tests/integration/docker/test_action_executor_mockoon.py -v --timeout=15
"""
from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest


ERPENXT_BASE = "http://localhost:8099"
HUBSPOT_BASE = "http://localhost:8098"
QUICKBOOKS_BASE = "http://localhost:8097"


class TestActionExecutorMockoon:
    """Combined Mockoon endpoint health checks and action executor tests."""

    @pytest.fixture(autouse=True)
    def _client(self) -> None:
        self._http = httpx.Client(timeout=10.0)

    def teardown_method(self) -> None:
        self._http.close()

    def _make_action(
        self,
        action_type: str = "post_slack_message",
        params: dict | None = None,
        **overrides: object,
    ) -> object:
        from src.orchestrators.planned_action import PlannedAction

        return PlannedAction(
            tenant_id=overrides.get("tenant_id", "test"),
            actor=overrides.get("actor", "test"),
            action_type=action_type,  # type: ignore[arg-type]
            params=params or {},
            risk_level=overrides.get("risk_level", "low"),  # type: ignore[arg-type]
        )

    def test_erpnext_mockoon_health(self) -> None:
        """ERPNext Mockoon /health returns 200 with status ok."""
        resp = self._http.get(f"{ERPENXT_BASE}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_hubspot_mockoon_health(self) -> None:
        """HubSpot Mockoon /health returns 200."""
        resp = self._http.get(f"{HUBSPOT_BASE}/health")
        assert resp.status_code == 200

    def test_quickbooks_mockoon_health(self) -> None:
        """QuickBooks Mockoon /health returns 200."""
        resp = self._http.get(f"{QUICKBOOKS_BASE}/health")
        assert resp.status_code == 200

    def test_erpnext_get_issues(self) -> None:
        """ERPNext frappe.client.get_list returns a list with items."""
        resp = self._http.get(
            f"{ERPENXT_BASE}/api/method/frappe.client.get_list",
            params={"doctype": "Issue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        issues = data["message"]
        assert isinstance(issues, list)
        assert len(issues) > 0

    def test_hubspot_get_deals(self) -> None:
        """HubSpot /crm/v3/objects/deals returns results with 3 deals."""
        resp = self._http.get(f"{HUBSPOT_BASE}/crm/v3/objects/deals")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_quickbooks_get_invoices(self) -> None:
        """QuickBooks /v3/company/{id}/query returns QueryResponse with Invoice list."""
        resp = self._http.get(
            f"{QUICKBOOKS_BASE}/v3/company/123146573628384/query"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "QueryResponse" in data
        assert "Invoice" in data["QueryResponse"]
        assert isinstance(data["QueryResponse"]["Invoice"], list)

    def test_execute_unknown_action_type(self) -> None:
        """Unknown action_type returns ok=False with error message."""
        from src.orchestrators.action_executor import execute_planned_action

        action = self._make_action(action_type="post_slack_message")
        action.action_type = "send_email"  # type: ignore[assignment]

        result = execute_planned_action(action)
        assert result["ok"] is False
        assert "Unknown action_type" in result["error"]

    def test_execute_hubspot_mock_mode(self) -> None:
        """HubSpot mock mode returns ok=True with mock result when token empty."""
        from src.orchestrators.action_executor import execute_planned_action

        action = self._make_action(
            action_type="update_hubspot_deal",
            params={"deal_id": "12345", "properties": {"dealstage": "closedwon"}},
        )

        with patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": ""}, clear=False):
            result = execute_planned_action(action)

        assert result["ok"] is True
        assert result["result"]["mock"] is True

    def test_execute_quickbooks_mock_mode(self) -> None:
        """QuickBooks mock mode returns ok=True with mock result when client id empty."""
        from src.orchestrators.action_executor import execute_planned_action

        action = self._make_action(
            action_type="write_quickbooks_note",
            params={"note": "test"},
        )

        with patch.dict(os.environ, {"QUICKBOOKS_CLIENT_ID": ""}, clear=False):
            result = execute_planned_action(action)

        assert result["ok"] is True
        assert result["result"]["mock"] is True

    def test_execute_slack_mocked(self) -> None:
        """post_slack_message with mocked send_message_sync returns ok=True."""
        from src.orchestrators.action_executor import execute_planned_action

        action = self._make_action(
            action_type="post_slack_message",
            params={"text": "Hello"},
        )

        with patch("src.integrations.slack.send_message_sync") as mock_slack:
            mock_slack.return_value = {"ok": True, "channel": "slack"}
            result = execute_planned_action(action)

        assert result["ok"] is True
