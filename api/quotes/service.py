"""
Quote service layer for the Corgi Insurance platform.

Orchestrates the full quote lifecycle: draft creation, step-by-step form
saving, company deduplication, premium rating, checkout URL generation,
partial checkout splitting, and quote migration between organizations.

Key responsibilities:
- Company dedup by federal EIN or legal name.
- Coverage tier routing (Tier 1 instant, Tier 2/3 brokered).
- AI classification enrichment (D&O industry, Tech E&O hazard, EPL, CGL).
- Promo code validation and discount calculation.
- Stripe checkout session creation (annual + monthly).
- Email notifications (quote ready, needs review).
"""

from datetime import date
from decimal import Decimal
from django.conf import settings
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError
from s3.service import S3Service
from s3.schemas import UploadFileInput
from stripe_integration.service import StripeService
from quotes.models import Quote, Company, Address, QuoteDocument
from organizations.models import OrganizationMember
from quotes.schemas import (
    RatingResult,
    StoredRatingResult,
    CoverageBreakdown,
    ReviewReason,
)
from quotes.constants import (
    COVERAGE_TO_FORM_KEY,
    FILE_FIELDS,
    BROKERED_FORM_COVERAGE_TYPES,
    BROKERED_NO_FORM_COVERAGE_TYPES,
)
from emails.service import EmailService
from emails.schemas import SendEmailInput
from policies.service import PolicyService
from policies.schemas import CreatePaymentLinkInput
from common.constants import COVERAGE_DISPLAY_NAMES
from common.exceptions import AccessDeniedError
from common.utils import deep_merge, parse_date, strip_keys_recursive
from organizations.service import OrganizationService
from rating.service import RatingService, CalculationContext
from rating.rules import get_definition
from rating.questionnaires import validate_questionnaire
from brokered.service import BrokeredService
from organizations.enrichment_service import CompanyEnrichmentService


