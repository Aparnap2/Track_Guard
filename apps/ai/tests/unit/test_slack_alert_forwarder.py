from unittest.mock import MagicMock, patch

import pytest

from src.states.schemas import MissionStateV2, SupportHealth


class TestSlackAlertForwarder:
    def test_forward_skips_good_health(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.GOOD)
        result = fwd.forward_mission_alert(state)
        assert result["skipped"] is True
        assert result["reason"] == "health not critical or attention"

    def test_forward_skips_duplicate(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        store = MagicMock()
        store.exists.return_value = True
        fwd = SlackAlertForwarder(store=store)
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.CRITICAL)
        result = fwd.forward_mission_alert(state)
        assert result["skipped"] is True
        assert result["reason"] == "duplicate"

    def test_forward_delivers_critical(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        store = MagicMock()
        store.exists.return_value = False
        fwd = SlackAlertForwarder(store=store)

        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-abc-123",
            overall_health=SupportHealth.CRITICAL,
        )

        with patch.object(fwd, "_deliver", return_value={"ok": True, "channel": "slack"}) as mock_deliver:
            result = fwd.forward_mission_alert(state)

        assert result["ok"] is True
        assert result.get("skipped") is not True
        mock_deliver.assert_called_once()
        store.set.assert_called_once_with(
            "alert:sent:t1:critical", "critical", ttl=3600
        )

    def test_forward_delivers_attention(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        store = MagicMock()
        store.exists.return_value = False
        fwd = SlackAlertForwarder(store=store)

        state = MissionStateV2(
            tenant_id="t2",
            run_id="run-xyz-456",
            overall_health=SupportHealth.ATTENTION,
        )

        with patch.object(fwd, "_deliver", return_value={"ok": True, "channel": "slack"}) as mock_deliver:
            result = fwd.forward_mission_alert(state)

        assert result["ok"] is True
        mock_deliver.assert_called_once()
        store.set.assert_called_once_with(
            "alert:sent:t2:attention", "attention", ttl=3600
        )

    def test_forward_stores_on_failure(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        store = MagicMock()
        store.exists.return_value = False
        fwd = SlackAlertForwarder(store=store)

        state = MissionStateV2(
            tenant_id="t3",
            run_id="run-fail",
            overall_health=SupportHealth.CRITICAL,
        )

        with patch.object(fwd, "_deliver", return_value={"ok": False, "error": "nope"}):
            result = fwd.forward_mission_alert(state)

        assert result["ok"] is False
        store.set.assert_not_called()

    def test_format_text_critical(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.CRITICAL,
        )
        text = fwd._format_text(state)
        assert "CRITICAL" in text
        assert "t1" in text
        assert "run-1" in text

    def test_format_text_attention(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.ATTENTION,
        )
        text = fwd._format_text(state)
        assert "ATTENTION" in text

    def test_format_text_good(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.GOOD,
        )
        text = fwd._format_text(state)
        assert "GOOD" in text

    def test_format_blocks_returns_valid_structure(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.CRITICAL,
        )
        blocks = fwd._format_blocks(state)
        assert isinstance(blocks, list)
        assert len(blocks) >= 2
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"

    def test_format_blocks_includes_context_footer(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.CRITICAL,
        )
        blocks = fwd._format_blocks(state)
        last = blocks[-1]
        assert last["type"] == "context"
        assert "run-1" in last["elements"][0]["text"]

    def test_format_blocks_includes_failed_connectors(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.CRITICAL,
            connectors_ok={"erpnext": True, "hubspot": False, "quickbooks": True},
        )
        blocks = fwd._format_blocks(state)
        block_texts = [str(b) for b in blocks]
        assert any("hubspot" in t for t in block_texts)

    def test_dedup_key_format(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.CRITICAL)
        key = fwd._dedup_key(state)
        assert key == "alert:sent:t1:critical"

    def test_dedup_key_attention(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.ATTENTION)
        key = fwd._dedup_key(state)
        assert key == "alert:sent:t1:attention"

    def test_deliver_calls_send_message_sync(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        with patch("src.integrations.slack.send_message_sync", return_value={"ok": True}) as mock:
            result = fwd._deliver(text="hello", blocks=[{"type": "section"}])

        assert result["ok"] is True
        mock.assert_called_once_with(text="hello", blocks=[{"type": "section"}])

    def test_deliver_without_blocks(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        with patch("src.integrations.slack.send_message_sync", return_value={"ok": True}) as mock:
            result = fwd._deliver(text="hello")

        assert result["ok"] is True
        mock.assert_called_once_with(text="hello", blocks=None)

    def test_calls_deliver_with_formatted_content(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        store = MagicMock()
        store.exists.return_value = False
        fwd = SlackAlertForwarder(store=store)

        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-fmt",
            overall_health=SupportHealth.CRITICAL,
        )

        with patch.object(fwd, "_deliver") as mock_deliver:
            mock_deliver.return_value = {"ok": True, "channel": "slack"}
            fwd.forward_mission_alert(state)

        args, kwargs = mock_deliver.call_args
        assert "CRITICAL" in kwargs.get("text", args[0] if args else "")
        assert kwargs.get("blocks") is not None
        assert len(kwargs["blocks"]) >= 2

    def test_domain_health_in_text(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        from src.states.schemas import SupportState, SupportHealth as SH

        state = MissionStateV2(
            tenant_id="t1",
            run_id="run-1",
            overall_health=SupportHealth.CRITICAL,
            support=SupportState(open_issues=5, health=SH.CRITICAL),
        )
        text = fwd._format_text(state)
        assert "Support" in text
        assert "critical" in text.lower()

    def test_forwarder_defaults_to_production_store(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder()
        assert fwd.store is not None
        assert fwd.store._prefix == "alert"

    def test_should_alert_critical(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.CRITICAL)
        assert fwd._should_alert(state) is True

    def test_should_alert_attention(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.ATTENTION)
        assert fwd._should_alert(state) is True

    def test_should_alert_good_is_false(self):
        from src.notifications.slack_alert_forwarder import SlackAlertForwarder

        fwd = SlackAlertForwarder(store=MagicMock())
        state = MissionStateV2(tenant_id="t1", overall_health=SupportHealth.GOOD)
        assert fwd._should_alert(state) is False
