"""TDD tests for Phase 3 (Approval Gate) components.

Tests cover PlannedAction model, classify_risk policy,
execute_planned_action executor, and approval queue.
All external calls are mocked — no real network.
"""
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestPlannedAction:
    def test_auto_generates_id_and_created_at(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        assert action.id
        assert isinstance(action.id, str)
        assert len(action.id) == 36
        assert action.created_at
        assert "T" in action.created_at
        assert action.created_at.endswith("Z") or action.created_at.endswith("+00:00")

    def test_default_values(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        assert action.risk_level == "low"
        assert action.requires_approval is False
        assert action.status == "planned"

    def test_accepts_post_slack_message(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="bob", action_type="post_slack_message")
        assert action.action_type == "post_slack_message"

    def test_accepts_create_erpnext_issue(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="bob", action_type="create_erpnext_issue")
        assert action.action_type == "create_erpnext_issue"

    def test_accepts_update_hubspot_deal(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="bob", action_type="update_hubspot_deal")
        assert action.action_type == "update_hubspot_deal"

    def test_accepts_send_investor_update(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="bob", action_type="send_investor_update")
        assert action.action_type == "send_investor_update"

    def test_accepts_write_quickbooks_note(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="bob", action_type="write_quickbooks_note")
        assert action.action_type == "write_quickbooks_note"

    def test_invalid_action_type_raises_validation_error(self):
        from src.orchestrators.planned_action import PlannedAction
        with pytest.raises(ValidationError):
            PlannedAction(tenant_id="t1", actor="bob", action_type="send_email")

    def test_executed_at_is_none_by_default(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        assert action.executed_at is None

    def test_executed_at_can_be_set_explicitly(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        action.executed_at = "2026-06-22T12:00:00Z"
        assert action.executed_at == "2026-06-22T12:00:00Z"

    def test_error_defaults_to_none(self):
        from src.orchestrators.planned_action import PlannedAction
        action = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        assert action.error is None


class TestClassifyRisk:
    def test_post_slack_message_returns_low_no_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message")
        assert risk == "low"
        assert requires is False
        assert reason is None

    def test_create_erpnext_issue_returns_medium_and_requires_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("create_erpnext_issue")
        assert risk == "medium"
        assert requires is True
        assert reason == "Creates a record in ERPNext helpdesk"

    def test_update_hubspot_deal_returns_high_and_requires_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("update_hubspot_deal")
        assert risk == "high"
        assert requires is True
        assert reason == "Modifies CRM deal data in HubSpot"

    def test_send_investor_update_returns_high_and_requires_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("send_investor_update")
        assert risk == "high"
        assert requires is True
        assert reason == "Sends external communication to investors"

    def test_write_quickbooks_note_returns_medium_and_requires_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("write_quickbooks_note")
        assert risk == "medium"
        assert requires is True
        assert reason == "Writes a note to QuickBooks accounting"

    def test_unknown_action_type_returns_high_with_message(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("send_email")
        assert risk == "high"
        assert requires is True
        assert reason == "Unknown action type: send_email"

    def test_delete_action_unknown_type_returns_high(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("delete_user_record")
        assert risk == "high"
        assert requires is True
        assert "Unknown action type" in reason

    def test_remove_action_unknown_type_returns_high(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("remove_old_data")
        assert risk == "high"
        assert requires is True
        assert "Unknown action type" in reason

    def test_monetary_amount_over_one_million_bumps_low_to_medium(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", {"monetary_amount": 2000000})
        assert risk == "medium"

    def test_monetary_amount_over_one_million_bumps_medium_to_high(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("write_quickbooks_note", {"monetary_amount": 2000000})
        assert risk == "high"

    def test_monetary_amount_over_one_million_high_stays_high(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("update_hubspot_deal", {"monetary_amount": 5000000})
        assert risk == "high"

    def test_monetary_amount_under_one_million_does_not_change_risk(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", {"monetary_amount": 500})
        assert risk == "low"

    def test_none_params_handled_gracefully(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", None)
        assert risk == "low"
        assert requires is False
        assert reason is None

    def test_params_not_provided_uses_empty_dict(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message")
        assert risk == "low"

    def test_invalid_monetary_amount_does_not_crash(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", {"monetary_amount": "not-a-number"})
        assert risk == "low"

    def test_monetary_amount_zero_does_not_change_risk(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("write_quickbooks_note", {"monetary_amount": 0})
        assert risk == "medium"

    def test_monetary_amount_exactly_one_million_does_not_bump(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", {"monetary_amount": 1000000})
        assert risk == "low"

    def test_low_risk_with_monetary_bump_sets_requires_approval(self):
        from src.orchestrators.approval_policy import classify_risk
        risk, requires, reason = classify_risk("post_slack_message", {"monetary_amount": 5000000})
        assert risk == "medium"
        assert requires is True
        assert "medium risk" in reason


class TestExecutePlannedAction:
    def test_slack_message_success(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
            params={"text": "Hello", "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]},
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            result = execute_planned_action(action)

        assert result["ok"] is True

    def test_erpnext_issue_success(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="create_erpnext_issue",
            params={"subject": "Test issue", "description": "Testing"},
        )
        with patch("src.integrations.erpnext_client.ERPNextClient._request") as mock_request:
            mock_request.return_value = {"name": "ISS-001", "status": "Open"}
            result = execute_planned_action(action)

        assert result["ok"] is True
        assert result["result"]["name"] == "ISS-001"

    def test_hubspot_deal_sdk_not_installed(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="update_hubspot_deal",
            params={"deal_id": "12345"},
        )
        with patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "some-token"}, clear=False):
            with patch.dict("sys.modules", {"hubspot": None}):
                result = execute_planned_action(action)

        assert result["ok"] is False
        assert "SDK not installed" in result["error"]

    def test_hubspot_deal_mock_mode_when_no_token(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="update_hubspot_deal",
        )
        with patch.dict(os.environ, {}, clear=True):
            result = execute_planned_action(action)

        assert result["ok"] is True
        assert result["result"]["mock"] is True

    def test_investor_update_sends_message(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="send_investor_update",
            params={"text": "Quarterly update", "full_draft": "Full report here"},
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            result = execute_planned_action(action)

        assert result["ok"] is True

    def test_investor_update_passes_full_draft(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="send_investor_update",
            params={"text": "Quarterly update", "full_draft": "Full report here"},
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            execute_planned_action(action)
            mock_send.assert_called_once_with(text="Quarterly update", full_draft="Full report here")

    def test_quickbooks_mock_mode_when_no_env(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="write_quickbooks_note",
            params={"note": "Test entry"},
        )
        with patch.dict(os.environ, {}, clear=True):
            result = execute_planned_action(action)

        assert result["ok"] is True
        assert result["result"]["mock"] is True
        assert "QuickBooks mock note" in result["result"]["message"]

    def test_unknown_action_type_returns_error(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
        )
        action.action_type = "send_email"
        result = execute_planned_action(action)

        assert result["ok"] is False
        assert "Unknown action_type" in result["error"]

    def test_exception_is_caught(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
        )
        with patch("src.integrations.slack.send_message_sync", side_effect=RuntimeError("boom")):
            result = execute_planned_action(action)

        assert result["ok"] is False
        assert "boom" in result["error"]

    def test_execute_slack_message_passes_text_and_blocks(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Block content"}}]
        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
            params={"text": "Hello world", "blocks": blocks},
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            execute_planned_action(action)
            mock_send.assert_called_once_with(text="Hello world", blocks=blocks)

    def test_execute_erpnext_issue_passes_priority(self):
        from src.orchestrators.action_executor import execute_planned_action
        from src.orchestrators.planned_action import PlannedAction

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="create_erpnext_issue",
            params={"subject": "Bug", "description": "Fix me", "priority": "High"},
        )
        with patch("src.integrations.erpnext_client.ERPNextClient._request") as mock_request:
            mock_request.return_value = {"name": "ISS-002"}
            result = execute_planned_action(action)

        assert result["ok"] is True
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/api/resource/Issue"
        assert call_args[1]["body"]["priority"] == "High"


class TestApprovalQueue:
    @pytest.fixture(autouse=True)
    def _clear_pending(self):
        import src.hitl.approval_queue as aq
        aq._pending_approvals.clear()

    def test_request_approval_stores_action_and_sends(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
            risk_level="high", requires_approval=True,
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            result = request_approval(action)

        assert result["ok"] is True
        assert result["action"]["id"] == action.id
        assert result["action"]["status"] == "planned"
        mock_send.assert_called_once()

    def test_handle_approval_approved_sets_status(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval, handle_approval_response

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action)

        result = handle_approval_response(action.id, approved=True)
        assert result["ok"] is True
        assert result["action"]["status"] == "approved"
        assert result["action"]["executed_at"] is not None

    def test_handle_approval_rejected_sets_status(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval, handle_approval_response

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="post_slack_message",
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action)

        result = handle_approval_response(action.id, approved=False)
        assert result["ok"] is True
        assert result["action"]["status"] == "rejected"
        assert result["action"].get("executed_at") is None

    def test_handle_approval_unknown_id_returns_not_found(self):
        from src.hitl.approval_queue import handle_approval_response

        result = handle_approval_response("nonexistent-id", approved=True)
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_get_pending_approvals_returns_all_when_no_filter(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval, get_pending_approvals

        action_a = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        action_b = PlannedAction(tenant_id="t2", actor="bob", action_type="post_slack_message")
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action_a)
            request_approval(action_b)

        pending = get_pending_approvals()
        assert len(pending) == 2

    def test_get_pending_approvals_filters_by_tenant(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval, get_pending_approvals

        action_a = PlannedAction(tenant_id="t1", actor="alice", action_type="post_slack_message")
        action_b = PlannedAction(tenant_id="t2", actor="bob", action_type="post_slack_message")
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action_a)
            request_approval(action_b)

        pending = get_pending_approvals(tenant_id="t1")
        assert len(pending) == 1
        assert pending[0]["tenant_id"] == "t1"

    def test_request_approval_blocks_contain_approve_reject_buttons(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="update_hubspot_deal",
            risk_level="high", requires_approval=True,
            approval_reason="Modifies CRM deal data",
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action)

        call_kwargs = mock_send.call_args[1]
        blocks = call_kwargs["blocks"]
        action_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(action_blocks) > 0
        elements = action_blocks[0]["elements"]
        button_texts = [e["text"]["text"] for e in elements if e.get("type") == "button"]
        assert "Approve" in button_texts
        assert "Reject" in button_texts

    def test_request_approval_sends_with_correct_text(self):
        from src.orchestrators.planned_action import PlannedAction
        from src.hitl.approval_queue import request_approval

        action = PlannedAction(
            tenant_id="t1", actor="alice", action_type="update_hubspot_deal",
            risk_level="high", requires_approval=True,
        )
        with patch("src.integrations.slack.send_message_sync") as mock_send:
            mock_send.return_value = {"ok": True, "channel": "slack"}
            request_approval(action)

        call_kwargs = mock_send.call_args[1]
        text = call_kwargs.get("text", "")
        assert "[Approval Required]" in text
        assert action.action_type in text
        assert action.actor in text
