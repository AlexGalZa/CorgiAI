from datetime import datetime
from typing import Optional

from ninja import Schema


class DemoCreateSchema(Schema):
    customer_email: str
    customer_name: str
    preferred_time: datetime
    ae_id: Optional[int] = None
    duration_minutes: Optional[int] = 30


class DemoAttendanceSchema(Schema):
    status: str
    notes: Optional[str] = None
    recording_url: Optional[str] = None


class DemoResponseSchema(Schema):
    id: int
    customer_email: str
    customer_name: str
    ae_id: int
    ae_name: Optional[str] = None
    scheduled_for: datetime
    duration_minutes: int
    status: str
    join_url: str
    recording_url: str
    notes: str
