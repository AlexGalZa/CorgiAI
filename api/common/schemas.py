from typing import Optional, Any
from ninja import Schema
from datetime import date
from pydantic import BeforeValidator
from typing import Annotated


class ApiResponseSchema(Schema):
    success: bool
    message: str
    data: Optional[Any] = None


FrontendDate = Annotated[
    date,
    BeforeValidator(
        lambda v: v.split("T")[0] if isinstance(v, str) and "T" in v else v
    ),
]
