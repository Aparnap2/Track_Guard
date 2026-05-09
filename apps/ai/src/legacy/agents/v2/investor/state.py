"""
InvestorState — state object for the InvestorAgent.

The InvestorAgent runs weekly (Monday 8am) to generate structured
investor update drafts in Markdown format.
"""
from __future__ import annotations
from typing import Optional, TypedDict


class InvestorState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────
    tenant_id:           str

    # ── Time period ───────────────────────────────────────────────
    period_start:        str            # ISO date (e.g. "2026-03-18")
    period_end:          str            # ISO date (e.g. "2026-03-25")

    # ── Metrics from PulseAgent / database ───────────────────────
    mrr_cents:           int
    mrr_growth_pct:      float
    burn_cents:          int
    runway_months:       float
    new_customers:       int
    churned_customers:   int
    active_customers:    int

    # ── Historical context from Qdrant ────────────────────────────
    top_wins:            list[str]      # wins from memory
    top_blockers:        list[str]      # blockers from memory
    historical_context:  str            # prose summary

    # ── DSPy-generated outputs ────────────────────────────────────
    draft_markdown:      str            # full investor update draft (<300 words)
    slack_preview:       str            # short preview for Slack

    # ── Critic loop ───────────────────────────────────────────────
    critique:            str            # critique verdict (PASS/FAIL + feedback)
    quality_pass:        bool           # whether draft passed critique
    iteration:           int            # 0 or 1 (max 1 revision)

    # ── Slack delivery ────────────────────────────────────────────
    slack_blocks:        list[dict]
    slack_result:        dict

    # ── Metadata ──────────────────────────────────────────────────
    data_sources:        list[str]
    error:               str
    error_node:          str

    # ── Investor Relationship Tracking ─────────────────────────────
    relationship_health: dict          # Relationship health metrics
    cold_investors:      list[dict]    # List of cold relationships
