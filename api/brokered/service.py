"""
Brokered coverage service for non-instant quote flows.

Handles Workers' Compensation automation via Skyvern Cloud (Pie Insurance
portal automation) and processes callbacks from Skyvern workflows.

Flow:
    1. ``trigger_workers_compensation()`` — Creates BrokeredQuoteRequest and
       kicks off Skyvern workflow.
    2. ``workers_compensation_callback()`` — Receives quote/decline result
       from Skyvern, creates CustomProduct if quoted.
    3. ``workers_compensation_run_status()`` — Handles Skyvern lifecycle
       events (failed, cancelled, etc.).
"""

from datetime import date, timedelta

from brokered.constants import (
    DEFAULT_NCCI_CLASS_CODE,
    PIE_CREDENTIAL_ID,
    WORKERS_COMPENSATION_WORKFLOW_ID,
)
from brokered.models import BrokeredQuoteRequest
from brokered.schemas import (
    WorkersCompWebhookSchema,
    WorkersCompFormPayload,
    SkyvernRunWebhookSchema,
)
from quotes.models import CustomProduct, Quote
from skyvern.service import SkyvernService


class BrokeredService:
    @staticmethod
    def trigger_workers_compensation(quote: Quote) -> None:
        existing = BrokeredQuoteRequest.objects.filter(
            quote=quote,
            coverage_type="custom-workers-comp",
        ).first()
        if existing and existing.status in {
            BrokeredQuoteRequest.Status.IN_PROGRESS,
            BrokeredQuoteRequest.Status.QUOTED,
        }:
            return

        company = quote.company
        address = company.business_address
        year_established = (
            company.business_start_date.year if company.business_start_date else None
        )

        form_payload: WorkersCompFormPayload = {
            "quote_number": quote.quote_number,
            "credential": PIE_CREDENTIAL_ID,
            "policy_effective_date": (date.today() + timedelta(days=15)).strftime(
                "%m/%d/%Y"
            ),
            "zip_code": int(address.zip),
            "business_legal_name": company.entity_legal_name,
            "entity_type": company.type,
            "fein": company.federal_ein,
            "class_code": DEFAULT_NCCI_CLASS_CODE,
            "full_time_employees": company.full_time_employees or 0,
            "part_time_employees": company.part_time_employees or 0,
            "annual_payroll": str(company.estimated_payroll)
            if company.estimated_payroll is not None
            else None,
            "year_established": year_established,
            "current_year": str(date.today().year),
            "business_description": company.business_description,
        }

        bq_request, _ = BrokeredQuoteRequest.objects.update_or_create(
            quote=quote,
            coverage_type="custom-workers-comp",
            defaults={
                "carrier": "Pie Insurance",
                "form_payload": form_payload,
                "status": BrokeredQuoteRequest.Status.PENDING,
                "run_id": None,
                "premium_amount": None,
                "decline_reason": None,
                "quote_url": None,
            },
        )

        try:
            run_id = SkyvernService.run_workflow(
                workflow_id=WORKERS_COMPENSATION_WORKFLOW_ID,
                parameters=form_payload,
            )
            bq_request.status = BrokeredQuoteRequest.Status.IN_PROGRESS
            bq_request.run_id = run_id
        except Exception:
            bq_request.status = BrokeredQuoteRequest.Status.FAILED
        bq_request.save(update_fields=["status", "run_id", "updated_at"])

    @staticmethod
    def workers_compensation_callback(
        quote_number: str, data: WorkersCompWebhookSchema
    ) -> tuple[int, dict]:
        status = (
            BrokeredQuoteRequest.Status.QUOTED
            if data.status == "quoted"
            else BrokeredQuoteRequest.Status.DECLINED
        )

        quote = Quote.objects.filter(quote_number=quote_number).first()
        if not quote:
            return 404, {"success": False, "message": "Quote not found", "data": None}

        bq_request = BrokeredQuoteRequest.objects.filter(
            quote=quote, coverage_type="custom-workers-comp"
        ).first()
        if not bq_request:
            return 404, {
                "success": False,
                "message": "Workers comp quote request not found",
                "data": None,
            }

        bq_request.status = status
        bq_request.premium_amount = data.premium_amount
        bq_request.decline_reason = (
            data.decline_reason if data.decline_reason != "None" else None
        )
        bq_request.quote_url = data.quote_url
        bq_request.save(
            update_fields=[
                "status",
                "premium_amount",
                "decline_reason",
                "quote_url",
                "updated_at",
            ]
        )

        if status == BrokeredQuoteRequest.Status.QUOTED and data.premium_amount:
            CustomProduct.objects.update_or_create(
                quote=quote,
                product_type="custom-workers-comp",
                defaults={
                    "name": "Workers Compensation",
                    "price": data.premium_amount,
                    "carrier": "Pie Insurance",
                    "fulfills_coverage": "custom-workers-comp",
                },
            )

        return 200, {"success": True, "message": "Callback processed", "data": None}

    @staticmethod
    def workers_compensation_run_status(
        data: SkyvernRunWebhookSchema,
    ) -> tuple[int, dict]:
        bq_request = BrokeredQuoteRequest.objects.filter(
            run_id=data.workflow_run_id,
            coverage_type="custom-workers-comp",
        ).first()
        if not bq_request:
            return 404, {
                "success": False,
                "message": "Workers comp quote request not found",
                "data": None,
            }

        terminal_statuses = {
            BrokeredQuoteRequest.Status.QUOTED,
            BrokeredQuoteRequest.Status.DECLINED,
        }
        if bq_request.status in terminal_statuses:
            return 200, {"success": True, "message": "No update needed", "data": None}

        skyvern_failed = data.status in {
            "failed",
            "cancelled",
            "timed_out",
            "terminated",
        }
        skyvern_completed = data.status == "completed"

        if skyvern_failed or skyvern_completed:
            bq_request.status = BrokeredQuoteRequest.Status.FAILED
            bq_request.decline_reason = data.failure_reason
            bq_request.save(update_fields=["status", "decline_reason", "updated_at"])

        return 200, {"success": True, "message": "Run status processed", "data": None}
