"""Lakebase Postgres helper for the graph queries.

Provides an `execute_query` coroutine matching DatabaseService's interface,
so callers can switch backends via the USE_LAKEBASE flag with minimal code
duplication.

Connection model:
  - One short-lived psycopg connection per query (graph endpoints are
    bursty and low-concurrency; pooling adds complexity).
  - OAuth credentials refreshed via /api/2.0/postgres/credentials when
    the cached token is within 5 minutes of expiry.

Spark SQL → Postgres compatibility:
  - Strips `<catalog>.<schema>.` table qualifiers (Postgres uses bare names).
  - Unquotes integer literals (`'12345'` → `12345`) so bigint comparisons
    work; string literals like `'customer'` are untouched.
  - Other window function / CTE / LEAST / GREATEST syntax is identical
    between Spark and Postgres for our queries.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime
from typing import Any

import psycopg
import psycopg.rows
import requests

from backend import config

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (env-driven)
# ---------------------------------------------------------------------------
LAKEBASE_HOST = os.getenv("LAKEBASE_HOST", "")
LAKEBASE_DATABASE = os.getenv("LAKEBASE_DATABASE", "")
LAKEBASE_ENDPOINT_PATH = os.getenv("LAKEBASE_ENDPOINT_PATH", "")  # e.g. projects/x/branches/production/endpoints/primary
LAKEBASE_USER = os.getenv("LAKEBASE_USER", "")  # set to SP/email; falls back to current-user lookup if empty

# ---------------------------------------------------------------------------
# Postgres credential cache
# ---------------------------------------------------------------------------
_pg_token: str | None = None
_pg_token_expiry: float = 0.0
_pg_user: str | None = None
_pg_lock = threading.Lock()


def _fetch_pg_credential() -> tuple[str, float]:
    """POST /api/2.0/postgres/credentials with workspace OAuth → Postgres OAuth token."""
    workspace_token = config.get_oauth_token()
    resp = requests.post(
        f"{config.DATABRICKS_WORKSPACE_URL}/api/2.0/postgres/credentials",
        headers={"Authorization": f"Bearer {workspace_token}"},
        json={"endpoint": LAKEBASE_ENDPOINT_PATH},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["token"]
    expire_iso = data["expire_time"].replace("Z", "+00:00")
    expiry = datetime.fromisoformat(expire_iso).timestamp()
    return token, expiry


def _resolve_user() -> str:
    """Return the username for the Postgres connection (SP principal or current user)."""
    if LAKEBASE_USER:
        return LAKEBASE_USER
    workspace_token = config.get_oauth_token()
    resp = requests.get(
        f"{config.DATABRICKS_WORKSPACE_URL}/api/2.0/preview/scim/v2/Me",
        headers={"Authorization": f"Bearer {workspace_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["userName"]


def _get_credentials() -> tuple[str, str]:
    """Return (user, token), refreshing if within 5 min of expiry."""
    global _pg_token, _pg_token_expiry, _pg_user
    with _pg_lock:
        if _pg_user is None:
            _pg_user = _resolve_user()
        if _pg_token is None or time.time() > (_pg_token_expiry - 300):
            _logger.info("🔑 Refreshing Lakebase credential…")
            _pg_token, _pg_token_expiry = _fetch_pg_credential()
        return _pg_user, _pg_token


# ---------------------------------------------------------------------------
# Spark SQL → Postgres rewriter
# ---------------------------------------------------------------------------
_QUALIFIED_TABLE_RE = re.compile(r"\b\w+\.\w+\.(graph_nodes|graph_edges)\b")
_QUOTED_INT_RE = re.compile(r"'(\d+)'")


def _spark_to_postgres(sql: str) -> str:
    """Lightweight rewrite: strip catalog.schema prefix; unquote integer literals."""
    sql = _QUALIFIED_TABLE_RE.sub(r"\1", sql)
    sql = _QUOTED_INT_RE.sub(r"\1", sql)
    return sql


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------
def _execute_sync(sql: str) -> list[dict[str, Any]]:
    rewritten = _spark_to_postgres(sql)
    user, token = _get_credentials()
    with psycopg.connect(
        host=LAKEBASE_HOST,
        port=5432,
        dbname=LAKEBASE_DATABASE,
        user=user,
        password=token,
        sslmode="require",
        connect_timeout=10,
    ) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(rewritten)
            if cur.description is None:
                return []
            rows = cur.fetchall()
            # JSONB columns come back as already-parsed dicts; the rest of
            # the codebase expects `properties` as a JSON STRING (it parses
            # itself in format_*_for_cytoscape). Re-stringify for parity.
            import json as _json
            for row in rows:
                if "properties" in row and not isinstance(row["properties"], (str, type(None))):
                    row["properties"] = _json.dumps(row["properties"])
            return rows


async def execute_query(sql: str) -> list[dict[str, Any]]:
    """Async-compatible wrapper around the sync psycopg call.

    Postgres queries against Lakebase are sub-10ms for our graph workload,
    so running on the event loop is fine for now. Move to a thread executor
    if we observe head-of-line blocking under load.
    """
    return _execute_sync(sql)


def is_configured() -> bool:
    """Return True if all required Lakebase env vars are present."""
    return bool(LAKEBASE_HOST and LAKEBASE_DATABASE and LAKEBASE_ENDPOINT_PATH)
