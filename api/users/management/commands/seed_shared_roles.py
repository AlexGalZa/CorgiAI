"""
Seed the shared Corgi database (used by static-pages, bulldog-law, and
other Corgi apps) with Corgi-specific roles, `corgi.*` permissions, and
role->permission grants. Safe to re-run; every INSERT has
ON CONFLICT DO NOTHING.

Run from the Dokploy app terminal:

    cd /app/api && python manage.py seed_shared_roles

Uses SHARED_DATABASE_URL if set, otherwise the known dokploy-postgres DSN.
"""

from __future__ import annotations

import os
from typing import Any

from django.core.management.base import BaseCommand


DEFAULT_URL = "postgresql://corgi:CorgiInsure2026!@dokploy-postgres:5432/corgi"


# ── Corgi roles ─────────────────────────────────────────────────────
# Mirrors User.ROLE_CHOICES minus policyholder (portal-only, no ops).
ROLES: list[tuple[str, str]] = [
    ("admin", "Corgi admin"),
    ("ae", "Account Executive"),
    ("ae_underwriting", "AE + Underwriting"),
    ("bdr", "Business Development Rep"),
    ("finance", "Finance"),
    ("broker", "Broker partner"),
    ("claims_adjuster", "Claims Adjuster"),
    ("customer_support", "Customer Support"),
    ("read_only", "Read-Only API"),
]

# ── Corgi permissions (corgi.<resource>.<action>) ───────────────────
# Derived from admin/src/lib/permissions.ts + admin/src/App.tsx RoleGuard
# + api/admin_api/helpers.py role groups.
PERMISSIONS: list[tuple[str, str, str, str]] = [
    # (key, resource, action, description)
    # Quotes
    ("corgi.quotes.view", "corgi.quotes", "view", "View quotes"),
    (
        "corgi.quotes.edit",
        "corgi.quotes",
        "edit",
        "Edit / recalculate / duplicate quotes",
    ),
    (
        "corgi.quotes.underwriter_override",
        "corgi.quotes",
        "approve",
        "Underwriter overrides on quote rating",
    ),
    # Policies
    ("corgi.policies.view", "corgi.policies", "view", "View policies"),
    (
        "corgi.policies.edit",
        "corgi.policies",
        "edit",
        "Endorse / cancel / reactivate policies",
    ),
    # Claims
    ("corgi.claims.view", "corgi.claims", "view", "View claims"),
    ("corgi.claims.edit", "corgi.claims", "edit", "File / update claims"),
    # Organizations
    ("corgi.organizations.view", "corgi.organizations", "view", "View organizations"),
    ("corgi.organizations.edit", "corgi.organizations", "edit", "Edit organizations"),
    (
        "corgi.organizations.create",
        "corgi.organizations",
        "create",
        "Create organizations",
    ),
    # Certificates
    (
        "corgi.certificates.view",
        "corgi.certificates",
        "view",
        "View certificates of insurance",
    ),
    (
        "corgi.certificates.edit",
        "corgi.certificates",
        "edit",
        "Issue / edit certificates",
    ),
    # Brokered requests
    (
        "corgi.brokered_requests.view",
        "corgi.brokered_requests",
        "view",
        "View brokered requests",
    ),
    (
        "corgi.brokered_requests.create",
        "corgi.brokered_requests",
        "create",
        "Create brokered requests",
    ),
    (
        "corgi.brokered_requests.edit",
        "corgi.brokered_requests",
        "edit",
        "Edit brokered requests",
    ),
    # Payments
    ("corgi.payments.view", "corgi.payments", "view", "View payments"),
    ("corgi.payments.edit", "corgi.payments", "edit", "Edit payments / issue refunds"),
    # Producers
    ("corgi.producers.view", "corgi.producers", "view", "View producers"),
    ("corgi.producers.edit", "corgi.producers", "edit", "Edit producers"),
    ("corgi.producers.create", "corgi.producers", "create", "Create producers"),
    # Commissions
    ("corgi.commissions.view", "corgi.commissions", "view", "View commissions"),
    # Finance dashboards
    ("corgi.finance.view", "corgi.finance", "view", "View finance dashboard"),
    (
        "corgi.entity_finance.view",
        "corgi.entity_finance",
        "view",
        "View per-entity finance",
    ),
    # Users
    ("corgi.users.view", "corgi.users", "view", "View users"),
    ("corgi.users.edit", "corgi.users", "edit", "Edit users"),
    ("corgi.users.create", "corgi.users", "create", "Create staff user accounts"),
    (
        "corgi.users.assign_permissions",
        "corgi.users",
        "approve",
        "Assign roles / permissions to users",
    ),
    (
        "corgi.users.impersonate",
        "corgi.users",
        "impersonate",
        "Impersonate users for support",
    ),
    # Reports
    ("corgi.reports.view", "corgi.reports", "view", "View reports"),
    ("corgi.reports.export", "corgi.reports", "export", "Export CSV / PDF reports"),
    # Form builder
    ("corgi.form_builder.view", "corgi.form_builder", "view", "View form builder"),
    (
        "corgi.form_builder.edit",
        "corgi.form_builder",
        "edit",
        "Edit form builder definitions",
    ),
    # Sales metrics / performance
    (
        "corgi.sales_metrics.view",
        "corgi.sales_metrics",
        "view",
        "View external sales metrics",
    ),
    (
        "corgi.sales_performance.view",
        "corgi.sales_performance",
        "view",
        "View internal AE/BDR performance",
    ),
]


