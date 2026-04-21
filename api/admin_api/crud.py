"""
CRUD (list / detail / update) endpoints for the Admin API.

Covers: audit log, users, organizations, forms, claims, internal documents,
brokered requests, quotes, policies, payments, certificates, producers,
policy transactions, claim documents.
"""

from typing import Any

from django.db.models import Q
from django.http import HttpRequest

from admin_api.helpers import (
    ADMIN_ROLES,
    ALL_STAFF_ROLES,
    FINANCE_ROLES,
    OPERATIONS_ROLES,
    _require_role,
    _scope_queryset_by_role,
)
from admin_api.schemas import (
    AuditLogEntry as AuditLogEntrySchema,
    AuditLogResponse,
    FormDefinitionInput,
)
from common.schemas import ApiResponseSchema
from forms.service import FormService
from users.auth import JWTAuth


# ── Form serializer helper ───────────────────────────────────────────


def _serialize_form(form_def) -> dict:
    """Serialize a FormDefinition instance to a response dict."""
    return {
        "id": form_def.id,
        "name": form_def.name,
        "slug": form_def.slug,
        "version": form_def.version,
        "description": form_def.description,
        "fields": form_def.fields,
        "conditional_logic": form_def.conditional_logic,
        "rating_field_mappings": form_def.rating_field_mappings,
        "coverage_type": form_def.coverage_type,
        "is_active": form_def.is_active,
        "created_at": form_def.created_at.isoformat() if form_def.created_at else None,
        "updated_at": form_def.updated_at.isoformat() if form_def.updated_at else None,
    }


