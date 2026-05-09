"""
CommsTriageState — state object for the CommsTriageAgent.

Triage agent for Slack communications - classifies and prioritizes
messages from various Slack channels for the founder.
"""
from __future__ import annotations
from typing import TypedDict


class CommsTriageState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────
    tenant_id:           str

    # ── Input ─────────────────────────────────────────────────────
    channels:            list[str]          # Slack channels to triage
    messages:            list[dict]         # Raw messages from channels

    # ── Classification results ────────────────────────────────────
    classified_messages: list[dict]         # Messages with classification
    urgent_messages:     list[dict]         # High priority messages
    action_items:        list[dict]         # Messages requiring action

    # ── Digest output ─────────────────────────────────────────────
    digest:              str                # Generated digest text
    slack_blocks:        list[dict]         # Slack Block Kit message

    # ── Metadata ──────────────────────────────────────────────────
    data_sources:        list[str]
    error:               str
    error_node:          str