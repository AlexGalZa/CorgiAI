from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Any

from pydantic import BaseModel


@dataclass
class LimitOption:
    value: int
    factor: float = 1.0


@dataclass
class RetentionOption:
    value: int
    factor: float = 1.0


@dataclass
class LimitRetentionConfig:
    aggregate_limits: list[LimitOption]
    per_occurrence_limits: list[LimitOption]
    retentions: list[RetentionOption]


@dataclass
class BaseRateEntry:
    key: str
    rate: float
    minimum_premium: Decimal = Decimal("0")


@dataclass
class BaseRateTable:
    entries: dict[str, BaseRateEntry]

    def get(self, key: str) -> BaseRateEntry | None:
        return self.entries.get(key)


@dataclass
class MultiplierRule:
    name: str
    condition: Callable[[dict[str, Any]], bool]
    true_value: float
    false_value: float = 1.0


@dataclass
class ConditionalMultiplier:
    name: str
    conditions: list[tuple[Callable[[dict[str, Any]], bool], float]]
    default_value: float = 1.0


@dataclass
class ReviewTrigger:
    name: str
    condition: Callable[[dict[str, Any], dict[str, Any]], bool]
    reason: str = ""


class DOIndustryResult(BaseModel):
    industry_group: str


class TechEOHazardResult(BaseModel):
    hazard_class: str


class EPLIndustryResult(BaseModel):
    industry_group: str


class CGLExposuresResult(BaseModel):
    recommended_hazard: str
    should_upgrade: bool


class ProductsOperationsResult(BaseModel):
    multiplier: float
    reasoning: str


@dataclass
class CoverageRatingDefinition:
    coverage_id: str
    limits_retentions: LimitRetentionConfig
    base_rate_table: BaseRateTable | None = None
    multiplier_rules: list[MultiplierRule | ConditionalMultiplier] = field(
        default_factory=list
    )
    review_triggers: list[ReviewTrigger] = field(default_factory=list)
