from datetime import date
from decimal import Decimal
from pydantic import BaseModel, computed_field, field_validator

from common.utils import parse_date


class DOQuestionnaire(BaseModel):
    is_publicly_traded: bool
    public_offering_details: str | None = None
    has_mergers_acquisitions: bool
    mergers_acquisitions_details: str | None = None
    board_size: int
    independent_directors: int
    director_names: str
    has_board_meetings: bool
    funding_raised: Decimal
    funding_date: date | None = None
    has_financial_audits: bool
    has_legal_compliance_officer: bool
    is_profitable: bool
    has_indebtedness: bool
    has_breached_loan_covenants: bool | None = None

    @field_validator("funding_date", mode="before")
    @classmethod
    def parse_funding_date(cls, v):
        if v is None:
            return None
        return parse_date(v)

    @computed_field
    @property
    def independent_board_ratio(self) -> float:
        if self.board_size == 0:
            return 0.0
        return self.independent_directors / self.board_size