class QuoteService:
    @staticmethod
    @transaction.atomic
    def create_draft_quote(
        coverages: list[str], selected_package: str | None, user
    ) -> Quote:
        if not OrganizationService.can_edit(user):
            raise AccessDeniedError("You do not have permission to create quotes")

        org_id = OrganizationService.get_active_org_id(user)

        address = Address.objects.create(
            street_address="",
            city="",
            state="CA",
            zip="",
        )

        company = Company.objects.create(
            business_address=address,
            entity_legal_name="",
            type="corporation",
            profit_type="for-profit",
            last_12_months_revenue=0,
            projected_next_12_months_revenue=0,
            business_description="",
        )

        quote = Quote.objects.create(
            user=user,
            organization_id=org_id,
            company=company,
            status="draft",
            coverages=coverages,
            available_coverages=coverages,
            completed_steps=["welcome", "package-selection"],
            current_step="products",
            form_data_snapshot={
                "coverages": coverages,
                "selected_package": selected_package,
            },
        )

        return quote

    @staticmethod
    def save_step(
        quote_number: str, step_id: str, data: dict, user, next_step: str | None = None
    ) -> Quote | None:
        if not OrganizationService.can_edit(user):
            return None

        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        clean_data = strip_keys_recursive(data, FILE_FIELDS)
        current_data = quote.form_data_snapshot or {}
        quote.form_data_snapshot = deep_merge(current_data, clean_data)

        if quote.status in ["quoted", "submitted", "needs_review"]:
            quote.status = "draft"
            quote.rating_result = None
            quote.quote_amount = None

        if "coverages" in data:
            quote.coverages = data["coverages"]
            existing_available = set(quote.available_coverages or [])
            new_coverages = set(data["coverages"])
            quote.available_coverages = list(existing_available | new_coverages)

        completed = quote.completed_steps or []
        if step_id not in completed:
            quote.completed_steps = completed + [step_id]

        if next_step and next_step not in completed:
            quote.current_step = next_step

        quote.save()

        return quote

    @staticmethod
    def _handle_document_upload(quote, file, document_type):
        try:
            path_prefix = f"quotes/{quote.quote_number}/{document_type}"

            result = S3Service.upload_file(
                UploadFileInput(
                    file=file,
                    path_prefix=path_prefix,
                    original_filename=file.name,
                    content_type=getattr(file, "content_type", None),
                )
            )

            if result:
                return QuoteDocument.objects.create(
                    quote=quote,
                    file_type=document_type,
                    original_filename=file.name,
                    file_size=file.size,
                    mime_type=getattr(file, "content_type", ""),
                    s3_key=result["s3_key"],
                    s3_url=result["s3_url"],
                )
            return None
        except Exception as e:
            raise e

    @staticmethod
    def upload_quote_document(
        quote_number: str, file, document_type: str, user
    ) -> dict | None:
        """Upload a single document for an existing quote (e.g. claim PDF from loss-history step).

        Returns a lightweight dict with id/filename/s3_key for the client to
        reference, or ``None`` if the quote is not found or the user lacks
        permission.
        """
        if not OrganizationService.can_edit(user):
            return None

        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        doc = QuoteService._handle_document_upload(quote, file, document_type)
        if not doc:
            return None
        return {
            "id": doc.id,
            "file_type": doc.file_type,
            "original_filename": doc.original_filename,
            "file_size": doc.file_size,
            "s3_key": doc.s3_key,
        }

    @staticmethod
    @transaction.atomic
    def create_quote(form_data, financial_files, transaction_files, claim_files, user):
        company_info = form_data["company_info"]
        address_data = company_info["business_address"]
        organization_info = company_info["organization_info"]
        financial_details = company_info["financial_details"]
        structure_operations = company_info["structure_operations"]

        federal_ein = organization_info.get("federal_ein")
        entity_legal_name = organization_info["entity_legal_name"]

        company_fields = dict(
            entity_legal_name=entity_legal_name,
            type=organization_info["organization_type"],
            type_other=organization_info.get("organization_type_other"),
            profit_type=organization_info["is_for_profit"],
            federal_ein=federal_ein,
            business_start_date=parse_date(
                organization_info.get("business_start_date")
            ),
            estimated_payroll=organization_info.get("estimated_payroll"),
            last_12_months_revenue=financial_details["last_12_months_revenue"],
            projected_next_12_months_revenue=financial_details[
                "projected_next_12_months_revenue"
            ],
            full_time_employees=financial_details.get("full_time_employees"),
            part_time_employees=financial_details.get("part_time_employees"),
            is_technology_company=structure_operations.get("is_technology_company"),
            has_subsidiaries=structure_operations["has_subsidiaries"],
            all_entities_covered=structure_operations.get("all_entities_covered"),
            subsidiaries_explanation=structure_operations.get(
                "subsidiaries_explanation"
            ),
            planned_acquisitions=structure_operations["planned_acquisitions"],
            planned_acquisitions_details=structure_operations.get(
                "planned_acquisitions_details"
            ),
            business_description=structure_operations["business_description"],
        )

        if federal_ein:
            existing_company = (
                Company.objects.filter(federal_ein=federal_ein).order_by("-id").first()
            )
        elif entity_legal_name:
            existing_company = (
                Company.objects.filter(
                    entity_legal_name=entity_legal_name,
                    quotes__user=user,
                )
                .order_by("-id")
                .first()
            )
        else:
            existing_company = None

        if existing_company:
            address = existing_company.business_address
            Address.objects.filter(pk=address.pk).update(
                street_address=address_data["street_address"],
                suite=address_data.get("suite", ""),
                city=address_data["city"],
                state=address_data["state"],
                zip=address_data["zip"],
            )
            Company.objects.filter(pk=existing_company.pk).update(**company_fields)
            company = Company.objects.get(pk=existing_company.pk)
        else:
            address = Address.objects.create(
                street_address=address_data["street_address"],
                suite=address_data.get("suite", ""),
                city=address_data["city"],
                state=address_data["state"],
                zip=address_data["zip"],
            )
            company = Company.objects.create(business_address=address, **company_fields)

        # ── Company enrichment ────────────────────────────────────────────
        # Attempt to enrich company data from external providers.
        # This is best-effort: if enrichment fails or returns None, we
        # continue with whatever data the customer supplied.
        try:
            enrichment = CompanyEnrichmentService.enrich(entity_legal_name)
            if enrichment:
                update_fields = {}
                if enrichment.get("industry") and not company.industry_group:
                    update_fields["industry_group"] = enrichment["industry"]
                if enrichment.get("employee_count") and not company.full_time_employees:
                    update_fields["full_time_employees"] = enrichment["employee_count"]
                if enrichment.get("description") and not company.business_description:
                    update_fields["business_description"] = enrichment["description"]
                if update_fields:
                    Company.objects.filter(pk=company.pk).update(**update_fields)
                    company.refresh_from_db()
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Company enrichment failed for '%s' — continuing without enrichment",
                entity_legal_name,
                exc_info=True,
            )
        # ── End enrichment ────────────────────────────────────────────────

        selected_coverages = form_data["coverages"]

        coverage_data = {}
        for coverage in selected_coverages:
            form_key = COVERAGE_TO_FORM_KEY.get(coverage)
            if form_key and form_key in form_data:
                coverage_data[coverage] = form_data[form_key]

        limits_retentions = {
            k: v
            for k, v in form_data.get("limits_retentions", {}).items()
            if k in selected_coverages
        }

        completed_steps = [
            "welcome",
            "package-selection",
            "products",
            "business-address",
            "organization-info",
            "financial-details",
            "structure-operations",
        ]
        for coverage in selected_coverages:
            completed_steps.append(coverage)

        completed_steps.extend(
            [
                "insurance-history",
                "loss-history",
                "notices-signatures",
                "summary",
            ]
        )

        org_id = OrganizationService.get_active_org_id(user)

        quote = Quote.objects.create(
            company=company,
            user=user,
            organization_id=org_id,
            status="submitted",
            coverages=selected_coverages,
            available_coverages=selected_coverages,
            coverage_data=coverage_data,
            limits_retentions=limits_retentions,
            claims_history=form_data.get("claims_history"),
            billing_frequency=form_data.get("billing_frequency", "annual"),
            promo_code=form_data.get("promo_code"),
            utm_source=(form_data.get("utm_source") or "")[:64],
            utm_medium=(form_data.get("utm_medium") or "")[:64],
            utm_campaign=(form_data.get("utm_campaign") or "")[:128],
            referrer_url=form_data.get("referrer_url") or "",
            landing_page_url=form_data.get("landing_page_url") or "",
            form_data_snapshot=form_data,
            completed_steps=completed_steps,
            current_step="summary",
        )

        for file in financial_files:
            QuoteService._handle_document_upload(quote, file, "financial-statements")

        for file in transaction_files:
            QuoteService._handle_document_upload(quote, file, "transaction-documents")

        for file in claim_files:
            QuoteService._handle_document_upload(quote, file, "claim-documents")

        if "custom-workers-comp" in selected_coverages:
            BrokeredService.trigger_workers_compensation(quote)

        # Start SLA clock for quote turnaround
        try:
            from sla.services import start_sla

            start_sla("quote_turnaround", "quote", quote.id)
        except Exception:
            pass  # SLA is non-blocking; never fail a quote for it

        return quote

    @staticmethod
    @transaction.atomic
    def create_quote_for_external(payload, api_key) -> dict | None:
        if not api_key.organization_id:
            raise ValueError("API key is not associated with an organization")

        company_input = payload.company
        address_data = company_input.business_address

        company_fields = dict(
            entity_legal_name=company_input.entity_legal_name,
            type=company_input.organization_type,
            profit_type=company_input.is_for_profit,
            federal_ein=company_input.federal_ein,
            business_start_date=parse_date(company_input.business_start_date)
            if company_input.business_start_date
            else None,
            estimated_payroll=company_input.estimated_payroll,
            last_12_months_revenue=company_input.last_12_months_revenue,
            projected_next_12_months_revenue=company_input.projected_next_12_months_revenue,
            full_time_employees=company_input.full_time_employees,
            part_time_employees=company_input.part_time_employees,
            is_technology_company=company_input.is_technology_company,
            has_subsidiaries=company_input.has_subsidiaries,
            planned_acquisitions=company_input.planned_acquisitions,
            planned_acquisitions_details=company_input.planned_acquisitions_details,
            business_description=company_input.business_description,
        )

        federal_ein = company_input.federal_ein
        entity_legal_name = company_input.entity_legal_name

        if federal_ein:
            existing_company = (
                Company.objects.filter(federal_ein=federal_ein).order_by("-id").first()
            )
        elif entity_legal_name:
            existing_company = (
                Company.objects.filter(
                    entity_legal_name=entity_legal_name,
                    quotes__organization=api_key.organization,
                )
                .order_by("-id")
                .first()
            )
        else:
            existing_company = None

        if existing_company:
            address = existing_company.business_address
            Address.objects.filter(pk=address.pk).update(
                street_address=address_data.street_address,
                suite=address_data.suite or "",
                city=address_data.city,
                state=address_data.state,
                zip=address_data.zip,
            )
            Company.objects.filter(pk=existing_company.pk).update(**company_fields)
            company = Company.objects.get(pk=existing_company.pk)
        else:
            address = Address.objects.create(
                street_address=address_data.street_address,
                suite=address_data.suite or "",
                city=address_data.city,
                state=address_data.state,
                zip=address_data.zip,
            )
            company = Company.objects.create(business_address=address, **company_fields)

        coverage_data = {
            k: v for k, v in payload.coverage_data.items() if k in payload.coverages
        }
        limits_retentions = {
            k: v for k, v in payload.limits_retentions.items() if k in payload.coverages
        }

        utm_source = (getattr(payload, "utm_source", None) or "")[:64]
        utm_medium = (getattr(payload, "utm_medium", None) or "")[:64]
        utm_campaign = (getattr(payload, "utm_campaign", None) or "")[:128]
        referrer_url = getattr(payload, "referrer_url", None) or ""
        landing_page_url = getattr(payload, "landing_page_url", None) or ""

        quote = Quote.objects.create(
            company=company,
            user=api_key.created_by,
            organization=api_key.organization,
            status="submitted",
            coverages=payload.coverages,
            available_coverages=payload.coverages,
            coverage_data=coverage_data,
            limits_retentions=limits_retentions,
            claims_history=payload.claims_history,
            billing_frequency=payload.billing_frequency,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            referrer_url=referrer_url,
            landing_page_url=landing_page_url,
            form_data_snapshot={
                "coverages": payload.coverages,
                "coverage_data": coverage_data,
                "limits_retentions": limits_retentions,
                "claims_history": payload.claims_history or {},
                "billing_frequency": payload.billing_frequency,
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
                "referrer_url": referrer_url,
                "landing_page_url": landing_page_url,
            },
        )

        QuoteService.process_quote_rating(quote, send_needs_review_email=False)

        return QuoteService.get_quote_for_external(quote.quote_number)

    @staticmethod
    def simulate_rating(quote: Quote, overrides: dict) -> dict:
        coverages = overrides.get("coverages") or quote.coverages
        coverage_data = (
            overrides.get("coverage_data")
            if overrides.get("coverage_data") is not None
            else (quote.coverage_data or {})
        )
        limits_retentions = (
            overrides.get("limits_retentions")
            if overrides.get("limits_retentions") is not None
            else (quote.limits_retentions or {})
        )
        revenue = (
            Decimal(str(overrides["revenue"]))
            if overrides.get("revenue") is not None
            else quote.company.last_12_months_revenue
        )
        (
            overrides.get("employee_count")
            if overrides.get("employee_count") is not None
            else (quote.company.full_time_employees or 0)
        )
        state = overrides.get("state") or (
            quote.company.business_address.state
            if quote.company.business_address
            else ""
        )
        business_description = (
            overrides.get("business_description")
            if overrides.get("business_description") is not None
            else (quote.company.business_description or "")
        )

        total_premium = Decimal("0")
        results = {}

        for coverage in coverages:
            try:
                definition = get_definition(coverage)
                if not definition:
                    results[coverage] = {
                        "success": False,
                        "premium": None,
                        "breakdown": f"Unknown coverage type: {coverage}",
                    }
                    continue

                questionnaire_data = coverage_data.get(coverage) or {}

                try:
                    validated = validate_questionnaire(coverage, questionnaire_data)
                    questionnaire = validated.model_dump()
                except ValidationError:
                    questionnaire = questionnaire_data
                except ValueError:
                    questionnaire = questionnaire_data

                stored_ai = (quote.initial_ai_classifications or {}).get(coverage, {})
                if stored_ai:
                    for ai_key, value in stored_ai.items():
                        if ai_key in ("do_industry_group", "epl_industry_group"):
                            questionnaire["industry_group"] = value
                        elif ai_key == "tech_eo_hazard_class":
                            questionnaire["hazardClass"] = value
                        elif ai_key == "cgl_hazard_class":
                            questionnaire["primary_operations_hazard"] = value
                        elif ai_key in (
                            "products_operations_multiplier",
                            "products_operations_description_used",
                            "do_industry_group_description_used",
                            "epl_industry_group_description_used",
                            "hazard_class_description_used",
                            "cgl_hazard_description_used",
                        ):
                            questionnaire[ai_key] = value

                loss_history = (
                    (quote.form_data_snapshot or {})
                    .get("claims_history", {})
                    .get("loss_history", {})
                )
                if loss_history:
                    questionnaire["has_past_claims"] = loss_history.get(
                        "has_past_claims", False
                    )

                limits_data = limits_retentions.get(coverage) or {}
                aggregate_limit = limits_data.get("aggregate_limit") or 1_000_000
                per_occurrence_limit = (
                    limits_data.get("per_occurrence_limit") or aggregate_limit
                )
                retention = (
                    limits_data.get("retention")
                    or definition.limits_retentions.retentions[0].value
                )

                context = CalculationContext(
                    questionnaire=questionnaire,
                    revenue=revenue,
                    limit=aggregate_limit,
                    retention=retention,
                    per_occurrence_limit=per_occurrence_limit,
                    employee_count=questionnaire.get("total_employees_us") or 0,
                    driver_count=questionnaire.get("num_employees_driving") or 0,
                    state=state,
                    business_description=business_description,
                )

                result = RatingService.calculate(
                    definition,
                    context,
                    bypass_review=True,
                )

                if result.success:
                    total_premium += result.premium
                    results[coverage] = {
                        "success": True,
                        "premium": float(result.premium),
                        "breakdown": result.breakdown or "",
                    }
                else:
                    results[coverage] = {
                        "success": False,
                        "premium": None,
                        "breakdown": result.review_reason or "Rating failed",
                    }

            except Exception as e:
                results[coverage] = {
                    "success": False,
                    "premium": None,
                    "breakdown": f"Calculation error: {str(e)}",
                }

        return {
            "total_premium": float(total_premium),
            "coverages": results,
        }

    @staticmethod
    def get_quotes_for_user(user) -> list[dict]:
        org_id = OrganizationService.get_active_org_id(user)
        return list(
            Quote.objects.filter(organization_id=org_id)
            .exclude(status="purchased")
            .order_by("-created_at")
            .values(
                "id",
                "quote_number",
                "status",
                "coverages",
                "quote_amount",
                "created_at",
                "current_step",
            )
        )

    @staticmethod
    def _serialize_custom_products(quote) -> tuple[list[dict], float]:
        products = []
        for p in quote.custom_products.all():
            products.append(
                {
                    "id": f"custom-{p.id}",
                    "name": p.name,
                    "product_type": p.product_type,
                    "per_occurrence_limit": p.per_occurrence_limit,
                    "aggregate_limit": p.aggregate_limit,
                    "retention": p.retention,
                    "price": float(p.price),
                    "monthly_price": float(p.price) / 12,
                }
            )
        total = sum(p["price"] for p in products)
        return products, total

    @staticmethod
    def _build_monthly_breakdown(
        rating_result: dict, discount_multiplier: float = 1.0
    ) -> dict:
        breakdown = rating_result.get("breakdown") or {}
        monthly_breakdown = {}
        for coverage, data in breakdown.items():
            original_premium = data.get("premium", 0)
            discounted_premium = original_premium * discount_multiplier
            amounts = RatingService.calculate_billing_amounts(
                discounted_premium, "monthly"
            )
            monthly_breakdown[coverage] = {
                "premium": float(amounts["monthly"]),
                "annual_premium": discounted_premium,
            }
        return monthly_breakdown

    @staticmethod
    def get_quote_by_number(quote_number: str, user) -> dict | None:
        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        quote_annual = float(quote.quote_amount) if quote.quote_amount else 0
        monthly_amounts = RatingService.calculate_billing_amounts(
            quote_annual, "monthly"
        )
        annual_amounts = RatingService.calculate_billing_amounts(quote_annual, "annual")
        monthly_amount = float(monthly_amounts["monthly"])
        annual_amount = float(annual_amounts["annual"])

        custom_products, custom_products_total = (
            QuoteService._serialize_custom_products(quote)
        )
        custom_products_monthly = custom_products_total / 12
        total_monthly = monthly_amount + custom_products_monthly
        total_annual = annual_amount + custom_products_total

        rating_result = quote.rating_result or {}
        needs_review = rating_result.get("success") is False
        monthly_breakdown = QuoteService._build_monthly_breakdown(rating_result)

        return {
            "id": quote.id,
            "quote_number": quote.quote_number,
            "status": quote.status,
            "coverages": quote.coverages,
            "available_coverages": quote.available_coverages or quote.coverages,
            "quote_amount": quote_annual,
            "monthly_amount": monthly_amount,
            "custom_products": custom_products,
            "custom_products_total": custom_products_total,
            "custom_products_monthly": custom_products_monthly,
            "total_amount": total_annual,
            "total_monthly": total_monthly,
            "needs_review": needs_review,
            "created_at": quote.created_at.isoformat(),
            "rating_result": rating_result,
            "monthly_breakdown": monthly_breakdown,
        }

    @staticmethod
    def get_quote_for_external(identifier: str) -> dict | None:
        try:
            lookup = (
                {"id": int(identifier)}
                if identifier.isdigit()
                else {"quote_number": identifier}
            )
            quote = Quote.objects.select_related(
                "company", "company__business_address", "user"
            ).get(**lookup)
        except Quote.DoesNotExist:
            return None

        quote_annual = float(quote.quote_amount) if quote.quote_amount else 0
        monthly_amounts = RatingService.calculate_billing_amounts(
            quote_annual, "monthly"
        )
        monthly_amount = float(monthly_amounts["monthly"])

        custom_products, custom_products_total = (
            QuoteService._serialize_custom_products(quote)
        )
        total_annual = quote_annual + custom_products_total
        total_monthly = monthly_amount + custom_products_total / 12

        rating_result = quote.rating_result or {}
        monthly_breakdown = QuoteService._build_monthly_breakdown(rating_result)

        company = quote.company
        address = company.business_address

        return {
            "quote_number": quote.quote_number,
            "status": quote.status,
            "coverages": quote.coverages,
            "billing_frequency": quote.billing_frequency,
            "quote_amount": quote_annual,
            "monthly_amount": monthly_amount,
            "total_amount": total_annual,
            "total_monthly": total_monthly,
            "needs_review": rating_result.get("success") is False,
            "created_at": quote.created_at.isoformat(),
            "company": {
                "entity_legal_name": company.entity_legal_name,
                "state": address.state,
                "last_12_months_revenue": float(company.last_12_months_revenue),
                "full_time_employees": company.full_time_employees,
                "part_time_employees": company.part_time_employees,
                "email": quote.user.email if quote.user else None,
            },
            "questionnaire": quote.coverage_data or {},
            "limits_retentions": quote.limits_retentions or {},
            "custom_products": custom_products,
            "rating_result": rating_result,
            "monthly_breakdown": monthly_breakdown,
        }

    @staticmethod
    def get_all_quotes_for_external(limit: int, offset: int) -> tuple[int, list[dict]]:
        qs = Quote.objects.select_related(
            "company", "company__business_address", "user"
        ).order_by("-created_at")

        total = qs.count()
        results = []
        for quote in qs[offset : offset + limit]:
            quote_annual = float(quote.quote_amount) if quote.quote_amount else 0
            monthly_amounts = RatingService.calculate_billing_amounts(
                quote_annual, "monthly"
            )
            monthly_amount = float(monthly_amounts["monthly"])

            custom_products, custom_products_total = (
                QuoteService._serialize_custom_products(quote)
            )
            rating_result = quote.rating_result or {}
            monthly_breakdown = QuoteService._build_monthly_breakdown(rating_result)

            company = quote.company
            address = company.business_address

            results.append(
                {
                    "quote_number": quote.quote_number,
                    "status": quote.status,
                    "coverages": quote.coverages,
                    "billing_frequency": quote.billing_frequency,
                    "quote_amount": quote_annual,
                    "monthly_amount": monthly_amount,
                    "total_amount": quote_annual + custom_products_total,
                    "total_monthly": monthly_amount + custom_products_total / 12,
                    "needs_review": rating_result.get("success") is False,
                    "created_at": quote.created_at.isoformat(),
                    "company": {
                        "entity_legal_name": company.entity_legal_name,
                        "state": address.state,
                        "last_12_months_revenue": float(company.last_12_months_revenue),
                        "full_time_employees": company.full_time_employees,
                        "part_time_employees": company.part_time_employees,
                        "email": quote.user.email if quote.user else None,
                    },
                    "questionnaire": quote.coverage_data or {},
                    "limits_retentions": quote.limits_retentions or {},
                    "custom_products": custom_products,
                    "rating_result": rating_result,
                    "monthly_breakdown": monthly_breakdown,
                }
            )

        return total, results

    @staticmethod
    def _calculate_premium(quote: Quote) -> tuple[RatingResult, dict]:
        total_premium = Decimal("0")
        all_breakdowns: dict[str, CoverageBreakdown] = {}
        review_reasons: list[ReviewReason] = []
        all_ai_classifications: dict[str, dict] = {}

        overrides = {o.coverage: o for o in quote.underwriter_overrides.all()}

        if quote.company.is_technology_company is False:
            company_override = overrides.get("company")
            if not (company_override and company_override.bypass_validation):
                review_reasons.append(
                    ReviewReason(
                        coverage="company",
                        reason="Company does not qualify as a technology company - manual underwriting review required",
                    )
                )

        loss_history = (
            (quote.form_data_snapshot or {})
            .get("claims_history", {})
            .get("loss_history", {})
        )
        if loss_history.get("has_past_claims", False):
            claims_override = overrides.get("claims_history")
            if not (claims_override and claims_override.bypass_validation):
                review_reasons.append(
                    ReviewReason(
                        coverage="claims_history",
                        reason="Review required: past claims, lawsuits, or loss incidents reported",
                    )
                )

        for coverage in quote.coverages:
            override = overrides.get(coverage)

            if (
                coverage in BROKERED_FORM_COVERAGE_TYPES
                or coverage in BROKERED_NO_FORM_COVERAGE_TYPES
            ):
                if not (override and override.bypass_validation):
                    review_reasons.append(
                        ReviewReason(
                            coverage=coverage,
                            reason="Brokered coverage - requires underwriting review",
                        )
                    )
                continue

            try:
                definition = get_definition(coverage)
                if not definition:
                    review_reasons.append(
                        ReviewReason(
                            coverage=coverage,
                            reason=f"Unknown coverage type: {coverage}",
                        )
                    )
                    continue

                questionnaire_data = quote.coverage_data.get(coverage) or {}
                limits_data = quote.limits_retentions.get(coverage) or {}

                try:
                    validated = validate_questionnaire(coverage, questionnaire_data)
                    questionnaire = validated.model_dump()
                except ValidationError as e:
                    review_reasons.append(
                        ReviewReason(
                            coverage=coverage,
                            reason=f"Questionnaire validation failed: {e.error_count()} errors",
                        )
                    )
                    continue
                except ValueError:
                    questionnaire = questionnaire_data

                stored_ai = (quote.initial_ai_classifications or {}).get(coverage, {})
                if stored_ai:
                    for ai_key, value in stored_ai.items():
                        if ai_key in ("do_industry_group", "epl_industry_group"):
                            questionnaire["industry_group"] = value
                        elif ai_key == "tech_eo_hazard_class":
                            questionnaire["hazardClass"] = value
                        elif ai_key == "cgl_hazard_class":
                            questionnaire["primary_operations_hazard"] = value
                        elif ai_key in (
                            "products_operations_multiplier",
                            "products_operations_description_used",
                            "do_industry_group_description_used",
                            "epl_industry_group_description_used",
                            "hazard_class_description_used",
                            "cgl_hazard_description_used",
                        ):
                            questionnaire[ai_key] = value

                loss_history = (
                    (quote.form_data_snapshot or {})
                    .get("claims_history", {})
                    .get("loss_history", {})
                )
                if loss_history:
                    questionnaire["has_past_claims"] = loss_history.get(
                        "has_past_claims", False
                    )

                aggregate_limit = limits_data.get("aggregate_limit") or 1_000_000
                per_occurrence_limit = (
                    limits_data.get("per_occurrence_limit") or aggregate_limit
                )

                retention = (
                    limits_data.get("retention")
                    or definition.limits_retentions.retentions[0].value
                )

                context = CalculationContext(
                    questionnaire=questionnaire,
                    revenue=quote.company.last_12_months_revenue,
                    limit=aggregate_limit,
                    retention=retention,
                    per_occurrence_limit=per_occurrence_limit,
                    employee_count=questionnaire.get("total_employees_us") or 0,
                    driver_count=questionnaire.get("num_employees_driving") or 0,
                    state=quote.company.business_address.state
                    if quote.company.business_address
                    else "",
                    business_description=quote.company.business_description or "",
                )

                result = RatingService.calculate(
                    definition,
                    context,
                    bypass_review=override.bypass_validation if override else False,
                    underwriter_multiplier=float(override.multiplier)
                    if override
                    else 1.0,
                    underwriter_comment=override.comment if override else "",
                )

                if result.ai_classifications:
                    all_ai_classifications[coverage] = result.ai_classifications

                    if quote.coverage_data is None:
                        quote.coverage_data = {}
                    existing_data = quote.coverage_data.get(coverage) or {}
                    enriched_values = {}
                    for ai_key, value in result.ai_classifications.items():
                        if ai_key in ("do_industry_group", "epl_industry_group"):
                            enriched_values["industry_group"] = value
                        elif ai_key == "tech_eo_hazard_class":
                            enriched_values["hazardClass"] = value
                        elif ai_key == "cgl_hazard_class":
                            enriched_values["primary_operations_hazard"] = value
                        elif ai_key in (
                            "products_operations_multiplier",
                            "products_operations_description_used",
                            "do_industry_group_description_used",
                            "epl_industry_group_description_used",
                            "hazard_class_description_used",
                            "cgl_hazard_description_used",
                        ):
                            enriched_values[ai_key] = value
                    quote.coverage_data[coverage] = {**existing_data, **enriched_values}

                if not result.success:
                    review_reasons.append(
                        ReviewReason(
                            coverage=coverage,
                            reason=result.review_reason or "Unknown reason",
                        )
                    )
                else:
                    total_premium += result.premium
                    all_breakdowns[coverage] = CoverageBreakdown(
                        premium=float(result.premium),
                        breakdown=result.breakdown or "",
                    )

            except Exception as e:
                review_reasons.append(
                    ReviewReason(
                        coverage=coverage,
                        reason=f"Calculation error: {str(e)}",
                    )
                )

        if review_reasons:
            return RatingResult(
                success=False,
                breakdown=all_breakdowns if all_breakdowns else None,
                review_reasons=review_reasons,
            ), all_ai_classifications

        return RatingResult(
            success=True,
            total_premium=total_premium,
            breakdown=all_breakdowns,
        ), all_ai_classifications

    @staticmethod
    def send_quote_ready_email(quote: Quote, effective_date=None):
        effective = effective_date or date.today()

        annual_payment_link = PolicyService.create_payment_link(
            CreatePaymentLinkInput(
                quote=quote, billing_frequency="annual", effective_date=effective
            )
        )
        monthly_payment_link = PolicyService.create_payment_link(
            CreatePaymentLinkInput(
                quote=quote, billing_frequency="monthly", effective_date=effective
            )
        )

        quote_annual = quote.quote_amount
        if quote_annual:
            annual_amounts = RatingService.calculate_billing_amounts(
                quote_annual, "annual"
            )
            monthly_amounts = RatingService.calculate_billing_amounts(
                quote_annual, "monthly"
            )
            annual_amount = float(annual_amounts["annual"])
            monthly_amount = float(monthly_amounts["monthly"])
        else:
            annual_amount = 0
            monthly_amount = 0

        html = render_to_string(
            "emails/quote_ready.html",
            {
                "contact_name": quote.user.get_full_name(),
                "quote_number": quote.quote_number,
                "company_name": quote.company.entity_legal_name,
                "annual_premium": f"{annual_amount:,.2f}",
                "monthly_premium": f"{monthly_amount:,.2f}",
                "coverages": [COVERAGE_DISPLAY_NAMES[c] for c in quote.coverages],
                "annual_payment_link": annual_payment_link,
                "monthly_payment_link": monthly_payment_link,
            },
        )

        EmailService.send(
            SendEmailInput(
                to=[quote.user.email],
                subject="Your Quote is Ready! 🚀",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
            )
        )

    @staticmethod
    def send_needs_review_notification(
        quote: Quote, review_reasons: list[ReviewReason]
    ):
        html = render_to_string(
            "emails/needs_review.html",
            {
                "quote_number": quote.quote_number,
                "company_name": quote.company.entity_legal_name,
                "submitted_at": quote.created_at.strftime("%Y-%m-%d %H:%M"),
                "review_reasons": [
                    {"coverage": r.coverage, "reason": r.reason} for r in review_reasons
                ],
            },
        )

        recipients = [settings.CORGI_NOTIFICATION_EMAIL]
        if quote.referral_partner and quote.referral_partner.notification_emails:
            recipients.extend(quote.referral_partner.notification_emails)

        EmailService.send(
            SendEmailInput(
                to=recipients,
                subject=f"Quote Needs Review - {quote.quote_number}",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
            )
        )

    @staticmethod
    def process_quote_rating(
        quote: Quote,
        send_needs_review_email: bool = True,
    ) -> RatingResult | None:
        rating_result = None

        try:
            rating_result, ai_classifications = QuoteService._calculate_premium(quote)

            if ai_classifications:
                existing = quote.initial_ai_classifications or {}
                quote.initial_ai_classifications = {**ai_classifications, **existing}

            stored_result = StoredRatingResult.from_rating_result(
                rating_result, timezone.now().isoformat()
            )
            quote.rating_result = stored_result.to_dict()

            if rating_result.success:
                quote.quote_amount = rating_result.total_premium
                quote.status = "quoted"
                quote.quoted_at = timezone.now()
                quote.save()
                # Complete SLA clock when quote is rated
                try:
                    from sla.services import complete_sla

                    complete_sla("quote_turnaround", "quote", quote.id)
                except Exception:
                    pass
            else:
                quote.status = "needs_review"
                quote.save()

                if send_needs_review_email:
                    try:
                        QuoteService.send_needs_review_notification(
                            quote, rating_result.review_reasons
                        )
                    except Exception:
                        pass

        except Exception as e:
            quote.status = "needs_review"
            quote.rating_result = {
                "success": False,
                "total_premium": None,
                "breakdown": None,
                "review_reasons": [
                    {"coverage": "system", "reason": f"Calculation failed: {str(e)}"}
                ],
                "calculated_at": timezone.now().isoformat(),
            }
            quote.save()
            rating_result = RatingResult(
                success=False,
                review_reasons=[
                    ReviewReason(
                        coverage="system", reason=f"Calculation failed: {str(e)}"
                    )
                ],
            )

            if send_needs_review_email:
                try:
                    QuoteService.send_needs_review_notification(
                        quote, rating_result.review_reasons
                    )
                except Exception:
                    pass

        return rating_result

    @staticmethod
    @transaction.atomic
    def update_and_recalculate_quote(
        quote_number: str,
        form_data: dict,
        user,
        financial_files: list = None,
        transaction_files: list = None,
        claim_files: list = None,
    ) -> Quote | None:
        if not OrganizationService.can_edit(user):
            return None

        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        company_info = form_data["company_info"]
        address_data = company_info["business_address"]
        organization_info = company_info["organization_info"]
        financial_details = company_info["financial_details"]
        structure_operations = company_info["structure_operations"]

        quote.company.business_address.street_address = address_data["street_address"]
        quote.company.business_address.suite = address_data.get("suite", "")
        quote.company.business_address.city = address_data["city"]
        quote.company.business_address.state = address_data["state"]
        quote.company.business_address.zip = address_data["zip"]
        quote.company.business_address.save()

        quote.company.entity_legal_name = organization_info["entity_legal_name"]
        quote.company.type = organization_info["organization_type"]
        quote.company.type_other = organization_info.get("organization_type_other")
        quote.company.profit_type = organization_info["is_for_profit"]
        quote.company.federal_ein = organization_info.get("federal_ein")
        quote.company.business_start_date = parse_date(
            organization_info.get("business_start_date")
        )
        quote.company.estimated_payroll = organization_info.get("estimated_payroll")
        quote.company.last_12_months_revenue = financial_details[
            "last_12_months_revenue"
        ]
        quote.company.projected_next_12_months_revenue = financial_details[
            "projected_next_12_months_revenue"
        ]
        quote.company.full_time_employees = financial_details.get("full_time_employees")
        quote.company.part_time_employees = financial_details.get("part_time_employees")
        quote.company.is_technology_company = structure_operations.get(
            "is_technology_company"
        )
        quote.company.has_subsidiaries = structure_operations["has_subsidiaries"]
        quote.company.all_entities_covered = structure_operations.get(
            "all_entities_covered"
        )
        quote.company.subsidiaries_explanation = structure_operations.get(
            "subsidiaries_explanation"
        )
        quote.company.planned_acquisitions = structure_operations[
            "planned_acquisitions"
        ]
        quote.company.planned_acquisitions_details = structure_operations.get(
            "planned_acquisitions_details"
        )
        quote.company.business_description = structure_operations[
            "business_description"
        ]
        quote.company.save()

        selected_coverages = form_data["coverages"]

        coverage_data = {}
        for coverage in selected_coverages:
            form_key = COVERAGE_TO_FORM_KEY.get(coverage)
            if form_key and form_key in form_data:
                coverage_data[coverage] = form_data[form_key]

        limits_retentions = {
            k: v
            for k, v in form_data.get("limits_retentions", {}).items()
            if k in selected_coverages
        }

        quote.coverages = selected_coverages
        existing_available = set(quote.available_coverages or [])
        new_coverages = set(selected_coverages)
        quote.available_coverages = list(existing_available | new_coverages)
        quote.coverage_data = coverage_data
        quote.limits_retentions = limits_retentions
        quote.claims_history = form_data.get("claims_history")
        quote.billing_frequency = form_data.get("billing_frequency", "annual")
        quote.promo_code = form_data.get("promo_code")

        referral_code = form_data.get("referral_code")
        if referral_code:
            from quotes.models import ReferralPartner

            partner = ReferralPartner.objects.filter(
                slug=referral_code, is_active=True
            ).first()
            if partner:
                quote.referral_partner = partner

        quote.form_data_snapshot = form_data
        quote.status = "submitted"

        completed = quote.completed_steps or []
        if "summary" not in completed:
            quote.completed_steps = completed + ["summary"]
        quote.current_step = "summary"

        quote.save()

        for file in financial_files or []:
            QuoteService._handle_document_upload(quote, file, "financial-statements")

        for file in transaction_files or []:
            QuoteService._handle_document_upload(quote, file, "transaction-documents")

        for file in claim_files or []:
            QuoteService._handle_document_upload(quote, file, "claim-documents")

        if "custom-workers-comp" in selected_coverages:
            BrokeredService.trigger_workers_compensation(quote)

        return quote

    @staticmethod
    def get_quote_form_data(quote_number: str, user) -> dict | None:
        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        original_annual = float(quote.quote_amount) if quote.quote_amount else 0
        rating_result = quote.rating_result or {}
        review_reasons = rating_result.get("review_reasons") or []
        needs_review = rating_result.get("success") is False

        global_review_reasons = {"company", "system"}
        has_global_review = any(
            r.get("coverage") in global_review_reasons for r in review_reasons
        )
        all_coverages = set(quote.coverages or [])

        all_brokered_types = set(BROKERED_FORM_COVERAGE_TYPES) | set(
            BROKERED_NO_FORM_COVERAGE_TYPES
        )
        fulfilled_by_custom_product = {
            cp.product_type
            for cp in quote.custom_products.all()
            if cp.product_type in all_brokered_types and cp.price > 0
        }

        if has_global_review:
            instant_coverages = []
            review_coverages = list(all_coverages - fulfilled_by_custom_product)
        else:
            review_coverage_set = {
                r.get("coverage") for r in review_reasons
            } - fulfilled_by_custom_product
            instant_coverages = list(
                all_coverages - review_coverage_set - fulfilled_by_custom_product
            )
            review_coverages = list(all_coverages & review_coverage_set)

        promo_code = quote.promo_code
        discount_percentage = None
        discount_multiplier = 1.0
        if promo_code:
            promo = StripeService.get_promotion_code(promo_code)
            if promo and promo.coupon and promo.coupon.percent_off:
                discount_percentage = float(promo.coupon.percent_off)
                discount_multiplier = 1 - (discount_percentage / 100)

        discounted_annual = original_annual * discount_multiplier

        original_monthly_amounts = RatingService.calculate_billing_amounts(
            original_annual, "monthly"
        )
        original_annual_amounts = RatingService.calculate_billing_amounts(
            original_annual, "annual"
        )

        monthly_amounts = RatingService.calculate_billing_amounts(
            discounted_annual, "monthly"
        )
        annual_amounts = RatingService.calculate_billing_amounts(
            discounted_annual, "annual"
        )

        monthly_amount = float(monthly_amounts["monthly"])
        annual_amount = float(annual_amounts["annual"])

        monthly_breakdown = QuoteService._build_monthly_breakdown(rating_result)

        custom_products, custom_products_total = (
            QuoteService._serialize_custom_products(quote)
        )
        custom_products_monthly = custom_products_total / 12

        total_monthly = monthly_amount + custom_products_monthly
        total_annual = annual_amount + custom_products_total

        discount_monthly = None
        discount_annual = None
        if discount_percentage:
            discount_monthly = round(
                float(original_monthly_amounts["monthly"]) - monthly_amount, 2
            )
            discount_annual = round(
                float(original_annual_amounts["annual"]) - annual_amount, 2
            )

        instant_annual = 0.0
        breakdown = rating_result.get("breakdown", {})
        for coverage in instant_coverages:
            if coverage in breakdown:
                instant_annual += breakdown[coverage].get("premium", 0)

        instant_annual_discounted = instant_annual * discount_multiplier
        instant_monthly_amounts = RatingService.calculate_billing_amounts(
            instant_annual_discounted, "monthly"
        )
        instant_annual_amounts = RatingService.calculate_billing_amounts(
            instant_annual_discounted, "annual"
        )

        instant_total_monthly = (
            float(instant_monthly_amounts["monthly"]) + custom_products_monthly
        )
        instant_total_annual = (
            float(instant_annual_amounts["annual"]) + custom_products_total
        )

        instant_original_monthly = RatingService.calculate_billing_amounts(
            instant_annual, "monthly"
        )
        instant_original_annual = RatingService.calculate_billing_amounts(
            instant_annual, "annual"
        )
        instant_discount_monthly = None
        instant_discount_annual = None
        if discount_percentage:
            instant_discount_monthly = round(
                float(instant_original_monthly["monthly"])
                - float(instant_monthly_amounts["monthly"]),
                2,
            )
            instant_discount_annual = round(
                float(instant_original_annual["annual"])
                - float(instant_annual_amounts["annual"]),
                2,
            )

        return {
            "quote_number": quote.quote_number,
            "status": quote.status,
            "coverages": quote.coverages,
            "available_coverages": quote.available_coverages or quote.coverages,
            "form_data": quote.form_data_snapshot or {},
            "completed_steps": quote.completed_steps or [],
            "current_step": quote.current_step or "",
            "rating_result": rating_result,
            "quote_amount": discounted_annual,
            "monthly_amount": monthly_amount,
            "custom_products": custom_products,
            "custom_products_total": custom_products_total,
            "custom_products_monthly": custom_products_monthly,
            "total_amount": total_annual,
            "total_monthly": total_monthly,
            "needs_review": needs_review,
            "monthly_breakdown": monthly_breakdown,
            "promo_code": promo_code,
            "discount_percentage": discount_percentage,
            "discount_monthly": discount_monthly,
            "discount_annual": discount_annual,
            "instant_coverages": instant_coverages,
            "review_coverages": review_coverages,
            "instant_total_monthly": instant_total_monthly,
            "instant_total_annual": instant_total_annual,
            "instant_discount_monthly": instant_discount_monthly,
            "instant_discount_annual": instant_discount_annual,
        }

    @staticmethod
    @transaction.atomic
    def split_quote_for_partial_checkout(
        original_quote: Quote,
        instant_coverages: list[str],
    ) -> Quote:
        review_coverages = [
            c for c in original_quote.coverages if c not in instant_coverages
        ]

        instant_coverage_data = {
            k: v
            for k, v in (original_quote.coverage_data or {}).items()
            if k in instant_coverages
        }
        instant_limits_retentions = {
            k: v
            for k, v in (original_quote.limits_retentions or {}).items()
            if k in instant_coverages
        }

        original_breakdown = (original_quote.rating_result or {}).get(
            "breakdown", {}
        ) or {}
        instant_premium = sum(
            (original_breakdown.get(c) or {}).get("premium", 0)
            for c in instant_coverages
        )

        instant_breakdown = {
            c: original_breakdown[c]
            for c in instant_coverages
            if c in original_breakdown and original_breakdown[c] is not None
        }
        instant_rating_result = {
            "success": True,
            "total_premium": instant_premium,
            "breakdown": instant_breakdown,
            "calculated_at": timezone.now().isoformat(),
        }

        new_quote = Quote.objects.create(
            company=original_quote.company,
            user=original_quote.user,
            organization=original_quote.organization,
            status="quoted",
            coverages=instant_coverages,
            available_coverages=instant_coverages,
            coverage_data=instant_coverage_data,
            limits_retentions=instant_limits_retentions,
            claims_history=original_quote.claims_history,
            quote_amount=Decimal(str(instant_premium)),
            quoted_at=timezone.now(),
            form_data_snapshot=original_quote.form_data_snapshot,
            rating_result=instant_rating_result,
            initial_ai_classifications={
                k: v
                for k, v in (original_quote.initial_ai_classifications or {}).items()
                if k in instant_coverages
            },
            billing_frequency=original_quote.billing_frequency,
            promo_code=original_quote.promo_code,
            referral_partner=original_quote.referral_partner,
            completed_steps=original_quote.completed_steps,
            current_step="summary",
            parent_quote=original_quote,
        )

        original_quote.custom_products.filter(price__gt=0).update(quote=new_quote)

        original_quote.underwriter_overrides.filter(
            coverage__in=instant_coverages
        ).update(quote=new_quote)

        review_coverage_data = {
            k: v
            for k, v in (original_quote.coverage_data or {}).items()
            if k in review_coverages
        }
        review_limits_retentions = {
            k: v
            for k, v in (original_quote.limits_retentions or {}).items()
            if k in review_coverages
        }
        review_breakdown = {
            c: original_breakdown[c]
            for c in review_coverages
            if c in original_breakdown
        }
        review_reasons = [
            r
            for r in (original_quote.rating_result or {}).get("review_reasons", [])
            if r.get("coverage") in review_coverages or r.get("coverage") == "company"
        ]

        original_quote.coverages = review_coverages
        original_quote.available_coverages = review_coverages
        original_quote.coverage_data = review_coverage_data
        original_quote.limits_retentions = review_limits_retentions
        original_quote.rating_result = {
            "success": False,
            "breakdown": review_breakdown,
            "review_reasons": review_reasons,
            "calculated_at": timezone.now().isoformat(),
        }
        original_quote.quote_amount = None
        original_quote.initial_ai_classifications = {
            k: v
            for k, v in (original_quote.initial_ai_classifications or {}).items()
            if k in review_coverages
        }
        original_quote.save()

        return new_quote

    @staticmethod
    def create_checkout_url(
        quote_number: str,
        user,
        billing_frequency: str,
        effective_date=None,
        coverages: list[str] | None = None,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> str | None:
        if not OrganizationService.can_access_billing(user):
            return None

        if not OrganizationService.can_edit(user):
            return None

        org_id = OrganizationService.get_active_org_id(user)
        try:
            quote = Quote.objects.get(quote_number=quote_number, organization_id=org_id)
        except Quote.DoesNotExist:
            return None

        if quote.status == "quoted":
            return PolicyService.create_payment_link(
                CreatePaymentLinkInput(
                    quote=quote,
                    billing_frequency=billing_frequency,
                    effective_date=effective_date,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            )

        if quote.status == "needs_review" and coverages:
            return PolicyService.create_payment_link(
                CreatePaymentLinkInput(
                    quote=quote,
                    billing_frequency=billing_frequency,
                    effective_date=effective_date,
                    coverages=coverages,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            )

        if quote.status == "needs_review" and quote.custom_products.exists():
            breakdown = (quote.rating_result or {}).get("breakdown", {})
            rated_coverages = [
                c for c in quote.coverages if breakdown.get(c, {}).get("premium", 0) > 0
            ]
            fulfilled_brokered_types = set(
                quote.custom_products.filter(price__gt=0).values_list(
                    "product_type", flat=True
                )
            )
            fulfilled_brokered = [
                c for c in quote.coverages if c in fulfilled_brokered_types
            ]
            payable_coverages = rated_coverages + fulfilled_brokered
            return PolicyService.create_payment_link(
                CreatePaymentLinkInput(
                    quote=quote,
                    billing_frequency=billing_frequency,
                    effective_date=effective_date,
                    coverages=payable_coverages,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            )

        return None

    @staticmethod
    @transaction.atomic
    def move_quote_to_org(quote_number: str, target_org_id: int, user) -> Quote:
        if not OrganizationService.can_edit(user):
            raise AccessDeniedError("You do not have permission to move quotes")

        source_org_id = OrganizationService.get_active_org_id(user)
        quote = Quote.objects.get(
            quote_number=quote_number, organization_id=source_org_id
        )

        membership = OrganizationMember.objects.filter(
            user=user, organization_id=target_org_id
        ).first()
        if not membership or membership.role == "viewer":
            raise AccessDeniedError(
                "You do not have edit permission in the target organization"
            )

        quote.organization_id = target_org_id
        quote.save(update_fields=["organization_id"])
        return quote
