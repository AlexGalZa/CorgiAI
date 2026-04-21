"""
Admin API router for Corgi Insurance staff operations.

All endpoints require staff-level authentication. Provides:
- Analytics dashboards (pipeline, premium, coverage, claims)
- Quote management actions (recalculate, approve, duplicate, simulate)
- Policy lifecycle actions (endorse, cancel, reactivate)
- Audit log access
- Form builder CRUD
- CRUD for quotes, policies, claims, users, orgs, certificates, payments,
  brokered requests, producers, internal/claim documents, policy transactions.

Route registration is delegated to sub-modules; this file wires them together.
"""

from ninja import Router

from admin_api.analytics import register_analytics_routes
from admin_api.crud import register_crud_routes
from admin_api.policy_actions import register_policy_action_routes
from admin_api.quote_actions import register_quote_action_routes

router = Router(tags=["Admin"])

# Register all route groups on the shared router
register_analytics_routes(router)
register_quote_action_routes(router)
register_policy_action_routes(router)
register_crud_routes(router)
