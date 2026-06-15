"""Unit tests for get_quickbooks_snapshot() — mock mode."""
import os

QB_MODULE = "src.integrations.quickbooks"
os.environ.pop("QUICKBOOKS_CLIENT_ID", None)


class TestQuickBooksMockMode:
    def test_mock_mode_returns_mock_data(self):
        import importlib
        mod = importlib.import_module(QB_MODULE)
        importlib.reload(mod)
        result = mod.get_quickbooks_snapshot("test-tenant")
        assert result["source"] == "quickbooks_mock"
        assert "fetched_at" in result

    def test_mock_mode_contains_finance_keys(self):
        import importlib
        mod = importlib.import_module(QB_MODULE)
        importlib.reload(mod)
        result = mod.get_quickbooks_snapshot("test-tenant")
        expected = ["finance_outstanding_invoices", "finance_total_outstanding_cents",
                    "finance_overdue_invoices", "finance_total_overdue_cents"]
        for key in expected:
            assert key in result, f"Missing key: {key}"

    def test_mock_mode_values_are_cents(self):
        import importlib
        mod = importlib.import_module(QB_MODULE)
        importlib.reload(mod)
        result = mod.get_quickbooks_snapshot("test-tenant")
        assert isinstance(result["finance_total_outstanding_cents"], int)
        assert result["finance_total_outstanding_cents"] == 2850000
