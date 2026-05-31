"""Trust Battery - durable storage in Postgres + Graphiti."""
import os
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config.database import get_database_url
from .trust_battery import AgentTrustProfile

log = logging.getLogger(__name__)

DATABASE_URL = get_database_url("iterateswarm")


async def save_trust_profile(profile: AgentTrustProfile) -> bool:
    """Write trust profile to Postgres and update mission_state with trust metadata."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        now = datetime.now(timezone.utc)

        await conn.execute(
            """
            INSERT INTO feedback_events (
                tenant_id, agent_name, event_type, event_data, created_at, trust_score_before, trust_score_after
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            ON CONFLICT DO NOTHING
            """,
            profile.tenant_id,
            profile.agent_name,
            "trust_profile_update",
            str({
                "trust_score": profile.trust_score,
                "route_priority": profile.route_priority,
                "success_rate_7d": profile.success_rate_7d,
                "schema_parse_rate": profile.schema_parse_rate,
                "founder_acceptance_rate": profile.founder_acceptance_rate,
                "false_positive_rate": profile.false_positive_rate,
                "avg_latency_ms": profile.avg_latency_ms,
            }),
            now,
            profile.trust_score,
            profile.trust_score,
        )

        await conn.execute(
            """
            INSERT INTO mission_states (tenant_id, timestamp, trust_score, route_priority)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tenant_id) DO UPDATE SET
                trust_score = EXCLUDED.trust_score,
                route_priority = EXCLUDED.route_priority
            """,
            profile.tenant_id,
            now,
            profile.trust_score,
            profile.route_priority,
        )

        await conn.close()
        log.info(f"Saved trust profile for {profile.agent_name} tenant {profile.tenant_id}")
        return True
    except Exception as e:
        log.error(f"Failed to save trust profile: {e}")
        return False


async def log_trust_event(
    tenant_id: str,
    agent_name: str,
    event_type: str,
    event_data: dict,
) -> bool:
    """Log a trust event to feedback_events table for audit trail.

    Args:
        tenant_id: The tenant the event belongs to
        agent_name: The agent involved
        event_type: Type of event (rate_good, rate_bad, dispute, etc.)
        event_data: Additional context (alert_id, score, trust_score_after, etc.)

    Returns:
        True if logged successfully, False on failure (best-effort)
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """
            INSERT INTO feedback_events (tenant_id, agent_name, event_type, event_data, created_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW())
            """,
            tenant_id,
            agent_name,
            event_type,
            str(event_data),
        )
        await conn.close()
        log.info(
            "Trust event logged",
            extra={
                "tenant_id": tenant_id,
                "agent_name": agent_name,
                "event_type": event_type,
            },
        )
        return True
    except Exception as e:
        log.warning(f"Failed to log trust event to DB (best-effort): {e}")
        return False


async def load_trust_profile(tenant_id: str, agent_name: str) -> AgentTrustProfile:
    """Load trust profile from Postgres."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        row = await conn.fetchrow(
            """
            SELECT fe.tenant_id, fe.agent_name,
                   (fe.event_data->>'trust_score')::float as trust_score,
                   (fe.event_data->>'route_priority')::int as route_priority,
                   (fe.event_data->>'success_rate_7d')::float as success_rate_7d,
                   (fe.event_data->>'schema_parse_rate')::float as schema_parse_rate,
                   (fe.event_data->>'founder_acceptance_rate')::float as founder_acceptance_rate,
                   (fe.event_data->>'false_positive_rate')::float as false_positive_rate,
                   (fe.event_data->>'avg_latency_ms')::int as avg_latency_ms,
                   fe.event_data->>'last_failure_at' as last_failure_at,
                   fe.created_at as updated_at
            FROM feedback_events fe
            WHERE fe.tenant_id = $1 AND fe.agent_name = $2
              AND fe.event_type = 'trust_profile_update'
            ORDER BY fe.created_at DESC
            LIMIT 1
            """,
            tenant_id,
            agent_name,
        )
        await conn.close()

        if row:
            last_failure = None
            if row["last_failure_at"]:
                try:
                    last_failure = datetime.fromisoformat(row["last_failure_at"])
                except ValueError:
                    pass

            return AgentTrustProfile(
                agent_name=row["agent_name"],
                tenant_id=row["tenant_id"],
                trust_score=row["trust_score"] or 0.75,
                route_priority=row["route_priority"] or 1,
                success_rate_7d=row["success_rate_7d"] or 0.8,
                schema_parse_rate=row["schema_parse_rate"] or 0.9,
                founder_acceptance_rate=row["founder_acceptance_rate"] or 0.85,
                false_positive_rate=row["false_positive_rate"] or 0.05,
                avg_latency_ms=row["avg_latency_ms"] or 1000,
                last_failure_at=last_failure,
                updated_at=row["updated_at"],
            )
    except Exception as e:
        log.warning(f"Failed to load trust profile from DB, using defaults: {e}")

    return AgentTrustProfile(agent_name=agent_name, tenant_id=tenant_id)


async def get_trust_leaderboard(tenant_id: str) -> list[AgentTrustProfile]:
    """Get all agent profiles sorted by trust score."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (fe.agent_name)
                   fe.tenant_id, fe.agent_name,
                   (fe.event_data->>'trust_score')::float as trust_score,
                   (fe.event_data->>'route_priority')::int as route_priority,
                   (fe.event_data->>'success_rate_7d')::float as success_rate_7d,
                   (fe.event_data->>'schema_parse_rate')::float as schema_parse_rate,
                   (fe.event_data->>'founder_acceptance_rate')::float as founder_acceptance_rate,
                   (fe.event_data->>'false_positive_rate')::float as false_positive_rate,
                   (fe.event_data->>'avg_latency_ms')::int as avg_latency_ms,
                   fe.event_data->>'last_failure_at' as last_failure_at,
                   fe.created_at as updated_at
            FROM feedback_events fe
            WHERE fe.tenant_id = $1 AND fe.event_type = 'trust_profile_update'
            ORDER BY fe.agent_name, fe.created_at DESC
            """,
            tenant_id,
        )
        await conn.close()

        profiles = []
        seen = set()
        for row in rows:
            if row["agent_name"] in seen:
                continue
            seen.add(row["agent_name"])

            last_failure = None
            if row["last_failure_at"]:
                try:
                    last_failure = datetime.fromisoformat(row["last_failure_at"])
                except ValueError:
                    pass

            profiles.append(
                AgentTrustProfile(
                    agent_name=row["agent_name"],
                    tenant_id=row["tenant_id"],
                    trust_score=row["trust_score"] or 0.75,
                    route_priority=row["route_priority"] or 1,
                    success_rate_7d=row["success_rate_7d"] or 0.8,
                    schema_parse_rate=row["schema_parse_rate"] or 0.9,
                    founder_acceptance_rate=row["founder_acceptance_rate"] or 0.85,
                    false_positive_rate=row["false_positive_rate"] or 0.05,
                    avg_latency_ms=row["avg_latency_ms"] or 1000,
                    last_failure_at=last_failure,
                    updated_at=row["updated_at"],
                )
            )

        profiles.sort(key=lambda p: p.trust_score, reverse=True)
        return profiles
    except Exception as e:
        log.warning(f"Failed to load trust leaderboard from DB: {e}")
        return []