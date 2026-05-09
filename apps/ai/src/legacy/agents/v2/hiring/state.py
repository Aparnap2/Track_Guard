"""
HiringAgentState — state object for the HiringAgent.

Hiring agent for candidate scoring and pipeline management.
"""
from __future__ import annotations
from typing import TypedDict


class HiringState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────
    tenant_id:           str

    # ── Input ─────────────────────────────────────────────────────
    candidate_data:      dict              # Raw candidate info
    role_id:             int               # Role they're applying for

    # ── Candidate info ────────────────────────────────────────────
    name:                str
    email:               str
    resume_url:          str
    source:              str

    # ── Scoring results ───────────────────────────────────────────
    score_overall:       float
    score_technical:     float
    culture_signals:     list[str]
    red_flags:           list[str]
    recommended_action:  str
    status:              str

    # ── Pipeline state ────────────────────────────────────────────
    current_stage:       str               # new, screening, interview, offer, hired, rejected

    # ── Metadata ──────────────────────────────────────────────────
    error:               str
    error_node:          str