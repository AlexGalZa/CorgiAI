"""
Premium rating engine for the Corgi Insurance platform.

Pure calculation logic with no direct database access. Takes company data,
questionnaire answers, and coverage selections, then computes premiums
through a multi-step pipeline:

    Base Premium → Limit Factor → Retention Factor → Risk Multipliers
    → Split Limit Discount → Underwriter Adjustment → State Tax
    → Stripe Processing Fee → Final Premium

Supports AI-powered classification for D&O industry groups, Tech E&O
hazard classes, EPL industry groups, and CGL exposure assessments.
Results include state tax and Stripe fee but exclude promo discounts.
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Union

from pydantic import BaseModel

from ai.service import AIService
from ai.schemas import AIQueryInput
from rating.schemas import (
    CGLExposuresResult,
    CoverageRatingDefinition,
    DOIndustryResult,
    EPLIndustryResult,
    MultiplierRule,
    ConditionalMultiplier,
    ProductsOperationsResult,
    TechEOHazardResult,
)
from rating.constants import (
    CGL_HAZARD_LEVELS,
    DO_INDUSTRY_PROMPT,
    TECH_EO_HAZARD_PROMPT,
    EPL_INDUSTRY_PROMPT,
    CGL_EXPOSURES_PROMPT,
    CGL_PRODUCTS_OPERATIONS_PROMPT,
    STATE_TAX_RATES,
    MONTHLY_BILLING_MULTIPLIER,
    STRIPE_PROCESSING_FEE_MULTIPLIER,
)
from rating.rules.cgl import BASE_RATES, ALT_CLASS_RATES, SQUARE_FOOTAGE_VALUES
from rating.rules.cyber import (
    RATE_TIERS,
    get_security_controls_factor,
    get_regulations_factor,
)
from rating.rules.do import BASE_PREMIUMS, get_geography_group_from_state
from rating.rules.epl import (
    EMPLOYEE_TIERS,
    GEOGRAPHY_STATES,
    get_highest_risk_geography,
)
from rating.rules.fiduciary import calculate_fiduciary_base_premium
from rating.rules.hnoa import DRIVER_BAND_PREMIUMS
from rating.rules.media import (
    REVENUE_TIERS as MEDIA_REVENUE_TIERS,
    get_content_exposure_factor,
)
from rating.rules.tech_eo import (
    REVENUE_TIERS as TECH_EO_REVENUE_TIERS,
    HAZARD_CLASS_FACTORS,
    calculate_ai_coverage_multiplier,
)


@dataclass
class CalculationContext:
    questionnaire: Union[BaseModel, dict]
    revenue: Decimal
    limit: int
    retention: int
    per_occurrence_limit: int = 0
    employee_count: int = 0
    driver_count: int = 0
    plan_assets: Decimal = Decimal("0")
    state: str = ""
    business_description: str = ""

    def __post_init__(self):
        if isinstance(self.questionnaire, BaseModel):
            self.questionnaire = self.questionnaire.model_dump()
        # Default per_occurrence_limit to aggregate limit if not provided
        if self.per_occurrence_limit == 0:
            self.per_occurrence_limit = self.limit


@dataclass
class CalculationResult:
    success: bool
    premium: Decimal | None = None
    base_premium: Decimal | None = None
    limit_factor: float | None = None
    retention_factor: float | None = None
    multipliers: dict[str, float] | None = None
    breakdown: str | None = None
    review_reason: str | None = None
    ai_classifications: dict | None = None


class RatingService:
    @staticmethod
    def calculate(
        definition: CoverageRatingDefinition,
        context: CalculationContext,
        bypass_review: bool = False,
        underwriter_multiplier: float = 1.0,
        underwriter_comment: str = "",
    ) -> CalculationResult:
        ai_classifications = RatingService._enrich_questionnaire(definition, context)

        bypassed_reason = None
        review_reasons = RatingService._check_review_triggers(definition, context)
        if review_reasons:
            if bypass_review:
                bypassed_reason = review_reasons[0]
            else:
                return CalculationResult(
                    success=False,
                    review_reason=review_reasons[0],
                    ai_classifications=ai_classifications or None,
                )

        base_premium = RatingService._get_base_premium(definition, context)
        if base_premium is None:
            return CalculationResult(
                success=False,
                review_reason="Could not determine base premium - outside standard rating parameters",
                ai_classifications=ai_classifications or None,
            )

        limit_factor = RatingService._get_limit_factor(definition, context.limit)
        retention_factor = RatingService._get_retention_factor(
            definition, context.retention
        )

        multipliers = RatingService._calculate_multipliers(
            definition, context.questionnaire
        )

        split_limit_discount = 1.0
        if context.per_occurrence_limit < context.limit:
            split_limit_discount = 0.9
            multipliers["split_limit_discount"] = split_limit_discount

        if underwriter_multiplier != 1.0:
            multipliers["underwriter_adjustment"] = underwriter_multiplier

        state_tax_multiplier = (
            STATE_TAX_RATES.get(context.state.upper(), 1.0) if context.state else 1.0
        )
        if state_tax_multiplier != 1.0:
            multipliers["state_tax"] = state_tax_multiplier

        multipliers["processing_fee"] = STRIPE_PROCESSING_FEE_MULTIPLIER

        total_multiplier = limit_factor * retention_factor * split_limit_discount
        for name, value in multipliers.items():
            if name != "split_limit_discount":
                total_multiplier *= value

        premium = base_premium * Decimal(str(total_multiplier))
        premium = premium.quantize(Decimal("0.01"))

        breakdown = RatingService._build_breakdown(
            base_premium,
            limit_factor,
            retention_factor,
            multipliers,
            premium,
            bypassed_reason=bypassed_reason,
            underwriter_comment=underwriter_comment,
        )

        return CalculationResult(
            success=True,
            premium=premium,
            base_premium=base_premium,
            limit_factor=limit_factor,
            retention_factor=retention_factor,
            multipliers=multipliers,
            breakdown=breakdown,
            ai_classifications=ai_classifications or None,
        )

    @staticmethod
    def _check_review_triggers(
        definition: CoverageRatingDefinition, context: CalculationContext
    ) -> list[str]:
        reasons = []
        for trigger in definition.review_triggers:
            if trigger.condition(context.questionnaire, context):
                reasons.append(trigger.reason)
        return reasons

    @staticmethod
    def _enrich_questionnaire(
        definition: CoverageRatingDefinition, context: CalculationContext
    ) -> dict:
        ai_classifications = {}

        if definition.coverage_id == "directors-and-officers":
            if context.state and not context.questionnaire.get("geography_group"):
                context.questionnaire["geography_group"] = (
                    get_geography_group_from_state(context.state)
                )

            cached_do_description = context.questionnaire.get(
                "do_industry_group_description_used"
            )
            if context.business_description and (
                not context.questionnaire.get("industry_group")
                or cached_do_description != context.business_description
            ):
                value = RatingService._classify_do_industry_group(
                    context.business_description
                )
                context.questionnaire["industry_group"] = value
                context.questionnaire["do_industry_group_description_used"] = (
                    context.business_description
                )
                ai_classifications["do_industry_group"] = value
                ai_classifications["do_industry_group_description_used"] = (
                    context.business_description
                )

        if definition.coverage_id == "employment-practices-liability":
            geographic_spread = context.questionnaire.get("geographic_spread") or []
            international_spread = (
                context.questionnaire.get("international_spread") or []
            )

            if context.questionnaire.get("wants_contractor_epli"):
                contractor_geo = (
                    context.questionnaire.get("contractor_geographic_spread") or []
                )
                contractor_intl = (
                    context.questionnaire.get("contractor_international_spread") or []
                )
                geographic_spread = geographic_spread + contractor_geo
                international_spread = international_spread + contractor_intl

            if (
                geographic_spread or international_spread
            ) and not context.questionnaire.get("geography_group"):
                context.questionnaire["geography_group"] = get_highest_risk_geography(
                    geographic_spread, international_spread
                )
            elif context.state and not context.questionnaire.get("geography_group"):
                state_upper = context.state.upper()
                for group, states in GEOGRAPHY_STATES.items():
                    if state_upper in states:
                        context.questionnaire["geography_group"] = group
                        break

            cached_epl_description = context.questionnaire.get(
                "epl_industry_group_description_used"
            )
            if context.business_description and (
                not context.questionnaire.get("industry_group")
                or cached_epl_description != context.business_description
            ):
                value = RatingService._classify_epl_industry(
                    context.business_description
                )
                context.questionnaire["industry_group"] = value
                context.questionnaire["epl_industry_group_description_used"] = (
                    context.business_description
                )
                ai_classifications["epl_industry_group"] = value
                ai_classifications["epl_industry_group_description_used"] = (
                    context.business_description
                )

        if definition.coverage_id == "technology-errors-and-omissions":
            services_description = context.questionnaire.get("services_description")
            cached_eo_description = context.questionnaire.get(
                "hazard_class_description_used"
            )
            if services_description and (
                not context.questionnaire.get("hazardClass")
                or cached_eo_description != services_description
            ):
                value = RatingService._classify_tech_eo_hazard_class(
                    services_description
                )
                context.questionnaire["hazardClass"] = value
                context.questionnaire["hazard_class_description_used"] = (
                    services_description
                )
                ai_classifications["tech_eo_hazard_class"] = value
                ai_classifications["hazard_class_description_used"] = (
                    services_description
                )

        if definition.coverage_id == "commercial-general-liability":
            other_exposures = context.questionnaire.get("other_exposures_description")
            current_hazard = context.questionnaire.get("primary_operations_hazard")
            cached_cgl_exposures = context.questionnaire.get(
                "cgl_hazard_description_used"
            )
            if (
                context.questionnaire.get("has_other_exposures")
                and other_exposures
                and current_hazard
                and cached_cgl_exposures != other_exposures
            ):
                value = RatingService._review_cgl_exposures(
                    other_exposures, current_hazard
                )
                if value != current_hazard:
                    context.questionnaire["primary_operations_hazard"] = value
                context.questionnaire["cgl_hazard_description_used"] = other_exposures
                ai_classifications["cgl_hazard_class"] = value
                ai_classifications["cgl_hazard_description_used"] = other_exposures

            products_ops_description = context.questionnaire.get(
                "products_completed_operations_description"
            )
            cached_description = context.questionnaire.get(
                "products_operations_description_used"
            )
            if (
                context.questionnaire.get("has_products_completed_operations")
                and products_ops_description
                and (
                    not context.questionnaire.get("products_operations_multiplier")
                    or cached_description != products_ops_description
                )
            ):
                multiplier = RatingService._assess_products_operations_risk(
                    products_ops_description
                )
                context.questionnaire["products_operations_multiplier"] = multiplier
                context.questionnaire["products_operations_description_used"] = (
                    products_ops_description
                )
                ai_classifications["products_operations_multiplier"] = multiplier
                ai_classifications["products_operations_description_used"] = (
                    products_ops_description
                )

        return ai_classifications

    @staticmethod
    def _classify_do_industry_group(business_description: str) -> str:
        result: DOIndustryResult = AIService.query(
            AIQueryInput(
                prompt=f"Classify this business into a D&O industry risk group:\n\n{business_description}",
                system_prompt=DO_INDUSTRY_PROMPT,
                response_format=DOIndustryResult,
            )
        )
        return result.industry_group

    @staticmethod
    def _classify_tech_eo_hazard_class(services_description: str) -> str:
        result: TechEOHazardResult = AIService.query(
            AIQueryInput(
                prompt=f"Classify this technology company into a hazard class:\n\n{services_description}",
                system_prompt=TECH_EO_HAZARD_PROMPT,
                response_format=TechEOHazardResult,
            )
        )
        return result.hazard_class

    @staticmethod
    def _classify_epl_industry(business_description: str) -> str:
        result: EPLIndustryResult = AIService.query(
            AIQueryInput(
                prompt=f"Classify this business into an EPL industry group:\n\n{business_description}",
                system_prompt=EPL_INDUSTRY_PROMPT,
                response_format=EPLIndustryResult,
            )
        )
        return result.industry_group

    @staticmethod
    def _review_cgl_exposures(
        other_exposures_description: str, current_hazard: str
    ) -> str:
        current_index = (
            CGL_HAZARD_LEVELS.index(current_hazard)
            if current_hazard in CGL_HAZARD_LEVELS
            else 1
        )
        result: CGLExposuresResult = AIService.query(
            AIQueryInput(
                prompt=f"Review these additional exposures and determine if hazard classification should be upgraded.\n\nCurrent Hazard Level: {current_hazard}\nAdditional Exposures: {other_exposures_description}",
                system_prompt=CGL_EXPOSURES_PROMPT,
                response_format=CGLExposuresResult,
            )
        )
        recommended_index = (
            CGL_HAZARD_LEVELS.index(result.recommended_hazard)
            if result.recommended_hazard in CGL_HAZARD_LEVELS
            else current_index
        )
        if result.should_upgrade and recommended_index > current_index:
            return result.recommended_hazard
        return current_hazard

    @staticmethod
    def _assess_products_operations_risk(description: str) -> float:
        result: ProductsOperationsResult = AIService.query(
            AIQueryInput(
                prompt=f"Assess the following products or completed operations and determine the appropriate risk multiplier:\n\n{description}",
                system_prompt=CGL_PRODUCTS_OPERATIONS_PROMPT,
                response_format=ProductsOperationsResult,
            )
        )
        return max(1.1, min(1.5, result.multiplier))

    @staticmethod
    def _get_base_premium(
        definition: CoverageRatingDefinition, context: CalculationContext
    ) -> Decimal | None:
        coverage_id = definition.coverage_id

        if coverage_id == "commercial-general-liability":
            return RatingService._get_cgl_base_premium(context)
        elif coverage_id == "cyber-liability":
            return RatingService._get_cyber_base_premium(context)
        elif coverage_id == "directors-and-officers":
            return RatingService._get_do_base_premium(context)
        elif coverage_id == "employment-practices-liability":
            return RatingService._get_epl_base_premium(context)
        elif coverage_id == "fiduciary-liability":
            return RatingService._get_fiduciary_base_premium(context)
        elif coverage_id == "hired-and-non-owned-auto":
            return RatingService._get_hnoa_base_premium(context)
        elif coverage_id == "media-liability":
            return RatingService._get_media_base_premium(context)
        elif coverage_id == "technology-errors-and-omissions":
            return RatingService._get_tech_eo_base_premium(context)

        return None

    @staticmethod
    def _get_cgl_base_premium(context: CalculationContext) -> Decimal | None:
        hazard = context.questionnaire.get(
            "primary_operations_hazard", "moderate-hazard"
        )
        entry = BASE_RATES.get(hazard)
        if not entry:
            return None

        minimum = entry.minimum_premium
        revenue = (
            Decimal(str(context.revenue))
            if not isinstance(context.revenue, Decimal)
            else context.revenue
        )
        gross_sales = float(revenue)

        if gross_sales == 0:
            office_sq_ft_raw = context.questionnaire.get("office_square_footage", 0)
            if isinstance(office_sq_ft_raw, str):
                office_sq_ft = SQUARE_FOOTAGE_VALUES.get(office_sq_ft_raw, 0)
            else:
                office_sq_ft = office_sq_ft_raw
            alt_rate = ALT_CLASS_RATES.get(hazard, Decimal("11.00"))
            premium = (Decimal(str(office_sq_ft)) / 1000) * alt_rate
        else:
            rate = Decimal(str(entry.rate))
            premium = (revenue / 1000) * rate

        return max(premium, minimum)

    @staticmethod
    def _get_cyber_base_premium(context: CalculationContext) -> Decimal | None:
        risk_group = context.questionnaire.get("riskGroup", 2)
        group_key = f"group{risk_group}"
        revenue = max(float(context.revenue), 500_000)
        rateable_revenue = revenue / 2

        rate = RatingService._interpolate_cyber_rate(
            rateable_revenue, group_key, RATE_TIERS
        )
        if rate is None:
            return None

        return Decimal(str(rateable_revenue * rate))

    @staticmethod
    def _interpolate_cyber_rate(
        rateable_revenue: float, group_key: str, tiers: list
    ) -> float | None:
        min_revenue = tiers[0]["revenue"]
        max_revenue = tiers[-1]["revenue"]

        if rateable_revenue <= min_revenue:
            return tiers[0].get(group_key)

        if rateable_revenue >= max_revenue:
            return tiers[-1].get(group_key)

        lower_tier = None
        upper_tier = None
        for i, tier in enumerate(tiers):
            if tier["revenue"] <= rateable_revenue:
                lower_tier = tier
                if i + 1 < len(tiers):
                    upper_tier = tiers[i + 1]

        if lower_tier is None or upper_tier is None:
            return None

        if rateable_revenue == lower_tier["revenue"]:
            return lower_tier.get(group_key)

        lower_rate = lower_tier.get(group_key)
        upper_rate = upper_tier.get(group_key)
        lower_bound = lower_tier["revenue"]
        upper_bound = upper_tier["revenue"]

        if lower_rate is None or upper_rate is None:
            return None

        rate = lower_rate + (upper_rate - lower_rate) * (
            rateable_revenue - lower_bound
        ) / (upper_bound - lower_bound)
        return rate

    @staticmethod
    def _get_do_base_premium(context: CalculationContext) -> Decimal | None:
        total_amount_raised = float(context.questionnaire.get("funding_raised", 0))

        tiers = [
            (0, 833_000, "0_833000"),
            (833_001, 2_500_000, "833001_2500000"),
            (2_500_001, 4_167_000, "2500001_4167000"),
            (4_167_001, 8_333_000, "4167001_8333000"),
            (8_333_001, 16_667_000, "8333001_16667000"),
            (16_667_001, 25_000_000, "16667001_25000000"),
            (25_000_001, 33_333_000, "25000001_33333000"),
            (33_333_001, 50_000_000, "33333001_50000000"),
            (50_000_001, 66_667_000, "50000001_66667000"),
            (66_667_001, 83_333_000, "66667001_83333000"),
            (83_333_001, 125_000_000, "83333001_125000000"),
            (125_000_001, 166_667_000, "125000001_166667000"),
            (166_667_001, 250_000_000, "166667001_250000000"),
            (250_000_001, 333_333_000, "250000001_333333000"),
            (333_333_001, 416_667_000, "333333001_416667000"),
            (416_667_001, 500_000_000, "416667001_500000000"),
            (500_000_001, float("inf"), "500000001_plus"),
        ]

        for min_val, max_val, key in tiers:
            if min_val <= total_amount_raised <= max_val:
                entry = BASE_PREMIUMS.get(key)
                if entry:
                    return Decimal(str(entry.rate))
        return None

    @staticmethod
    def _get_epl_base_premium(context: CalculationContext) -> Decimal | None:
        us_employees = sum(
            item.get("employee_count", 0)
            for item in (context.questionnaire.get("geographic_spread") or [])
        )
        international_employees = sum(
            item.get("employee_count", 0)
            for item in (context.questionnaire.get("international_spread") or [])
        )
        employee_count = us_employees + international_employees

        if context.questionnaire.get("wants_contractor_epli"):
            us_contractors = sum(
                item.get("employee_count", 0)
                for item in (
                    context.questionnaire.get("contractor_geographic_spread") or []
                )
            )
            international_contractors = sum(
                item.get("employee_count", 0)
                for item in (
                    context.questionnaire.get("contractor_international_spread") or []
                )
            )
            employee_count += us_contractors + international_contractors

        if employee_count == 0:
            employee_count = context.employee_count or 10
        employee_count = max(employee_count, 10)

        cumulative_from_previous = Decimal("0")
        for tier in EMPLOYEE_TIERS:
            if tier["ceiling"] <= employee_count and tier["cumulative"] is not None:
                cumulative_from_previous = Decimal(str(tier["cumulative"]))
            else:
                break

        current_tier = None
        for tier in EMPLOYEE_TIERS:
            if tier["floor"] < employee_count <= tier["ceiling"]:
                current_tier = tier
                break
            elif tier["floor"] == 0 and employee_count <= tier["ceiling"]:
                current_tier = tier
                break

        if current_tier is None:
            current_tier = EMPLOYEE_TIERS[-1]

        employees_in_current_tier = employee_count - current_tier["floor"]
        incremental_premium = Decimal(str(employees_in_current_tier)) * Decimal(
            str(current_tier["rate"])
        )

        return cumulative_from_previous + incremental_premium

    @staticmethod
    def _get_fiduciary_base_premium(context: CalculationContext) -> Decimal | None:
        from rating.questionnaires.fiduciary import PLAN_ASSET_BAND_VALUES

        plan_assets = float(context.plan_assets) if context.plan_assets else 0
        if not plan_assets:
            asset_band = context.questionnaire.get("total_plan_assets", "")
            if isinstance(asset_band, str) and asset_band in PLAN_ASSET_BAND_VALUES:
                plan_assets = PLAN_ASSET_BAND_VALUES[asset_band]
            elif asset_band:
                try:
                    plan_assets = float(asset_band)
                except (ValueError, TypeError):
                    plan_assets = 0
        return calculate_fiduciary_base_premium(plan_assets, has_defined_benefit=False)

    @staticmethod
    def _get_hnoa_base_premium(context: CalculationContext) -> Decimal | None:
        driver_band = context.questionnaire.get("driver_band", "0_5")
        return DRIVER_BAND_PREMIUMS.get(driver_band)

    @staticmethod
    def _get_media_base_premium(context: CalculationContext) -> Decimal | None:
        for tier in MEDIA_REVENUE_TIERS:
            if float(context.revenue) <= tier["max"]:
                return tier["premium"]
        return None

    @staticmethod
    def _get_tech_eo_base_premium(context: CalculationContext) -> Decimal | None:
        revenue = float(context.revenue)
        base = None
        for tier in TECH_EO_REVENUE_TIERS:
            min_val = tier.get("min", 0)
            max_val = tier["max"]
            if min_val < revenue <= max_val:
                base = tier["premium"]
                break
        if base is None and revenue <= TECH_EO_REVENUE_TIERS[0]["max"]:
            base = TECH_EO_REVENUE_TIERS[0]["premium"]

        if base is None:
            return None

        hazard_class = context.questionnaire.get("hazardClass", "b2b-saas")
        hazard_factor = HAZARD_CLASS_FACTORS.get(hazard_class, 1.0)

        return base * Decimal(str(hazard_factor))

    @staticmethod
    def _get_limit_factor(definition: CoverageRatingDefinition, limit: int) -> float:
        for opt in definition.limits_retentions.aggregate_limits:
            if opt.value == limit:
                return opt.factor
        return 1.0

    @staticmethod
    def _get_retention_factor(
        definition: CoverageRatingDefinition, retention: int
    ) -> float:
        for opt in definition.limits_retentions.retentions:
            if opt.value == retention:
                return opt.factor
        return 1.0

    @staticmethod
    def _calculate_multipliers(
        definition: CoverageRatingDefinition, questionnaire: dict
    ) -> dict[str, float]:
        multipliers = {}

        for rule in definition.multiplier_rules:
            if isinstance(rule, MultiplierRule):
                if rule.condition(questionnaire):
                    multipliers[rule.name] = rule.true_value
                else:
                    multipliers[rule.name] = rule.false_value
            elif isinstance(rule, ConditionalMultiplier):
                value = rule.default_value
                for condition, factor in rule.conditions:
                    if condition(questionnaire):
                        value = factor
                        break
                multipliers[rule.name] = value

        if definition.coverage_id == "cyber-liability":
            multipliers["security_controls"] = get_security_controls_factor(
                questionnaire
            )
            multipliers["regulations"] = get_regulations_factor(questionnaire)

        if definition.coverage_id == "media-liability":
            multipliers["content_exposure"] = get_content_exposure_factor(questionnaire)

        if definition.coverage_id == "commercial-general-liability":
            products_ops_multiplier = questionnaire.get(
                "products_operations_multiplier"
            )
            if products_ops_multiplier is not None:
                multipliers["products_operations"] = products_ops_multiplier

        if definition.coverage_id == "technology-errors-and-omissions":
            ai_multiplier = calculate_ai_coverage_multiplier(questionnaire)
            if ai_multiplier != 1.0:
                multipliers["ai_coverage"] = ai_multiplier

        return multipliers

    @staticmethod
    def _build_breakdown(
        base_premium: Decimal,
        limit_factor: float,
        retention_factor: float,
        multipliers: dict[str, float],
        final_premium: Decimal,
        bypassed_reason: str | None = None,
        underwriter_comment: str = "",
    ) -> str:
        lines = []

        if bypassed_reason:
            lines.append(f"⚠️ Review bypassed: {bypassed_reason}")

        lines.extend(
            [
                f"Base Premium: ${base_premium:,.2f}",
                f"Limit Factor: {limit_factor}",
                f"Retention Factor: {retention_factor}",
            ]
        )

        if multipliers:
            lines.append("Multipliers:")
            for name, value in multipliers.items():
                lines.append(f"  - {name}: {value}")

        lines.append(f"Final Premium: ${final_premium:,.2f}")

        if underwriter_comment:
            lines.append(f"Underwriter Note: {underwriter_comment}")

        return "\n".join(lines)

    @staticmethod
    def get_billing_surcharge() -> Decimal:
        return Decimal(str(MONTHLY_BILLING_MULTIPLIER))

    @staticmethod
    def apply_monthly_surcharge(base_premium: Decimal) -> Decimal:
        return base_premium * Decimal(str(MONTHLY_BILLING_MULTIPLIER))

    @staticmethod
    def get_monthly_payment(annual_premium: Decimal) -> Decimal:
        return annual_premium / 12

    @staticmethod
    def calculate_billing_amounts(
        annual_premium: Decimal | float,
        billing_frequency: str,
    ) -> dict:
        annual = Decimal(str(annual_premium))

        if billing_frequency == "annual":
            return {
                "annual": annual,
                "monthly": annual / 12,
                "discount_applied": True,
            }
        else:
            base = annual * Decimal(str(MONTHLY_BILLING_MULTIPLIER))
            return {
                "annual": base,
                "monthly": base / 12,
                "discount_applied": False,
            }

    @staticmethod
    def apply_promo_discount(amount: float, promo) -> float:
        if not promo or not getattr(promo, "coupon", None):
            return amount
        coupon = promo.coupon
        if getattr(coupon, "percent_off", None):
            return amount * (1 - coupon.percent_off / 100)
        if getattr(coupon, "amount_off", None):
            return max(0, amount - coupon.amount_off / 100)
        return amount
