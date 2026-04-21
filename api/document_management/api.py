"""
Document Management API endpoints.

Provides folder CRUD and document-in-folder listing for the portal,
plus tokenized share-link management for claims and certificates.
"""

import secrets
from datetime import timedelta
from typing import Any, Optional

from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from ninja import Router, Schema

from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Documents"])

# Default lifetime for a share link when none is supplied.
DEFAULT_SHARE_EXPIRES_DAYS = 7
# Max lifetime cap (prevent runaway tokens).
MAX_SHARE_EXPIRES_DAYS = 90


class CreateFolderSchema(Schema):
    name: str
    parent_id: Optional[int] = None
    description: str = ""
    color: str = ""


@router.get("/folders", auth=JWTAuth(), response={200: ApiResponseSchema})
def list_folders(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all document folders for the current organization."""
    from organizations.service import OrganizationService
    from document_management.models import DocumentFolder

    org_id = OrganizationService.get_active_org_id(request.auth)
    folders = (
        DocumentFolder.objects.filter(
            organization_id=org_id,
        )
        .select_related("parent")
        .prefetch_related("items__document")
    )

    def serialize_folder(f):
        return {
            "id": f.pk,
            "name": f.name,
            "description": f.description,
            "color": f.color,
            "parent_id": f.parent_id,
            "full_path": f.full_path,
            "document_count": f.items.count(),
            "child_count": f.children.count(),
            "created_at": f.created_at.isoformat(),
        }

    return 200, {
        "success": True,
        "message": "Folders retrieved successfully",
        "data": [serialize_folder(f) for f in folders],
    }


@router.post(
    "/folders",
    auth=JWTAuth(),
    response={201: ApiResponseSchema, 400: ApiResponseSchema},
)
def create_folder(
    request: HttpRequest, payload: CreateFolderSchema
) -> tuple[int, dict[str, Any]]:
    """Create a new document folder."""
    from organizations.service import OrganizationService
    from document_management.models import DocumentFolder

    if not payload.name.strip():
        return 400, {
            "success": False,
            "message": "Folder name is required",
            "data": None,
        }

    org_id = OrganizationService.get_active_org_id(request.auth)

    # Validate parent belongs to same org
    parent = None
    if payload.parent_id:
        try:
            parent = DocumentFolder.objects.get(
                pk=payload.parent_id, organization_id=org_id
            )
        except DocumentFolder.DoesNotExist:
            return 400, {
                "success": False,
                "message": "Parent folder not found",
                "data": None,
            }

    folder = DocumentFolder.objects.create(
        organization_id=org_id,
        name=payload.name.strip(),
        parent=parent,
        description=payload.description,
        color=payload.color,
        created_by=request.auth,
    )

    return 201, {
        "success": True,
        "message": "Folder created successfully",
        "data": {
            "id": folder.pk,
            "name": folder.name,
            "full_path": folder.full_path,
        },
    }


@router.get(
    "/folders/{folder_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def get_folder(request: HttpRequest, folder_id: int) -> tuple[int, dict[str, Any]]:
    """Get folder details and its documents."""
    from organizations.service import OrganizationService
    from document_management.models import DocumentFolder
    from s3.service import DocumentStorage

    org_id = OrganizationService.get_active_org_id(request.auth)
    try:
        folder = DocumentFolder.objects.get(pk=folder_id, organization_id=org_id)
    except DocumentFolder.DoesNotExist:
        return 404, {"success": False, "message": "Folder not found", "data": None}

    storage = DocumentStorage()
    items = []
    for item in folder.items.select_related("document").order_by("-created_at"):
        doc = item.document
        download_url = None
        try:
            download_url = storage.get_download_url(
                doc.s3_key, filename=doc.original_filename
            )
        except Exception:
            download_url = doc.s3_url

        items.append(
            {
                "id": doc.pk,
                "item_id": item.pk,
                "title": doc.title,
                "category": doc.category,
                "original_filename": doc.original_filename,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "download_url": download_url,
                "created_at": doc.created_at.isoformat(),
            }
        )

    children = [
        {"id": c.pk, "name": c.name, "document_count": c.items.count()}
        for c in folder.children.all()
    ]

    return 200, {
        "success": True,
        "message": "Folder retrieved successfully",
        "data": {
            "id": folder.pk,
            "name": folder.name,
            "description": folder.description,
            "color": folder.color,
            "full_path": folder.full_path,
            "parent_id": folder.parent_id,
            "children": children,
            "documents": items,
        },
    }


@router.delete(
    "/folders/{folder_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def delete_folder(request: HttpRequest, folder_id: int) -> tuple[int, dict[str, Any]]:
    """Delete an empty folder."""
    from organizations.service import OrganizationService
    from document_management.models import DocumentFolder

    org_id = OrganizationService.get_active_org_id(request.auth)
    try:
        folder = DocumentFolder.objects.get(pk=folder_id, organization_id=org_id)
    except DocumentFolder.DoesNotExist:
        return 404, {"success": False, "message": "Folder not found", "data": None}

    if folder.items.exists() or folder.children.exists():
        return 400, {
            "success": False,
            "message": "Cannot delete a non-empty folder",
            "data": None,
        }

    folder.delete()
    return 200, {"success": True, "message": "Folder deleted", "data": None}


# ─── Share Links (5.2) ───────────────────────────────────────────────────────


class CreateShareLinkSchema(Schema):
    resource_type: str  # 'certificate' or 'claim'
    resource_id: int
    expires_in_days: int = DEFAULT_SHARE_EXPIRES_DAYS


def _resolve_share_resource(resource_type: str, resource_id: int, user=None):
    """Resolve (resource, s3_key, filename) for a share resource.

    If ``user`` is provided, verifies the user owns/can manage the resource.
    Returns ``(None, None, None)`` when the resource does not exist or
    ownership fails.
    """
    if resource_type == "certificate":
        from certificates.models import CustomCertificate

        qs = CustomCertificate.objects.select_related("document")
        if user is not None:
            from organizations.service import OrganizationService

            org_id = OrganizationService.get_active_org_id(user)
            qs = qs.filter(organization_id=org_id)
        cert = qs.filter(pk=resource_id).first()
        if cert is None or cert.document is None:
            return None, None, None
        doc = cert.document
        return cert, doc.s3_key, doc.original_filename

    if resource_type == "claim":
        from claims.models import ClaimDocument

        qs = ClaimDocument.objects.select_related("claim")
        if user is not None:
            from organizations.service import OrganizationService

            org_id = OrganizationService.get_active_org_id(user)
            qs = qs.filter(claim__organization_id=org_id)
        doc = qs.filter(pk=resource_id).first()
        if doc is None:
            return None, None, None
        return doc, doc.s3_key, doc.original_filename

    return None, None, None


@router.post(
    "/share-links",
    auth=JWTAuth(),
    response={201: ApiResponseSchema, 400: ApiResponseSchema, 404: ApiResponseSchema},
)
def create_share_link(
    request: HttpRequest, payload: CreateShareLinkSchema
) -> tuple[int, dict[str, Any]]:
    """Create a tokenized share link for a claim document or certificate.

    The caller must own the resource (belong to the same organization).
    """
    from document_management.models import ShareLink

    resource_type = (payload.resource_type or "").strip().lower()
    if resource_type not in {"certificate", "claim"}:
        return 400, {
            "success": False,
            "message": "resource_type must be 'certificate' or 'claim'",
            "data": None,
        }

    days = payload.expires_in_days or DEFAULT_SHARE_EXPIRES_DAYS
    if days <= 0 or days > MAX_SHARE_EXPIRES_DAYS:
        return 400, {
            "success": False,
            "message": f"expires_in_days must be between 1 and {MAX_SHARE_EXPIRES_DAYS}",
            "data": None,
        }

    resource, _s3_key, _filename = _resolve_share_resource(
        resource_type, payload.resource_id, user=request.auth
    )
    if resource is None:
        return 404, {
            "success": False,
            "message": "Resource not found or access denied",
            "data": None,
        }

    # token_urlsafe(48) yields ~64 URL-safe chars
    token = secrets.token_urlsafe(48)[:64]
    expires_at = timezone.now() + timedelta(days=days)

    link = ShareLink.objects.create(
        token=token,
        resource_type=resource_type,
        resource_id=payload.resource_id,
        expires_at=expires_at,
        created_by=request.auth,
    )

    return 201, {
        "success": True,
        "message": "Share link created",
        "data": {
            "id": link.pk,
            "token": link.token,
            "resource_type": link.resource_type,
            "resource_id": link.resource_id,
            "expires_at": link.expires_at.isoformat(),
            "share_url": f"/share/{link.token}",
            "created_at": link.created_at.isoformat(),
        },
    }


@router.delete(
    "/share-links/{link_id}",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def revoke_share_link(request: HttpRequest, link_id: int) -> tuple[int, dict[str, Any]]:
    """Revoke a share link owned by the current user."""
    from document_management.models import ShareLink

    link = ShareLink.objects.filter(pk=link_id, created_by=request.auth).first()
    if link is None:
        return 404, {
            "success": False,
            "message": "Share link not found",
            "data": None,
        }

    if link.revoked_at is None:
        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at", "updated_at"])

    return 200, {
        "success": True,
        "message": "Share link revoked",
        "data": {"id": link.pk, "revoked_at": link.revoked_at.isoformat()},
    }


def public_share_view(request: HttpRequest, token: str):
    """Public (NO auth) share resolver.

    Resolves the token to a resource, generates a short-lived S3
    signed URL and redirects the caller to it. Returns:
      - 404 when the token is unknown or the underlying resource is gone
      - 410 when the link has been revoked or has expired
    """
    from document_management.models import ShareLink
    from s3.service import S3Service

    link = ShareLink.objects.filter(token=token).first()
    if link is None:
        return JsonResponse(
            {"success": False, "message": "Share link not found", "data": None},
            status=404,
        )

    if link.revoked_at is not None:
        return JsonResponse(
            {"success": False, "message": "Share link has been revoked", "data": None},
            status=410,
        )

    if link.expires_at <= timezone.now():
        return JsonResponse(
            {"success": False, "message": "Share link has expired", "data": None},
            status=410,
        )

    resource, s3_key, filename = _resolve_share_resource(
        link.resource_type, link.resource_id, user=None
    )
    if resource is None or not s3_key:
        return JsonResponse(
            {
                "success": False,
                "message": "Shared document is unavailable",
                "data": None,
            },
            status=404,
        )

    signed_url = S3Service.generate_presigned_url(s3_key, expiration=300)
    if not signed_url:
        return JsonResponse(
            {
                "success": False,
                "message": "Unable to generate download URL",
                "data": None,
            },
            status=500,
        )

    # Allow ?json=1 callers (e.g. the portal SSR page) to fetch metadata.
    if request.GET.get("json") in {"1", "true"}:
        return JsonResponse(
            {
                "success": True,
                "message": "Share link resolved",
                "data": {
                    "resource_type": link.resource_type,
                    "resource_id": link.resource_id,
                    "filename": filename or "document",
                    "download_url": signed_url,
                    "expires_at": link.expires_at.isoformat(),
                },
            },
            status=200,
        )

    return HttpResponseRedirect(signed_url)
