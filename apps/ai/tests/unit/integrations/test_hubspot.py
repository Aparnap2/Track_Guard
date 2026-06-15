"""Unit tests for get_hubspot_snapshot() — mock mode."""
import os
from unittest.mock import patch

HUBSPOT_MODULE = "src.integrations.hubspot"
os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)


class TestHubspotMockMode:
    def test_mock_mode_returns_mock_data(self):
        import importlib
        mod = importlib.import_module(HUBSPOT_MODULE)
        importlib.reload(mod)
        result = mod.get_hubspot_snapshot("test-tenant")
        assert result["source"] == "hubspot_mock"
        assert result["revenue_total_deals_cents"] > 0
        assert "fetched_at" in result

    def test_mock_mode_contains_all_keys(self):
        import importlib
        mod = importlib.import_module(HUBSPOT_MODULE)
        importlib.reload(mod)
        result = mod.get_hubspot_snapshot("test-tenant")
        expected = ["revenue_total_deals_cents", "revenue_won_deals_30d_cents",
                    "revenue_pipeline_deals_cents", "revenue_active_customers",
                    "revenue_mrr_cents", "source", "fetched_at"]
        for key in expected:
            assert key in result, f"Missing key: {key}"

    def test_mock_mode_values_are_ints(self):
        import importlib
        mod = importlib.import_module(HUBSPOT_MODULE)
        importlib.reload(mod)
        result = mod.get_hubspot_snapshot("test-tenant")
        for key in ["revenue_total_deals_cents", "revenue_won_deals_30d_cents",
                    "revenue_pipeline_deals_cents", "revenue_active_customers"]:
            assert isinstance(result[key], int)
