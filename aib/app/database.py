"""
PostgreSQL connection pool and query helpers.
Provides graceful degradation when the database is unavailable.
"""

import time
import psycopg2
import psycopg2.pool
import psycopg2.extras
from app import config

# ── Connection pool ─────────────────────────────────────────────────────
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_db_available: bool | None = None  # None = not yet tested


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=config.DATABASE_URL,
        )
    return _pool


def is_db_available() -> bool:
    """Check if the database is available (cached after first test)."""
    global _db_available
    if _db_available is None:
        _db_available = test_connection()
    return _db_available


def query(sql: str, params: tuple | list | None = None) -> list[dict]:
    """
    Execute a parameterised query and return rows as list of dicts.
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        start = time.time()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            duration_ms = int((time.time() - start) * 1000)
            if config.DEBUG:
                print(f"DB query ({duration_ms}ms, {cur.rowcount} rows): {sql[:80]}")
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return []
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def query_one(sql: str, params: tuple | list | None = None) -> dict | None:
    """
    Execute a query and return the first row or None.
    """
    rows = query(sql, params)
    return rows[0] if rows else None


def test_connection() -> bool:
    """
    Verify the database is reachable.
    """
    global _db_available
    try:
        query("SELECT NOW()")
        print("Database connected successfully")
        _db_available = True
        return True
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        _db_available = False
        return False


def close_pool() -> None:
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None