def register_crud_routes(router):
    """Register all CRUD list/detail/update endpoints on the given router."""

    # ═══════════════════════════════════════════════════════════════════
    # Audit Log
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/audit-log",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="Paginated audit log entries",
    )
    def get_audit_log(
        request: HttpRequest,
        limit: int = 50,
        offset: int = 0,
        user_id: int = None,
        model_name: str = None,
        object_id: str = None,
        action: str = None,
        from_date: str = None,
        to_date: str = None,
    ) -> tuple[int, dict[str, Any]]:
        """Return paginated and filtered audit log entries."""
        _require_role(request, ADMIN_ROLES, "view_audit_log")

        from common.models import AuditLogEntry

        qs = AuditLogEntry.objects.select_related("user").order_by("-timestamp")

        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if model_name:
            qs = qs.filter(model_name=model_name)
        if object_id:
            qs = qs.filter(object_id=object_id)
        if action:
            qs = qs.filter(action=action)
        if from_date:
            qs = qs.filter(timestamp__date__gte=from_date)
        if to_date:
            qs = qs.filter(timestamp__date__lte=to_date)

        total = qs.count()
        entries_qs = qs[offset : offset + limit]

        entries = [
            AuditLogEntrySchema(
                id=entry.id,
                timestamp=entry.timestamp,
                actor=entry.user.email if entry.user else None,
                action=entry.action,
                content_type=entry.model_name,
                object_id=entry.object_id,
                changes=entry.changes or {},
            )
            for entry in entries_qs
        ]

        data = AuditLogResponse(
            entries=entries, total=total, limit=limit, offset=offset
        )
        return 200, {"success": True, "message": "Audit log", "data": data.dict()}

    # ═══════════════════════════════════════════════════════════════════
    # Users
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/users",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all users (paginated)",
    )
    def list_users(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        role: str = "",
        is_active: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all users for admin dashboard."""
        _require_role(request, ADMIN_ROLES, "list_users")
        from users.models import User

        qs = User.objects.all()

        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        allowed_ordering = {
            "created_at",
            "-created_at",
            "email",
            "-email",
            "last_name",
            "-last_name",
            "role",
            "-role",
        }
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        users = qs[offset : offset + page_size]

        results = [
            {
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": f"{u.first_name} {u.last_name}".strip() or u.email,
                "role": u.role,
                "phone_number": getattr(u, "phone_number", ""),
                "company_name": getattr(u, "company_name", ""),
                "is_active": u.is_active,
                "is_staff": u.is_staff,
                "created_at": u.created_at.isoformat()
                if hasattr(u, "created_at") and u.created_at
                else None,
                "updated_at": u.updated_at.isoformat()
                if hasattr(u, "updated_at") and u.updated_at
                else None,
            }
            for u in users
        ]

        return 200, {
            "success": True,
            "message": "Users list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.patch(
        "/users/{user_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Update a user",
    )
    def update_user(request: HttpRequest, user_id: int) -> tuple[int, dict[str, Any]]:
        """Update a user's details (admin)."""
        _require_role(request, ADMIN_ROLES, "update_user")
        import json as _json
        from users.models import User

        try:
            u = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        body = _json.loads(request.body) if request.body else {}
        for field in (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "company_name",
            "role",
            "is_active",
            "is_staff",
        ):
            if field in body:
                setattr(u, field, body[field])
        u.save()

        return 200, {
            "success": True,
            "message": "User updated",
            "data": {"id": u.id, "email": u.email},
        }

    # ═══════════════════════════════════════════════════════════════════
    # Organizations
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/organizations",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all organizations (paginated)",
    )
    def list_organizations(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all organizations for admin dashboard."""
        _require_role(request, ADMIN_ROLES, "list_organizations")
        from organizations.models import Organization

        qs = Organization.objects.select_related("owner").all()

        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(owner__email__icontains=search)
            )

        allowed_ordering = {"created_at", "-created_at", "name", "-name"}
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        orgs = qs[offset : offset + page_size]

        results = [
            {
                "id": org.id,
                "name": org.name,
                "owner": org.owner_id,
                "owner_detail": {
                    "email": org.owner.email,
                    "full_name": f"{org.owner.first_name} {org.owner.last_name}".strip()
                    or org.owner.email,
                }
                if org.owner
                else None,
                "is_personal": org.is_personal,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            }
            for org in orgs
        ]

        return 200, {
            "success": True,
            "message": "Organizations list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.patch(
        "/organizations/{org_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Update an organization",
    )
    def update_organization(
        request: HttpRequest, org_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Update an organization's details."""
        _require_role(request, ADMIN_ROLES, "update_organization")
        import json
        from organizations.models import Organization

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        body = json.loads(request.body) if request.body else {}
        for field in ("name", "is_personal"):
            if field in body:
                setattr(org, field, body[field])
        org.save()

        return 200, {
            "success": True,
            "message": "Organization updated",
            "data": {
                "id": org.id,
                "name": org.name,
                "is_personal": org.is_personal,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Form Builder CRUD
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/forms",
        auth=JWTAuth(),
        response={200: ApiResponseSchema},
        summary="List all form definitions",
    )
    def list_forms(request: HttpRequest) -> tuple[int, dict[str, Any]]:
        """List all form definitions, ordered by name."""
        _require_role(request, ALL_STAFF_ROLES, "list_forms")
        forms = FormService.list_forms()
        data = [_serialize_form(f) for f in forms]
        return 200, {"success": True, "message": "Forms list", "data": data}

    @router.get(
        "/forms/{form_id}",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Get a single form definition",
    )
    def get_form(request: HttpRequest, form_id: int) -> tuple[int, dict[str, Any]]:
        """Retrieve a single form definition by ID."""
        _require_role(request, ALL_STAFF_ROLES, "get_form")
        form_def = FormService.get_form_by_id(form_id)
        if not form_def:
            return 404, {"success": False, "message": "Form not found", "data": None}
        return 200, {
            "success": True,
            "message": "Form retrieved",
            "data": _serialize_form(form_def),
        }

    @router.post(
        "/forms",
        auth=JWTAuth(),
        response={201: ApiResponseSchema, 400: ApiResponseSchema},
        summary="Create a new form definition",
    )
    def create_form(
        request: HttpRequest, data: FormDefinitionInput
    ) -> tuple[int, dict[str, Any]]:
        """Create a new form definition for coverage questionnaires."""
        _require_role(request, ADMIN_ROLES, "create_form")
        form_data = data.dict(exclude_none=True)
        if "fields" in form_data:
            form_data["fields"] = [
                f.dict() if hasattr(f, "dict") else f for f in form_data["fields"]
            ]
        form_def = FormService.create_form(form_data)
        return 201, {
            "success": True,
            "message": "Form created",
            "data": _serialize_form(form_def),
        }

    @router.put(
        "/forms/{form_id}",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Update a form definition",
    )
    def update_form(
        request: HttpRequest, form_id: int, data: FormDefinitionInput
    ) -> tuple[int, dict[str, Any]]:
        """Update an existing form definition."""
        _require_role(request, ADMIN_ROLES, "update_form")
        form_data = data.dict(exclude_none=True)
        if "fields" in form_data:
            form_data["fields"] = [
                f.dict() if hasattr(f, "dict") else f for f in form_data["fields"]
            ]
        form_def = FormService.update_form(form_id, form_data)
        if not form_def:
            return 404, {"success": False, "message": "Form not found", "data": None}
        return 200, {
            "success": True,
            "message": "Form updated",
            "data": _serialize_form(form_def),
        }

    @router.delete(
        "/forms/{form_id}",
        auth=JWTAuth(),
        response={200: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Delete a form definition",
    )
    def delete_form(request: HttpRequest, form_id: int) -> tuple[int, dict[str, Any]]:
        """Soft-delete a form definition by deactivating it."""
        _require_role(request, ADMIN_ROLES, "delete_form")
        success = FormService.delete_form(form_id)
        if not success:
            return 404, {"success": False, "message": "Form not found", "data": None}
        return 200, {"success": True, "message": "Form deactivated", "data": None}

    @router.post(
        "/forms/{form_id}/duplicate",
        auth=JWTAuth(),
        response={201: ApiResponseSchema, 404: ApiResponseSchema},
        summary="Duplicate a form definition with new version",
    )
    def duplicate_form(
        request: HttpRequest, form_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Create a copy of an existing form with incremented version."""
        _require_role(request, ADMIN_ROLES, "duplicate_form")
        form_def = FormService.duplicate_form(form_id)
        if not form_def:
            return 404, {"success": False, "message": "Form not found", "data": None}
        return 201, {
            "success": True,
            "message": "Form duplicated",
            "data": _serialize_form(form_def),
        }

    # ═══════════════════════════════════════════════════════════════════
    # Claims
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/claims",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all claims (paginated)",
    )
    def list_claims(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        status: str = "",
        ordering: str = "-created_at",
        include_deleted: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all claims for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_claims")
        from claims.models import Claim

        manager = Claim.all_objects if include_deleted else Claim.objects
        qs = manager.select_related("policy", "user", "organization").all()

        if search:
            qs = qs.filter(
                Q(claim_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)

        allowed = {
            "created_at",
            "-created_at",
            "status",
            "-status",
            "claim_number",
            "-claim_number",
        }
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": c.id,
                "claim_number": c.claim_number,
                "policy": c.policy_id,
                "user": c.user_id,
                "organization": getattr(c, "organization_id", None),
                "organization_name": getattr(
                    getattr(c, "organization", None), "name", ""
                ),
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone_number": getattr(c, "phone_number", ""),
                "description": c.description,
                "status": c.status,
                "admin_notes": getattr(c, "admin_notes", ""),
                "loss_state": getattr(c, "loss_state", ""),
                "paid_loss": str(getattr(c, "paid_loss", 0)),
                "paid_lae": str(getattr(c, "paid_lae", 0)),
                "case_reserve_loss": str(getattr(c, "case_reserve_loss", 0)),
                "case_reserve_lae": str(getattr(c, "case_reserve_lae", 0)),
                "total_incurred": str(getattr(c, "total_incurred", 0)),
                "claim_report_date": c.claim_report_date.isoformat()
                if getattr(c, "claim_report_date", None)
                else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in items
        ]

        return 200, {
            "success": True,
            "message": "Claims list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.get(
        "/claims/{claim_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Get a single claim",
    )
    def get_claim_detail(
        request: HttpRequest, claim_id: int
    ) -> tuple[int, dict[str, Any]]:
        _require_role(request, ALL_STAFF_ROLES, "view_claim_detail")
        from claims.models import Claim

        try:
            c = Claim.objects.get(pk=claim_id)
        except Claim.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        return 200, {
            "success": True,
            "message": "Claim detail",
            "data": {
                "id": c.id,
                "claim_number": c.claim_number,
                "policy": c.policy_id,
                "user": c.user_id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "description": c.description,
                "status": c.status,
                "admin_notes": getattr(c, "admin_notes", ""),
                "loss_state": getattr(c, "loss_state", ""),
                "paid_loss": str(getattr(c, "paid_loss", 0)),
                "paid_lae": str(getattr(c, "paid_lae", 0)),
                "case_reserve_loss": str(getattr(c, "case_reserve_loss", 0)),
                "case_reserve_lae": str(getattr(c, "case_reserve_lae", 0)),
                "total_incurred": str(getattr(c, "total_incurred", 0)),
                "claim_report_date": c.claim_report_date.isoformat()
                if getattr(c, "claim_report_date", None)
                else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            },
        }

    @router.patch(
        "/claims/{claim_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Update a claim",
    )
    def update_claim(request: HttpRequest, claim_id: int) -> tuple[int, dict[str, Any]]:
        _require_role(request, OPERATIONS_ROLES, "update_claim")
        import json as _json
        from claims.models import Claim

        try:
            c = Claim.objects.get(pk=claim_id)
        except Claim.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        body = _json.loads(request.body) if request.body else {}
        for field in ("status", "admin_notes", "loss_state"):
            if field in body:
                setattr(c, field, body[field])
        c.save()
        return 200, {
            "success": True,
            "message": "Claim updated",
            "data": {"id": c.id, "status": c.status},
        }

    # ═══════════════════════════════════════════════════════════════════
    # Internal Documents
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/internal-documents",
        auth=JWTAuth(),
        response={200: dict},
        summary="List internal documents (paginated)",
    )
    def list_internal_documents(
        request: HttpRequest,
        page: int = 1,
        claim: int = 0,
        status: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of internal documents for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_internal_documents")
        from claims.models import ClaimDocument as InternalDocument

        qs = InternalDocument.objects.all()
        if claim:
            qs = qs.filter(claim_id=claim)

        allowed = {"created_at", "-created_at"}
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": d.id,
                "claim": d.claim_id,
                "claim_number": getattr(d.claim, "claim_number", "")
                if d.claim_id
                else "",
                "document_type": getattr(d, "file_type", ""),
                "status": "uploaded",
                "original_filename": d.original_filename,
                "s3_key": getattr(d, "s3_key", ""),
                "s3_url": getattr(d, "s3_url", ""),
                "file_size": getattr(d, "file_size", 0),
                "mime_type": getattr(d, "mime_type", ""),
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in items
        ]

        return 200, {
            "success": True,
            "message": "Internal documents list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.patch(
        "/internal-documents/{doc_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Update an internal document",
    )
    def update_internal_document(
        request: HttpRequest, doc_id: int
    ) -> tuple[int, dict[str, Any]]:
        _require_role(request, OPERATIONS_ROLES, "update_internal_document")
        import json as _json
        from claims.models import ClaimDocument

        try:
            d = ClaimDocument.objects.get(pk=doc_id)
        except ClaimDocument.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        body = _json.loads(request.body) if request.body else {}
        for field in ("file_type", "original_filename"):
            if field in body:
                setattr(d, field, body[field])
        d.save()
        return 200, {
            "success": True,
            "message": "Document updated",
            "data": {"id": d.id},
        }

    # ═══════════════════════════════════════════════════════════════════
    # Claim Documents
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/claim-documents",
        auth=JWTAuth(),
        response={200: dict},
        summary="List claim documents",
    )
    def list_claim_documents(
        request: HttpRequest,
        claim: int = 0,
        page: int = 1,
    ) -> tuple[int, dict[str, Any]]:
        _require_role(request, ALL_STAFF_ROLES, "list_claim_documents")
        from claims.models import ClaimDocument as InternalDocument

        qs = InternalDocument.objects.all()
        if claim:
            qs = qs.filter(claim_id=claim)
        qs = qs.order_by("-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": d.id,
                "claim": d.claim_id,
                "document_type": getattr(d, "file_type", ""),
                "status": "uploaded",
                "original_filename": d.original_filename,
                "s3_url": getattr(d, "s3_url", ""),
                "file_size": getattr(d, "file_size", 0),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in items
        ]

        return 200, {
            "success": True,
            "message": "Claim documents",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Brokered Requests
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/brokered-requests",
        auth=JWTAuth(),
        response={200: dict},
        summary="List brokered requests (paginated)",
    )
    def list_brokered_requests(
        request: HttpRequest,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of brokered quote requests for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_brokered_requests")
        from brokered.models import BrokeredQuoteRequest

        qs = BrokeredQuoteRequest.objects.select_related(
            "quote", "quote__company"
        ).all()
        if search:
            qs = qs.filter(
                Q(company_name__icontains=search) | Q(requester_email__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)

        # Role-scoped filtering (brokers only see brokered requests for their quotes)
        qs = _scope_queryset_by_role(qs, request.auth, "brokered_requests")

        allowed = {
            "created_at",
            "-created_at",
            "status",
            "-status",
            "company_name",
            "-company_name",
        }
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = min(page_size, 100)
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = []
        for r in items:
            results.append(
                {
                    "id": r.id,
                    "company_name": r.company_name,
                    "status": r.status,
                    "status_display": getattr(
                        r, "get_status_display", lambda: r.status
                    )(),
                    "coverage_types": getattr(r, "coverage_types", []),
                    "coverage_type_display": getattr(r, "coverage_type_display", ""),
                    "carrier": getattr(r, "carrier", ""),
                    "carrier_display": getattr(
                        r, "get_carrier_display", lambda: getattr(r, "carrier", "")
                    )(),
                    "requested_coverage_detail": getattr(
                        r, "requested_coverage_detail", ""
                    ),
                    "aggregate_limit": str(getattr(r, "aggregate_limit", "")),
                    "per_occurrence_limit": str(getattr(r, "per_occurrence_limit", "")),
                    "retention": str(getattr(r, "retention", "")),
                    "additional_notes": getattr(r, "additional_notes", ""),
                    "requester": getattr(r, "requester_id", None),
                    "requester_name": getattr(r, "requester_name", ""),
                    "requester_email": getattr(r, "requester_email", ""),
                    "quote": getattr(r, "quote_id", None),
                    "premium_amount": str(getattr(r, "premium_amount", ""))
                    if getattr(r, "premium_amount", None)
                    else None,
                    "is_bound": getattr(r, "is_bound", False),
                    "notes": getattr(r, "notes", ""),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
            )

        return 200, {
            "success": True,
            "message": "Brokered requests list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.get(
        "/brokered-requests/{request_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Get a single brokered request",
    )
    def get_brokered_request(
        request: HttpRequest, request_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Retrieve a single brokered request by ID."""
        _require_role(request, ALL_STAFF_ROLES, "view_brokered_request")
        from brokered.models import BrokeredQuoteRequest

        try:
            r = BrokeredQuoteRequest.objects.get(pk=request_id)
        except BrokeredQuoteRequest.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        data = {
            "id": r.id,
            "company_name": r.company_name,
            "status": r.status,
            "coverage_types": getattr(r, "coverage_types", []),
            "carrier": getattr(r, "carrier", ""),
            "requester": getattr(r, "requester_id", None),
            "requester_email": getattr(r, "requester_email", ""),
            "quote": getattr(r, "quote_id", None),
            "premium_amount": str(getattr(r, "premium_amount", ""))
            if getattr(r, "premium_amount", None)
            else None,
            "notes": getattr(r, "notes", ""),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        return 200, {"success": True, "message": "Brokered request", "data": data}

    @router.post(
        "/brokered-requests",
        auth=JWTAuth(),
        response={200: dict, 400: dict},
        summary="Create a brokered request",
    )
    def create_brokered_request(
        request: HttpRequest, payload: dict
    ) -> tuple[int, dict[str, Any]]:
        """Create a new brokered quote request."""
        _require_role(request, ALL_STAFF_ROLES, "create_brokered_request")
        from brokered.models import BrokeredQuoteRequest

        data = payload if isinstance(payload, dict) else {}
        WRITABLE = [
            "company_name",
            "coverage_types",
            "carrier",
            "requested_coverage_detail",
            "aggregate_limit",
            "per_occurrence_limit",
            "retention",
            "blocker_type",
            "blocker_detail",
            "requester_email",
            "client_email",
            "client_contact_url",
            "django_admin_url",
            "notes",
            "additional_notes",
            "decline_reason",
            "missing_docs_note",
            "is_bound",
            "custom_product_created",
            "docs_uploaded",
            "stripe_confirmed",
        ]
        try:
            kwargs = {f: data[f] for f in WRITABLE if f in data}
            kwargs.setdefault("status", "received")
            if "premium_amount" in data:
                kwargs["premium_amount"] = (
                    float(data["premium_amount"]) if data["premium_amount"] else None
                )
            r = BrokeredQuoteRequest.objects.create(**kwargs)
            return 200, {
                "success": True,
                "message": "Brokered request created",
                "data": {"id": r.id},
            }
        except Exception as e:
            return 400, {"success": False, "message": str(e), "data": None}

    @router.patch(
        "/brokered-requests/{request_id}",
        auth=JWTAuth(),
        response={200: dict, 400: dict, 404: dict},
        summary="Update a brokered request",
    )
    def update_brokered_request(
        request: HttpRequest, request_id: int, payload: dict
    ) -> tuple[int, dict[str, Any]]:
        """Partially update a brokered quote request."""
        _require_role(request, ALL_STAFF_ROLES, "update_brokered_request")
        from brokered.models import BrokeredQuoteRequest

        try:
            r = BrokeredQuoteRequest.objects.get(pk=request_id)
        except BrokeredQuoteRequest.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}
        data = payload if isinstance(payload, dict) else {}
        UPDATABLE = [
            "company_name",
            "status",
            "coverage_types",
            "carrier",
            "requested_coverage_detail",
            "aggregate_limit",
            "per_occurrence_limit",
            "retention",
            "blocker_type",
            "blocker_detail",
            "requester_email",
            "client_email",
            "client_contact_url",
            "django_admin_url",
            "notes",
            "additional_notes",
            "decline_reason",
            "missing_docs_note",
            "is_bound",
            "custom_product_created",
            "docs_uploaded",
            "stripe_confirmed",
        ]
        for field in UPDATABLE:
            if field in data:
                setattr(r, field, data[field])
        if "premium_amount" in data:
            r.premium_amount = (
                float(data["premium_amount"]) if data["premium_amount"] else None
            )
        try:
            r.save()
            return 200, {
                "success": True,
                "message": "Brokered request updated",
                "data": {"id": r.id},
            }
        except Exception as e:
            return 400, {"success": False, "message": str(e), "data": None}

    # ═══════════════════════════════════════════════════════════════════
    # Quotes
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/quotes",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all quotes (paginated)",
    )
    def list_quotes(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        status: str = "",
        ordering: str = "-created_at",
        include_deleted: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all quotes for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_quotes")
        from quotes.models import Quote

        manager = Quote.all_objects if include_deleted else Quote.objects
        qs = manager.select_related(
            "company", "user", "organization", "referral_partner"
        ).all()
        if search:
            qs = qs.filter(
                Q(quote_number__icontains=search)
                | Q(company__entity_legal_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)

        # Role-scoped filtering (brokers only see their referral partner quotes)
        qs = _scope_queryset_by_role(qs, request.auth, "quotes")

        allowed = {
            "created_at",
            "-created_at",
            "status",
            "-status",
            "quote_number",
            "-quote_number",
        }
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": q.id,
                "quote_number": q.quote_number,
                "company": q.company_id,
                "company_detail": {
                    "id": q.company.id,
                    "entity_legal_name": q.company.entity_legal_name,
                }
                if q.company
                else None,
                "user": q.user_id,
                "organization": getattr(q, "organization_id", None),
                "status": q.status,
                "quote_amount": str(q.quote_amount) if q.quote_amount else "0",
                "quoted_at": q.quoted_at.isoformat()
                if getattr(q, "quoted_at", None)
                else None,
                "billing_frequency": getattr(q, "billing_frequency", ""),
                "current_step": getattr(q, "current_step", ""),
                "coverages": getattr(q, "coverages", None),
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "updated_at": q.updated_at.isoformat() if q.updated_at else None,
            }
            for q in items
        ]

        return 200, {
            "success": True,
            "message": "Quotes list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.get(
        "/quotes/{quote_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Get a single quote",
    )
    def get_quote_detail(
        request: HttpRequest, quote_id: int
    ) -> tuple[int, dict[str, Any]]:
        """Retrieve a single quote by ID."""
        _require_role(request, ALL_STAFF_ROLES, "view_quote_detail")
        from quotes.models import Quote

        try:
            q = Quote.objects.select_related("company").get(pk=quote_id)
        except Quote.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        return 200, {
            "success": True,
            "message": "Quote detail",
            "data": {
                "id": q.id,
                "quote_number": q.quote_number,
                "company": q.company_id,
                "company_detail": {
                    "id": q.company.id,
                    "entity_legal_name": q.company.entity_legal_name,
                }
                if q.company
                else None,
                "user": q.user_id,
                "organization": getattr(q, "organization_id", None),
                "status": q.status,
                "quote_amount": str(q.quote_amount) if q.quote_amount else "0",
                "quoted_at": q.quoted_at.isoformat()
                if getattr(q, "quoted_at", None)
                else None,
                "billing_frequency": getattr(q, "billing_frequency", ""),
                "current_step": getattr(q, "current_step", ""),
                "coverages": getattr(q, "coverages", None),
                "coverage_data": getattr(q, "coverage_data", None),
                "limits_retentions": getattr(q, "limits_retentions", None),
                "rating_result": getattr(q, "rating_result", None),
                "form_data_snapshot": getattr(q, "form_data_snapshot", None),
                "referral_partner": getattr(q, "referral_partner", ""),
                "promo_code": getattr(q, "promo_code", ""),
                "created_at": q.created_at.isoformat() if q.created_at else None,
                "updated_at": q.updated_at.isoformat() if q.updated_at else None,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Policies
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/policies",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all policies (paginated)",
    )
    def list_policies(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        status: str = "",
        quote: int = 0,
        ordering: str = "-created_at",
        include_deleted: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all policies for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_policies")
        from policies.models import Policy

        manager = Policy.all_objects if include_deleted else Policy.objects
        qs = manager.select_related("quote", "quote__company").all()
        if search:
            qs = qs.filter(
                Q(policy_number__icontains=search)
                | Q(insured_legal_name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if quote:
            qs = qs.filter(quote_id=quote)

        # Role-scoped filtering (brokers only see policies from their referred quotes)
        qs = _scope_queryset_by_role(qs, request.auth, "policies")

        allowed = {
            "created_at",
            "-created_at",
            "status",
            "-status",
            "policy_number",
            "-policy_number",
        }
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": p.id,
                "policy_number": p.policy_number,
                "quote": getattr(p, "quote_id", None),
                "coverage_type": getattr(p, "coverage_type", ""),
                "carrier": getattr(p, "carrier", ""),
                "is_brokered": getattr(p, "is_brokered", False),
                "premium": str(p.premium) if p.premium else "0",
                "monthly_premium": str(getattr(p, "monthly_premium", 0)),
                "billing_frequency": getattr(p, "billing_frequency", ""),
                "coi_number": getattr(p, "coi_number", ""),
                "insured_fein": getattr(p, "insured_fein", ""),
                "insured_legal_name": getattr(p, "insured_legal_name", ""),
                "principal_state": getattr(p, "principal_state", ""),
                "effective_date": p.effective_date.isoformat()
                if getattr(p, "effective_date", None)
                else None,
                "expiration_date": p.expiration_date.isoformat()
                if getattr(p, "expiration_date", None)
                else None,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in items
        ]

        return 200, {
            "success": True,
            "message": "Policies list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    @router.get(
        "/policies/{policy_id}",
        auth=JWTAuth(),
        response={200: dict, 404: dict},
        summary="Get a single policy",
    )
    def get_policy_detail(
        request: HttpRequest, policy_id: int
    ) -> tuple[int, dict[str, Any]]:
        _require_role(request, ALL_STAFF_ROLES, "view_policy_detail")
        from policies.models import Policy

        try:
            p = Policy.objects.get(pk=policy_id)
        except Policy.DoesNotExist:
            return 404, {"success": False, "message": "Not found", "data": None}

        return 200, {
            "success": True,
            "message": "Policy detail",
            "data": {
                "id": p.id,
                "policy_number": p.policy_number,
                "quote": getattr(p, "quote_id", None),
                "coverage_type": getattr(p, "coverage_type", ""),
                "carrier": getattr(p, "carrier", ""),
                "is_brokered": getattr(p, "is_brokered", False),
                "premium": str(p.premium) if p.premium else "0",
                "monthly_premium": str(getattr(p, "monthly_premium", 0)),
                "billing_frequency": getattr(p, "billing_frequency", ""),
                "limits_retentions": getattr(p, "limits_retentions", None),
                "coi_number": getattr(p, "coi_number", ""),
                "insured_fein": getattr(p, "insured_fein", ""),
                "insured_legal_name": getattr(p, "insured_legal_name", ""),
                "principal_state": getattr(p, "principal_state", ""),
                "purchased_at": p.purchased_at.isoformat()
                if getattr(p, "purchased_at", None)
                else None,
                "paid_to_date": p.paid_to_date.isoformat()
                if getattr(p, "paid_to_date", None)
                else None,
                "effective_date": p.effective_date.isoformat()
                if getattr(p, "effective_date", None)
                else None,
                "expiration_date": p.expiration_date.isoformat()
                if getattr(p, "expiration_date", None)
                else None,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Payments
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/payments",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all payments (paginated)",
    )
    def list_payments(
        request: HttpRequest,
        page: int = 1,
        page_size: int = 25,
        policy: int = 0,
        status: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all payments for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_payments")
        from policies.models import Payment

        qs = Payment.objects.select_related("policy").all()
        if policy:
            qs = qs.filter(policy_id=policy)
        if status:
            qs = qs.filter(status=status)

        allowed = {
            "created_at",
            "-created_at",
            "status",
            "-status",
            "amount",
            "-amount",
        }
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = min(page_size, 100)
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": p.id,
                "policy": p.policy_id,
                "policy_number": p.policy.policy_number if p.policy else "",
                "stripe_invoice_id": getattr(p, "stripe_invoice_id", ""),
                "amount": str(p.amount) if p.amount else "0",
                "status": p.status,
                "paid_at": p.paid_at.isoformat()
                if getattr(p, "paid_at", None)
                else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in items
        ]

        return 200, {
            "success": True,
            "message": "Payments list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Certificates
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/certificates",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all certificates (paginated)",
    )
    def list_certificates(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all certificates for admin dashboard."""
        _require_role(request, ALL_STAFF_ROLES, "list_certificates")
        from certificates.models import CustomCertificate

        qs = CustomCertificate.objects.all()
        if search:
            qs = qs.filter(
                Q(holder_name__icontains=search) | Q(coi_number__icontains=search)
            )

        allowed = {"created_at", "-created_at", "holder_name", "-holder_name"}
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": c.id,
                "user": c.user_id,
                "organization": getattr(c, "organization_id", None),
                "coi_number": c.coi_number,
                "custom_coi_number": getattr(c, "custom_coi_number", ""),
                "holder_name": c.holder_name,
                "holder_city": getattr(c, "holder_city", ""),
                "holder_state": getattr(c, "holder_state", ""),
                "is_additional_insured": getattr(c, "is_additional_insured", False),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in items
        ]

        return 200, {
            "success": True,
            "message": "Certificates list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Producers
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/producers",
        auth=JWTAuth(),
        response={200: dict},
        summary="List all producers (paginated)",
    )
    def list_producers(
        request: HttpRequest,
        page: int = 1,
        search: str = "",
        producer_type: str = "",
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        """Paginated list of all producers for admin dashboard."""
        _require_role(request, FINANCE_ROLES, "list_producers")
        from producers.models import Producer

        qs = Producer.objects.all()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
        if producer_type:
            qs = qs.filter(producer_type=producer_type)

        allowed = {"created_at", "-created_at", "name", "-name"}
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": p.id,
                "name": p.name,
                "producer_type": p.producer_type,
                "email": p.email,
                "license_number": getattr(p, "license_number", ""),
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in items
        ]

        return 200, {
            "success": True,
            "message": "Producers list",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }

    # ═══════════════════════════════════════════════════════════════════
    # Policy Transactions
    # ═══════════════════════════════════════════════════════════════════

    @router.get(
        "/policy-transactions",
        auth=JWTAuth(),
        response={200: dict},
        summary="List policy transactions (paginated)",
    )
    def list_policy_transactions(
        request: HttpRequest,
        page: int = 1,
        policy: int = 0,
        ordering: str = "-created_at",
    ) -> tuple[int, dict[str, Any]]:
        _require_role(request, ALL_STAFF_ROLES, "list_policy_transactions")
        from policies.models import PolicyTransaction

        qs = PolicyTransaction.objects.all()
        if policy:
            qs = qs.filter(policy_id=policy)

        allowed = {"created_at", "-created_at"}
        qs = qs.order_by(ordering if ordering in allowed else "-created_at")

        total = qs.count()
        page_size = 25
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]

        results = [
            {
                "id": t.id,
                "policy": t.policy_id,
                "transaction_type": getattr(t, "transaction_type", ""),
                "amount": str(t.amount) if getattr(t, "amount", None) else "0",
                "description": getattr(t, "description", ""),
                "effective_date": t.effective_date.isoformat()
                if getattr(t, "effective_date", None)
                else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ]

        return 200, {
            "success": True,
            "message": "Policy transactions",
            "data": {
                "count": total,
                "next": f"?page={page + 1}" if offset + page_size < total else None,
                "previous": f"?page={page - 1}" if page > 1 else None,
                "results": results,
            },
        }
