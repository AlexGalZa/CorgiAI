"""
Demo scheduling + attendance tracking API.

Public intake for prospective customers to book a demo with an AE, plus
authenticated endpoints for AEs/admins to list and update attendance.
"""

from datetime import timedelta
from typing import Any, Optional

from django.db.models import Q
from django.http import HttpRequest
from ninja import Router

from common.schemas import ApiResponseSchema
from demos.models import Demo
from demos.schemas import DemoAttendanceSchema, DemoCreateSchema, DemoResponseSchema
from producers.models import Producer
from users.auth import JWTAuth

router = Router(tags=["Demos"])


ALLOWED_STATUSES = {"scheduled", "held", "no_show", "cancelled"}
AE_OR_ADMIN_ROLES = {"admin", "ae"}


def _serialize(demo: Demo) -> dict:
    return DemoResponseSchema(
        id=demo.id,
        customer_email=demo.customer_email,
        customer_name=demo.customer_name,
        ae_id=demo.ae_id,
        ae_name=demo.ae.name if demo.ae_id else None,
        scheduled_for=demo.scheduled_for,
        duration_minutes=demo.duration_minutes,
        status=demo.status,
        join_url=demo.join_url,
        recording_url=demo.recording_url,
        notes=demo.notes,
    ).dict()


@router.post(
    "",
    response={
        201: ApiResponseSchema,
        400: ApiResponseSchema,
        409: ApiResponseSchema,
    },
)
def create_demo(
    request: HttpRequest, data: DemoCreateSchema
) -> tuple[int, dict[str, Any]]:
    """Public intake — book a demo with an AE.

    If ``ae_id`` is not provided, an active AE is auto-assigned. Validates that
    the selected AE does not already have a demo scheduled within the requested
    time window (scheduled_for to scheduled_for + duration).
    """
    duration = data.duration_minutes or 30
    start = data.preferred_time
    end = start + timedelta(minutes=duration)

    if data.ae_id:
        ae = Producer.objects.filter(
            id=data.ae_id, producer_type="ae", is_active=True
        ).first()
        if not ae:
            return 400, {
                "success": False,
                "message": "Invalid or inactive AE",
            }
    else:
        ae = (
            Producer.objects.filter(producer_type="ae", is_active=True)
            .order_by("id")
            .first()
        )
        if not ae:
            return 400, {
                "success": False,
                "message": "No AEs available to host a demo",
            }

    overlap = Demo.objects.filter(
        ae=ae,
        status="scheduled",
        scheduled_for__lt=end,
    ).filter(Q(scheduled_for__gte=start) | Q(scheduled_for__lt=start))

    has_conflict = False
    for existing in overlap:
        existing_end = existing.scheduled_for + timedelta(
            minutes=existing.duration_minutes
        )
        if existing.scheduled_for < end and existing_end > start:
            has_conflict = True
            break

    if has_conflict:
        return 409, {
            "success": False,
            "message": "AE's calendar has a conflict at the requested time",
        }

    demo = Demo.objects.create(
        customer_email=data.customer_email,
        customer_name=data.customer_name,
        ae=ae,
        scheduled_for=start,
        duration_minutes=duration,
    )

    return 201, {
        "success": True,
        "message": "Demo scheduled",
        "data": _serialize(demo),
    }


@router.patch(
    "/{demo_id}/attendance",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
        404: ApiResponseSchema,
    },
)
def update_attendance(
    request: HttpRequest, demo_id: int, data: DemoAttendanceSchema
) -> tuple[int, dict[str, Any]]:
    """Update a demo's status + notes after it is held (AE/admin only)."""
    user = request.auth
    if getattr(user, "role", None) not in AE_OR_ADMIN_ROLES:
        return 403, {
            "success": False,
            "message": "Only AEs or admins can update demo attendance",
        }

    if data.status not in ALLOWED_STATUSES:
        return 400, {
            "success": False,
            "message": f"Invalid status. Must be one of {sorted(ALLOWED_STATUSES)}",
        }

    demo = Demo.objects.filter(id=demo_id).first()
    if not demo:
        return 404, {"success": False, "message": "Demo not found"}

    demo.status = data.status
    if data.notes is not None:
        demo.notes = data.notes
    if data.recording_url is not None:
        demo.recording_url = data.recording_url
    demo.save(update_fields=["status", "notes", "recording_url", "updated_at"])

    return 200, {
        "success": True,
        "message": "Attendance updated",
        "data": _serialize(demo),
    }


@router.get(
    "",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 403: ApiResponseSchema},
)
def list_demos(
    request: HttpRequest, status: Optional[str] = None
) -> tuple[int, dict[str, Any]]:
    """List demos. AEs see only their own; admins see all."""
    user = request.auth
    role = getattr(user, "role", None)
    if role not in AE_OR_ADMIN_ROLES:
        return 403, {
            "success": False,
            "message": "Not authorized to list demos",
        }

    qs = Demo.objects.select_related("ae").all()

    if role == "ae":
        ae = Producer.objects.filter(email=user.email, producer_type="ae").first()
        if not ae:
            return 200, {"success": True, "message": "No demos", "data": []}
        qs = qs.filter(ae=ae)

    if status:
        qs = qs.filter(status=status)

    data = [_serialize(d) for d in qs]
    return 200, {"success": True, "message": "Demos retrieved", "data": data}
