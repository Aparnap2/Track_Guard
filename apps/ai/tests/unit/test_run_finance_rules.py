"""Tests for run_finance_rules activity — TDD Red phase.

Tests cover:
- Basic success path (ok=True, tenant_id matching)
- FinancialSnapshot field coverage
- Triggered detection rules
- MBA primitive computation
- Edge cases: empty signals, missing keys, invalid inputs
- Multiple simultaneous rule triggers
"""
import pytest


class TestRunFinanceRules:
    """Tests for run_finance_rules activity."""

    # ── Basic success path ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_returns_dict_with_ok(self):
        """Activity returns dict with ok=True on success."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test-tenant", {"mrr_cents": 100000})
        assert result["ok"] is True
        assert result["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_returns_snapshot_with_all_fields(self):
        """Returns FinancialSnapshot-compatible dict."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"mrr_cents": 200000, "burn_30d_cents": 50000})
        snapshot = result["snapshot"]
        assert "mrr" in snapshot
        assert "burn_rate" in snapshot
        assert "runway_days" in snapshot
        assert "burn_multiple" in snapshot
        assert "triggered_rules" in result

    # ── Detection rule triggering ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_triggered_rules_empty_on_healthy(self):
        """No rules triggered on healthy signals."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"monthly_churn_pct": 0.01, "burn_30d_cents": 100})
        assert result["triggered_rules"] == []

    @pytest.mark.asyncio
    async def test_triggered_churn_when_above_3pct(self):
        """is_silent_churn_death triggered when churn > 3%."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"monthly_churn_pct": 0.05})
        assert "is_silent_churn_death" in result["triggered_rules"]

    @pytest.mark.asyncio
    async def test_triggered_burn_multiple_when_above_2x(self):
        """is_burn_multiple_creep triggered when burn_multiple > 2x."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"net_burn": 50000, "net_new_arr": 10000})
        assert "is_burn_multiple_creep" in result["triggered_rules"]

    # ── MBA primitive computation ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_runway_days_computed(self):
        """runway_days computed from runway_months * 30."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"burn_30d_cents": 50000, "runway_months": 12})
        snapshot = result["snapshot"]
        assert snapshot["runway_days"] == 360  # 12 * 30

    @pytest.mark.asyncio
    async def test_burn_multiple_computed(self):
        """burn_multiple computed from net_burn and net_new_arr."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {"net_burn": 100000, "net_new_arr": 50000})
        assert result["snapshot"]["burn_multiple"] == 2.0

    # ── Edge cases ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_handles_missing_signals_gracefully(self):
        """Missing signals use safe defaults (no KeyError)."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {})
        assert result["ok"] is True
        assert result["triggered_rules"] == []

    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_input(self):
        """Returns ok=False for invalid inputs instead of raising."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("", {})
        assert result["ok"] is False

    # ── Complex scenarios ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_computes_multiple_rules_on_complex_signals(self):
        """Multiple rules can trigger simultaneously."""
        from src.activities.run_finance_rules import run_finance_rules

        result = await run_finance_rules("test", {
            "monthly_churn_pct": 0.05,
            "net_burn": 100000,
            "net_new_arr": 10000,
            "burn_30d_cents": 100000,
            "prev_burn_cents": 50000,
            "runway_months": 6,
        })
        assert len(result["triggered_rules"]) >= 2
        assert "is_silent_churn_death" in result["triggered_rules"]