# Role groupings (match api/admin_api/helpers.py).
_WRITE = ["admin", "ae", "ae_underwriting"]
_READ_ALL_STAFF = ["admin", "ae", "ae_underwriting", "bdr", "finance", "broker"]
_FINANCE = ["admin", "finance"]
_ADMIN = ["admin"]
_CLAIMS = ["admin", "ae", "ae_underwriting", "claims_adjuster"]

# ── Role -> permission key grants ───────────────────────────────────
GRANTS: list[tuple[str, list[str]]] = [
    ("corgi.quotes.view", _READ_ALL_STAFF),
    ("corgi.quotes.edit", _WRITE),
    ("corgi.quotes.underwriter_override", ["admin", "ae_underwriting"]),
    ("corgi.policies.view", _READ_ALL_STAFF),
    ("corgi.policies.edit", _WRITE),
    ("corgi.claims.view", _CLAIMS),
    ("corgi.claims.edit", _WRITE),
    ("corgi.organizations.view", _WRITE),
    ("corgi.organizations.edit", _WRITE),
    ("corgi.organizations.create", _WRITE),
    ("corgi.certificates.view", _READ_ALL_STAFF),
    ("corgi.certificates.edit", ["admin", "ae_underwriting"]),
    ("corgi.brokered_requests.view", _READ_ALL_STAFF),
    ("corgi.brokered_requests.create", ["admin", "ae", "ae_underwriting", "bdr"]),
    ("corgi.brokered_requests.edit", _WRITE),
    ("corgi.payments.view", _READ_ALL_STAFF),
    ("corgi.payments.edit", _FINANCE),
    ("corgi.producers.view", _FINANCE),
    ("corgi.producers.edit", _ADMIN),
    ("corgi.producers.create", _ADMIN),
    ("corgi.commissions.view", _FINANCE),
    ("corgi.finance.view", _FINANCE),
    ("corgi.entity_finance.view", _FINANCE),
    ("corgi.users.view", _WRITE),
    ("corgi.users.edit", _WRITE),
    ("corgi.users.create", _ADMIN),
    ("corgi.users.assign_permissions", _ADMIN),
    ("corgi.users.impersonate", _WRITE),
    ("corgi.reports.view", ["admin", "ae", "ae_underwriting", "bdr", "finance"]),
    ("corgi.reports.export", _READ_ALL_STAFF),
    ("corgi.form_builder.view", _WRITE),
    ("corgi.form_builder.edit", _WRITE),
    ("corgi.sales_metrics.view", _WRITE),
    ("corgi.sales_performance.view", _WRITE),
]


class Command(BaseCommand):
    help = "Seed roles + corgi.* permissions + grants into the shared Corgi database."

    def handle(self, *args: Any, **options: Any) -> None:
        import psycopg2

        url = os.getenv("SHARED_DATABASE_URL") or DEFAULT_URL
        self.stdout.write(self.style.NOTICE(f"Connecting to shared DB: {_safe(url)}"))

        conn = psycopg2.connect(url)
        conn.autocommit = False
        try:
            cur = conn.cursor()

            cur.execute(
                "SELECT to_regclass('public.roles'), to_regclass('public.permissions'), "
                "to_regclass('public.role_permissions')"
            )
            row = cur.fetchone()
            if not all(row):
                raise SystemExit(
                    "Shared DB is missing roles/permissions/role_permissions tables. "
                    "The portal (static-pages) must create them before this seed runs."
                )

            roles_added = self._seed_roles(cur)
            perms_added = self._seed_permissions(cur)
            grants_added = self._seed_grants(cur)

            conn.commit()
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. +{roles_added} roles, +{perms_added} permissions, +{grants_added} grants. "
                    "All existing rows left untouched."
                )
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _seed_roles(self, cur: Any) -> int:
        added = 0
        for name, description in ROLES:
            cur.execute(
                "INSERT INTO roles (name, description) VALUES (%s, %s) "
                "ON CONFLICT (name) DO NOTHING",
                (name, description),
            )
            if cur.rowcount:
                added += 1
        self.stdout.write(f"  roles: +{added} (of {len(ROLES)})")
        return added

    def _seed_permissions(self, cur: Any) -> int:
        added = 0
        for key, resource, action, description in PERMISSIONS:
            # Try the common static-pages schema first (key/resource/action/description).
            # Some schemas use 'access' instead of 'action' — bulldog-law reads both.
            try:
                cur.execute(
                    "INSERT INTO permissions (key, resource, action, description) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (key) DO NOTHING",
                    (key, resource, action, description),
                )
            except Exception:
                cur.connection.rollback()
                cur.execute(
                    "INSERT INTO permissions (key, resource, access, description) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (key) DO NOTHING",
                    (key, resource, action, description),
                )
            if cur.rowcount:
                added += 1
        self.stdout.write(f"  permissions: +{added} (of {len(PERMISSIONS)})")
        return added

    def _seed_grants(self, cur: Any) -> int:
        added = 0
        total = sum(len(roles) for _, roles in GRANTS)
        for key, roles in GRANTS:
            for role in roles:
                cur.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "SELECT r.id, p.id FROM roles r, permissions p "
                    "WHERE r.name = %s AND p.key = %s "
                    "ON CONFLICT DO NOTHING",
                    (role, key),
                )
                if cur.rowcount:
                    added += 1
        self.stdout.write(f"  grants: +{added} (of {total})")
        return added


def _safe(url: str) -> str:
    if "@" not in url:
        return url
    scheme_creds, host = url.split("@", 1)
    if ":" not in scheme_creds:
        return url
    prefix, _ = scheme_creds.rsplit(":", 1)
    return f"{prefix}:***@{host}"
