"""Verify DB migrations are applied."""
import os
from pathlib import Path

import pytest

# Load .env file for DATABASE_URL
_env_file = Path(__file__).resolve().parents[2] / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file, override=False)
    except ImportError:
        pass

try:
    import psycopg2

    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False

# Skip if DATABASE_URL not set
if not os.environ.get("DATABASE_URL"):
    PG_AVAILABLE = False

# The Docker PostgreSQL maps internal 5432 → host 5433.
# If the shell has DATABASE_URL with port 5432, it won't work —
# transparently fix it.
_raw_dsn = os.environ.get("DATABASE_URL", "")
if ":5432/" in _raw_dsn and "localhost" in _raw_dsn:
    DSN = _raw_dsn.replace(":5432/", ":5433/")
else:
    DSN = _raw_dsn or "postgresql://iterateswarm:iterateswarm@localhost:5433/iterateswarm"


class TestDBMigrations:
    def test_agent_alerts_has_insight_columns(self):
        if not PG_AVAILABLE:
            pytest.skip("psycopg2 not available")
        try:
            with psycopg2.connect(DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT insight_acknowledged FROM agent_alerts LIMIT 1"
                    )
        except Exception:
            pytest.fail("insight_acknowledged column missing")

    def test_resolved_blindspots_table_exists(self):
        if not PG_AVAILABLE:
            pytest.skip()
        try:
            with psycopg2.connect(DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM resolved_blindspots LIMIT 1")
        except Exception:
            pytest.fail("resolved_blindspots table missing")

    def test_eval_scores_table_exists(self):
        if not PG_AVAILABLE:
            pytest.skip()
        try:
            with psycopg2.connect(DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM eval_scores LIMIT 1")
        except Exception:
            pytest.fail("eval_scores table missing")

    def test_onboarding_events_table_exists(self):
        if not PG_AVAILABLE:
            pytest.skip()
        try:
            with psycopg2.connect(DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM onboarding_events LIMIT 1")
        except Exception:
            pytest.fail("onboarding_events table missing")

    def test_existing_tables_unchanged(self):
        """Verify existing tables still have expected columns."""
        if not PG_AVAILABLE:
            pytest.skip()
        try:
            with psycopg2.connect(DSN) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'founders' AND column_name = 'id' "
                        "LIMIT 1"
                    )
                    assert cur.fetchone() is not None, "founders table missing or corrupted"
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'messages' AND column_name = 'id' "
                        "LIMIT 1"
                    )
                    assert cur.fetchone() is not None, "messages table missing or corrupted"
        except AssertionError:
            pytest.fail("Existing tables modified unexpectedly")
        except Exception as e:
            pytest.fail(f"Existing tables modified unexpectedly: {e}")
