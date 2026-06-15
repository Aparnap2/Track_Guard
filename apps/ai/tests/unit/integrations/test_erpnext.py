"""Unit tests for get_erpnext_snapshot() — mock mode and real mode."""
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

os.environ.pop("ERPNEXT_URL", None)

from src.integrations.erpnext import (
    get_erpnext_snapshot,
    MOCK_MODE,
    _add_metadata,
)


class TestMockMode:
    def test_mock_mode_enabled_by_default(self):
        assert MOCK_MODE is True

    def test_mock_mode_returns_valid_shape(self):
        result = get_erpnext_snapshot("test-tenant")
        assert isinstance(result, dict)
        assert result["source"] == "erpnext_mock"
        assert "fetched_at" in result

    def test_mock_mode_all_sections_present(self):
        result = get_erpnext_snapshot("test-tenant")
        assert result["support_open_issues"] == 12
        assert result["execution_active_projects"] == 4
        assert result["team_active_count"] == 18
        assert result["finance_unpaid_cents"] == 2400000


class TestRealMode:
    @patch("src.integrations.erpnext.MOCK_MODE", False)
    @patch("src.integrations.erpnext.ERPNextClient")
    def test_real_mode_creates_client(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.count.return_value = 0
        mock_client.list.return_value = []
        result = get_erpnext_snapshot("test-tenant")
        assert result["source"] == "erpnext"

    @patch("src.integrations.erpnext.MOCK_MODE", False)
    @patch("src.integrations.erpnext.ERPNextClient")
    def test_real_mode_finance_in_cents(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.count.return_value = 0
        mock_client.list.return_value = [
            {"name": "INV-001", "outstanding_amount": "100.50"},
            {"name": "INV-002", "outstanding_amount": "200.00"},
        ]
        result = get_erpnext_snapshot("test-tenant")
        assert result["finance_unpaid_cents"] == 30050


class TestErrorHandling:
    @patch("src.integrations.erpnext.MOCK_MODE", False)
    @patch("src.integrations.erpnext.ERPNextClient")
    def test_connector_failure_returns_defaults(self, mock_client_class):
        from src.integrations.erpnext import ERPNextError
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.count.side_effect = ERPNextError("Connection failed")
        mock_client.list.side_effect = ERPNextError("Connection failed")
        result = get_erpnext_snapshot("test-tenant")
        assert result["support_open_issues"] == 0
        assert result["execution_active_projects"] == 0
        assert result["finance_unpaid_cents"] == 0
