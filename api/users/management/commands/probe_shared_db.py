"""
Introspect the shared Corgi database (the one static-pages + bulldog-law
use) for existing roles / permissions / grants.

Run from the Dokploy app terminal:

    cd /app/api && python manage.py probe_shared_db

Uses SHARED_DATABASE_URL if set, otherwise defaults to the known
dokploy-postgres connection. Reads only; never writes.
"""

from __future__ import annotations

import os
from typing import Any

from django.core.management.base import BaseCommand


DEFAULT_URL = "postgresql://corgi:CorgiInsure2026!@dokploy-postgres:5432/corgi"


class Command(BaseCommand):
    help = (
        "Dump roles / corgi.* permissions / role grants from the shared Corgi database."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        import psycopg2

        url = os.getenv("SHARED_DATABASE_URL") or DEFAULT_URL
        self.stdout.write(self.style.NOTICE(f"Connecting to: {self._safe_url(url)}"))

        conn = psycopg2.connect(url)
        try:
            cur = conn.cursor()
            self._section("ROLES", cur, "SELECT name FROM roles ORDER BY name")
            self._section(
                "PERMISSIONS (corgi.*)",
                cur,
                "SELECT key FROM permissions WHERE resource LIKE 'corgi.%' ORDER BY key",
            )
            self._section(
                "PERMISSIONS (other prefixes — for context only)",
                cur,
                "SELECT resource || '  ' || key FROM permissions "
                "WHERE resource NOT LIKE 'corgi.%' ORDER BY resource, key",
            )
            self._section(
                "ROLE -> corgi.* GRANTS",
                cur,
                "SELECT r.name || '  ->  ' || p.key "
                "FROM role_permissions rp "
                "JOIN roles r       ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE p.resource LIKE 'corgi.%' "
                "ORDER BY r.name, p.key",
            )
        finally:
            conn.close()

    def _section(self, title: str, cur: Any, sql: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"── {title} ──"))
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"  query failed: {exc}"))
            return
        if not rows:
            self.stdout.write("  (none)")
            return
        for row in rows:
            self.stdout.write(f"  {row[0]}")

    @staticmethod
    def _safe_url(url: str) -> str:
        # Redact the password before logging.
        if "@" not in url:
            return url
        scheme_creds, host = url.split("@", 1)
        if ":" not in scheme_creds:
            return url
        prefix, _ = scheme_creds.rsplit(":", 1)
        return f"{prefix}:***@{host}"
