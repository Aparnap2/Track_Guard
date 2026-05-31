"""
MissionState — Shared Context Object.

Per PRD Section 11:
All agents read MissionState before running.
All agents write their domain fields after running.
Stored in PostgreSQL `mission_states` table. Updated atomically.

Schema matches 001_session_layer.sql (columns, not JSONB).
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from src.config.database import get_database_url

log = logging.getLogger(__name__)

DATABASE_URL = get_database_url("iterateswarm")


@dataclass
class MissionState:
    """Shared context object read/written by all agents.

    Per PRD Section 11:
    - All agents read MissionState before running
    - All agents write their domain fields after running
    - Stored in PostgreSQL mission_states table

    Schema matches 001_session_layer.sql (columns, not JSONB).
    """

    tenant_id: str
    timestamp: datetime | None = None

    # Data Quality Gate fields
    data_last_synced: datetime | None = None
    mrr: float | None = None
    burn_rate: float | None = None

    # Finance domain (Finance Guardian writes)
    runway_days: int | None = None
    burn_alert: bool = False
    burn_severity: str | None = None  # low, medium, high, critical

    # BI domain (BI Analyst writes)
    mrr_trend: str | None = None  # growing, stable, declining
    churn_rate: float | None = None

    # Ops domain (Ops Watch writes)
    churn_risk_users: str | None = None  # comma-separated
    top_feature_ask: str | None = None
    error_spike: bool = False

    # Cross-agent signals (Co-founder manages)
    active_alerts: str | None = None  # comma-separated
    founder_focus: str | None = None

    # Trust Battery integration (V3.0)
    trust_score: float | None = None  # 0.00-1.00 from trust battery
    route_priority: int | None = None  # routing priority based on trust

    # Runtime fields (not persisted to DB)
    skip_reason: str | None = None
    data_quality: "DataQualityResult" = None


async def get_mission_state(tenant_id: str) -> MissionState:
    """Get MissionState from database.

    Returns empty MissionState if not found (graceful fallback per PRD Section 25).

    Args:
        tenant_id: The tenant to get state for

    Returns:
        MissionState (empty if not found)
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        row = await conn.fetchrow(
            """
            SELECT tenant_id, timestamp, runway_days, burn_alert, burn_severity,
                   mrr_trend, churn_rate, churn_risk_users, top_feature_ask,
                   error_spike, active_alerts, founder_focus, trust_score, route_priority
            FROM mission_states
            WHERE tenant_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            tenant_id,
        )
        await conn.close()

        if row:
            return MissionState(
                tenant_id=row["tenant_id"],
                timestamp=row["timestamp"],
                runway_days=row["runway_days"],
                burn_alert=row["burn_alert"],
                burn_severity=row["burn_severity"],
                mrr_trend=row["mrr_trend"],
                churn_rate=row["churn_rate"],
                churn_risk_users=row["churn_risk_users"],
                top_feature_ask=row["top_feature_ask"],
                error_spike=row["error_spike"],
                active_alerts=row["active_alerts"],
                founder_focus=row["founder_focus"],
                trust_score=row["trust_score"],
                route_priority=row["route_priority"],
            )
    except Exception as e:
        log.warning(f"MissionState lookup failed for {tenant_id}: {e}")

    return MissionState(tenant_id=tenant_id)


async def update_mission_state(state: MissionState) -> bool:
    """Update MissionState in database atomically.

    Per PRD Section 11: Updated atomically.

    Args:
        state: MissionState to persist

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """
            INSERT INTO mission_states (
                tenant_id, timestamp, runway_days, burn_alert, burn_severity,
                mrr_trend, churn_rate, churn_risk_users, top_feature_ask,
                error_spike, active_alerts, founder_focus, trust_score, route_priority, created_at
            )
            VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
                timestamp = NOW(),
                runway_days = EXCLUDED.runway_days,
                burn_alert = EXCLUDED.burn_alert,
                burn_severity = EXCLUDED.burn_severity,
                mrr_trend = EXCLUDED.mrr_trend,
                churn_rate = EXCLUDED.churn_rate,
                churn_risk_users = EXCLUDED.churn_risk_users,
                top_feature_ask = EXCLUDED.top_feature_ask,
                error_spike = EXCLUDED.error_spike,
                active_alerts = EXCLUDED.active_alerts,
                founder_focus = EXCLUDED.founder_focus,
                trust_score = EXCLUDED.trust_score,
                route_priority = EXCLUDED.route_priority
            """,
            state.tenant_id,
            state.runway_days,
            state.burn_alert,
            state.burn_severity,
            state.mrr_trend,
            state.churn_rate,
            state.churn_risk_users,
            state.top_feature_ask,
            state.error_spike,
            state.active_alerts,
            state.founder_focus,
            state.trust_score,
            state.route_priority,
        )
        await conn.close()
        log.info(f"MissionState updated for tenant: {state.tenant_id}")
        return True
    except Exception as e:
        log.error(f"MissionState update failed for {state.tenant_id}: {e}")
        return False