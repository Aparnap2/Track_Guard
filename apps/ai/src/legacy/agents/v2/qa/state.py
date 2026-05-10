"""
QAState — state object for the QAAgent.

The QAAgent answers the founder's top 20 business questions
via Slack or API. Questions are pre-templated for fast response.
"""
from __future__ import annotations
from typing import Optional, TypedDict


class QAState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────
    tenant_id:           str

    # ── Question from founder ─────────────────────────────────────
    question:            str            # raw question from Slack/API
    matched_template:    str            # which of the 20 templates matched
    question_category:   str            # mrr | burn | runway | customers | growth

    # ── Data fetched from database/integrations ───────────────────
    mrr_cents:           int
    arr_cents:           int
    burn_cents:          int
    runway_months:       float
    active_customers:    int
    new_customers:       int
    churned_customers:   int
    mrr_growth_pct:      float
    quick_ratio:         float
    active_users_30d:    int

    # ── Historical context from Qdrant ────────────────────────────
    past_answer:         str            # previous answer to same question
    historical_context:  str            # prose summary

    # ── DSPy-generated outputs ────────────────────────────────────
    answer:              str            # direct 1-2 sentence answer with numbers
    follow_up:           str            # one relevant follow-up question

    # ── Slack delivery ────────────────────────────────────────────
    slack_blocks:        list[dict]
    slack_result:        dict

    # ── Metadata ──────────────────────────────────────────────────
    latency_ms:          int            # response time in milliseconds
    data_sources:        list[str]
    error:               str
    error_node:          str
