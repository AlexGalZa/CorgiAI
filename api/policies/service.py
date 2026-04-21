"""
Policy service layer for the Corgi Insurance platform.

Manages the full policy lifecycle: creation from checkout, carrier
selection, document generation, endorsements (modify limits, add/remove
coverage, backdate), cancellations, reactivations, and billing portal
access. Handles Stripe payment processing for all policy actions.

Key responsibilities:
- Policy creation from Stripe checkout/subscription events.
- Regulatory field denormalization (insured name, FEIN, address, state).
- PolicyTransaction + StateAllocation + Cession creation.
- Midterm endorsements with prorated Stripe charges/refunds.
- COI and policy document generation and S3 upload.
- Welcome and cancellation email sending.
"""

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string

from s3.service import S3Service
from s3.schemas import UploadFileInput
from stripe_integration.service import StripeService
from stripe_integration.schemas import (
    CreateDirectSubscriptionInput,
    CreateMultiLineCheckoutInput,
    CreateMultiLineSubscriptionCheckoutInput,
    CreateOneTimeCheckoutInput,
    CreateSubscriptionCheckoutInput,
    GetOrCreateCustomerInput,
    LineItemInput,
    RecurringLineItemInput,
)
from policies.models import (
    Cession,
    Payment,
    Policy,
    PolicyTransaction,
    StateAllocation,
    SurplusLinesFiling,
)
from policies.sequences import generate_coi_number
from users.models import UserDocument
from policies.schemas import CreatePaymentLinkInput
from documents_generator.service import DocumentsGeneratorService
from common.constants import (
    ADMIN_FEE_RATE,
    ADMIN_FEE_RECIPIENT,
    ALL_COVERAGES,
    CGL_COVERAGE,
    COLLECTOR_ENTITY,
    COVERAGE_DISPLAY_NAMES,
    DEFAULT_ATTACHMENT_POINT,
    DEFAULT_CEDED_PREMIUM_RATE,
    DEFAULT_REINSURANCE_TYPE,
    DEFAULT_REINSURER_NAME,
    DEFAULT_TREATY_ID,
    HNOA_COVERAGE,
    NTIC_CARRIER,
    NTIC_LIMIT_THRESHOLD,
    TECHRRG_CARRIER,
)
from rating.constants import (
    STATE_TAX_RATES,
    SURPLUS_LINES_TAX_RATES,
    SURPLUS_LINES_FILING_DEADLINES,
    SURPLUS_LINES_STAMPING_OFFICES,
)
from common.exceptions import AccessDeniedError
from organizations.service import OrganizationService
from emails.service import EmailService
from emails.schemas import SendEmailInput
from rating.service import RatingService

logger = logging.getLogger(__name__)


class PolicyService:
    @staticmethod
    def get_carrier_for_quote(quote) -> str:
        """Return the carrier for the whole quote (used for COI-level decisions).
        Returns NTIC if ANY coverage has aggregate > threshold."""
        all_limits = quote.limits_retentions or {}
        for coverage_limits in all_limits.values():
            if isinstance(coverage_limits, dict):
                aggregate = (
                    coverage_limits.get("aggregate_limit")
                    or coverage_limits.get("aggregateLimit")
                    or 0
                )
                if aggregate > NTIC_LIMIT_THRESHOLD:
                    return NTIC_CARRIER
        return TECHRRG_CARRIER

    @staticmethod
    def get_carrier_for_coverage(coverage_limits: dict) -> str:
        """Return the carrier for a single coverage based on its own aggregate limit."""
        if not isinstance(coverage_limits, dict):
            return TECHRRG_CARRIER
        aggregate = (
            coverage_limits.get("aggregate_limit")
            or coverage_limits.get("aggregateLimit")
            or 0
        )
        return NTIC_CARRIER if aggregate > NTIC_LIMIT_THRESHOLD else TECHRRG_CARRIER

    @staticmethod
    def get_carrier_for_coi(policy: "Policy", new_limits: dict = None) -> str:
        """Return the carrier for a COI. NTIC if any sibling policy is NTIC or force_ntic."""
        sibling_policies = Policy.objects.filter(
            coi_number=policy.coi_number, is_brokered=False
        )
        for p in sibling_policies:
            # force_ntic flag overrides the threshold check
            if getattr(p, "force_ntic", False):
                return NTIC_CARRIER
            limits = new_limits if p.pk == policy.pk else (p.limits_retentions or {})
            aggregate = (
                limits.get("aggregate_limit") or limits.get("aggregateLimit") or 0
            )
            if aggregate > NTIC_LIMIT_THRESHOLD:
                return NTIC_CARRIER
        return TECHRRG_CARRIER

    @staticmethod
    def _get_checkout_context(input: CreatePaymentLinkInput):
        quote = input.quote
        quote.refresh_from_db()
        custom_products = list(quote.custom_products.all())
        effective_date = input.effective_date or date.today()
        return {
            "quote": quote,
            "success_url": input.success_url or settings.STRIPE_SUCCESS_URL,
            "cancel_url": input.cancel_url or settings.STRIPE_CANCEL_URL,
            "customer": StripeService.get_or_create_customer(
                GetOrCreateCustomerInput(
                    email=quote.user.email,
                    name=quote.user.get_full_name(),
                    metadata={
                        "user_id": str(quote.user.id),
                        "company_name": quote.company.entity_legal_name or "",
                    },
                )
            ),
            "custom_products": custom_products,
            "promo": StripeService.get_promotion_code(quote.promo_code)
            if quote.promo_code
            else None,
            "effective_date": effective_date,
            "coverages": input.coverages,
        }

    @staticmethod
    def _build_checkout_url(base_url: str, quote_number: str) -> str:
        return f"{base_url}?quote={quote_number}&session_id={{CHECKOUT_SESSION_ID}}"

    @staticmethod
    def _quote_metadata(
        quote, billing_frequency: str, effective_date: date = None, extra: dict = None
    ) -> dict:
        meta = {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "billing_frequency": billing_frequency,
            "effective_date": effective_date.isoformat()
            if effective_date
            else date.today().isoformat(),
            "carrier": PolicyService.get_carrier_for_quote(quote),
        }
        if extra:
            meta.update(extra)
        return meta

    @staticmethod
    def _quote_product_metadata(quote) -> dict:
        # Carrier tag lets finance filter Stripe objects by TechRRG / NTIC
        # without joining back to Django. Brokered routing is per-policy, so
        # we stamp the computed quote-level carrier here and leave the
        # `brokered` flag for the bind path where it's authoritative.
        return {
            "quote_id": str(quote.id),
            "quote_number": quote.quote_number,
            "carrier": PolicyService.get_carrier_for_quote(quote),
        }

    @staticmethod
    def build_regulatory_fields(
        quote, billing_frequency: str, effective_date, expiration_date
    ) -> dict:
        company = quote.company
        addr = company.business_address

        if billing_frequency == "annual":
            paid_to_date = expiration_date
        else:
            paid_to_date = effective_date + relativedelta(months=1)

        return {
            "insured_legal_name": company.entity_legal_name,
            "insured_fein": company.federal_ein,
            "mailing_address": {
                "street": addr.street_address,
                "suite": addr.suite,
                "city": addr.city,
                "state": addr.state,
                "zip": addr.zip,
            },
            "principal_state": addr.state,
            "paid_to_date": paid_to_date,
        }

    @staticmethod
    def create_payment_link(input: CreatePaymentLinkInput) -> str:
        if input.billing_frequency == "monthly":
            return PolicyService._create_monthly_checkout(input)
        return PolicyService._create_annual_checkout(input)

    @staticmethod
    def _get_coverage_breakdown(
        quote, promo, coverages: list[str] = None
    ) -> list[dict]:
        breakdown = (quote.rating_result or {}).get("breakdown") or {}
        target_coverages = coverages if coverages is not None else quote.coverages
        items = []
        for coverage in target_coverages:
            coverage_data = breakdown.get(coverage, {})
            premium = float(coverage_data.get("premium", 0))
            if premium > 0:
                discounted = RatingService.apply_promo_discount(premium, promo)
                items.append(
                    {
                        "coverage": coverage,
                        "name": COVERAGE_DISPLAY_NAMES.get(coverage, coverage),
                        "premium": discounted,
                    }
                )
        return items

    @staticmethod
    def _create_annual_checkout(input: CreatePaymentLinkInput) -> str:
        ctx = PolicyService._get_checkout_context(input)
        quote, customer, promo = ctx["quote"], ctx["customer"], ctx["promo"]
        effective_date = ctx["effective_date"]
        coverages = ctx["coverages"]
        success_url = PolicyService._build_checkout_url(
            ctx["success_url"], quote.quote_number
        )

        extra_meta = (
            {"partial_coverages": ",".join(coverages)}
            if coverages is not None
            else None
        )
        coverage_items = PolicyService._get_coverage_breakdown(quote, promo, coverages)

        if not ctx["custom_products"] and len(coverage_items) == 1:
            item = coverage_items[0]
            return StripeService.create_one_time_checkout(
                CreateOneTimeCheckoutInput(
                    customer_id=customer.id,
                    amount_cents=int(item["premium"] * 100),
                    product_name=item["name"],
                    success_url=success_url,
                    cancel_url=ctx["cancel_url"],
                    metadata=PolicyService._quote_metadata(
                        quote, "annual", effective_date, extra_meta
                    ),
                    product_metadata=PolicyService._quote_product_metadata(quote),
                )
            )

        line_items = []
        for item in coverage_items:
            line_items.append(
                StripeService.build_line_item(
                    LineItemInput(
                        name=item["name"],
                        amount_cents=int(item["premium"] * 100),
                        metadata={
                            "quote_id": str(quote.id),
                            "type": "coverage",
                            "coverage": item["coverage"],
                            "carrier": PolicyService.get_carrier_for_coverage(
                                (quote.limits_retentions or {}).get(
                                    item["coverage"], {}
                                )
                            ),
                        },
                    )
                )
            )
        for product in ctx["custom_products"]:
            line_items.append(
                StripeService.build_line_item(
                    LineItemInput(
                        name=product.name,
                        amount_cents=int(product.price * 100),
                        metadata={
                            "quote_id": str(quote.id),
                            "type": "custom_product",
                            "product_id": str(product.id),
                        },
                    )
                )
            )

        return StripeService.create_multi_line_checkout(
            CreateMultiLineCheckoutInput(
                customer_id=customer.id,
                line_items=line_items,
                success_url=success_url,
                cancel_url=ctx["cancel_url"],
                metadata=PolicyService._quote_metadata(
                    quote, "annual", effective_date, extra_meta
                ),
            )
        )

    @staticmethod
    def _create_monthly_checkout(input: CreatePaymentLinkInput) -> str:
        ctx = PolicyService._get_checkout_context(input)
        quote, customer, promo = ctx["quote"], ctx["customer"], ctx["promo"]
        effective_date = ctx["effective_date"]
        coverages = ctx["coverages"]
        success_url = PolicyService._build_checkout_url(
            ctx["success_url"], quote.quote_number
        )
        product_meta = PolicyService._quote_product_metadata(quote)
        price_meta = {**product_meta, "billing_type": "monthly"}

        trial_end = None
        if effective_date > date.today():
            effective_datetime = datetime.combine(effective_date, time(12, 0, 0))
            min_trial_end = datetime.now() + timedelta(hours=48)
            if effective_datetime < min_trial_end:
                effective_datetime = min_trial_end
            trial_end = int(effective_datetime.timestamp())

        extra_meta = (
            {"partial_coverages": ",".join(coverages)}
            if coverages is not None
            else None
        )
        coverage_items = PolicyService._get_coverage_breakdown(quote, promo, coverages)

        if not ctx["custom_products"] and len(coverage_items) == 1:
            item = coverage_items[0]
            amounts = RatingService.calculate_billing_amounts(
                item["premium"], "monthly"
            )
            monthly_amount_cents = round(float(amounts["monthly"]) * 100)
            return StripeService.create_subscription_checkout(
                CreateSubscriptionCheckoutInput(
                    customer_id=customer.id,
                    amount_cents=monthly_amount_cents,
                    product_name=item["name"],
                    success_url=success_url,
                    cancel_url=ctx["cancel_url"],
                    interval="month",
                    interval_count=1,
                    metadata=PolicyService._quote_metadata(
                        quote, "monthly", effective_date, extra_meta
                    ),
                    product_metadata=product_meta,
                    price_metadata=price_meta,
                    subscription_metadata=product_meta,
                    trial_end=trial_end,
                )
            )

        line_items = []
        for item in coverage_items:
            amounts = RatingService.calculate_billing_amounts(
                item["premium"], "monthly"
            )
            monthly_cents = round(float(amounts["monthly"]) * 100)
            line_items.append(
                RecurringLineItemInput(
                    name=item["name"],
                    amount_cents=monthly_cents,
                    interval="month",
                    interval_count=1,
                    metadata={
                        "quote_id": str(quote.id),
                        "type": "coverage",
                        "coverage": item["coverage"],
                        "carrier": PolicyService.get_carrier_for_coverage(
                            (quote.limits_retentions or {}).get(item["coverage"], {})
                        ),
                    },
                )
            )

        for product in ctx["custom_products"]:
            monthly_product_cents = round(float(product.price) / 12 * 100)
            line_items.append(
                RecurringLineItemInput(
                    name=product.name,
                    amount_cents=monthly_product_cents,
                    interval="month",
                    interval_count=1,
                    metadata={
                        "quote_id": str(quote.id),
                        "type": "custom_product",
                        "product_id": str(product.id),
                    },
                )
            )

        return StripeService.create_multi_line_subscription_checkout(
            CreateMultiLineSubscriptionCheckoutInput(
                customer_id=customer.id,
                line_items=line_items,
                success_url=success_url,
                cancel_url=ctx["cancel_url"],
                metadata=PolicyService._quote_metadata(
                    quote, "monthly", effective_date, extra_meta
                ),
                subscription_metadata=product_meta,
                trial_end=trial_end,
            )
        )

    @staticmethod
    def generate_documents_and_send_email(policies: list[Policy], coi_number: str):
        if not policies:
            return

        first_policy = policies[0]
        user = first_policy.quote.user
        quote = first_policy.quote
        organization = quote.organization

        coi_bytes = DocumentsGeneratorService.generate_coi_for_policies(
            policies, coi_number
        )
        if coi_bytes:
            PolicyService._upload_and_store_coi_document(
                first_policy, user, coi_bytes, coi_number, organization
            )

        policy_documents = PolicyService._generate_and_store_policy_documents(
            first_policy, user, policies, organization
        )

        for custom_product in quote.custom_products.all():
            if custom_product.s3_key:
                brokered_policy = next(
                    (
                        p
                        for p in policies
                        if p.is_brokered
                        and p.coverage_type == custom_product.product_type
                    ),
                    None,
                )
                if brokered_policy:
                    UserDocument.objects.create(
                        user=user,
                        organization=organization,
                        category="policy",
                        title=custom_product.name,
                        policy_numbers=[brokered_policy.policy_number],
                        effective_date=brokered_policy.effective_date,
                        expiration_date=brokered_policy.expiration_date,
                        file_type="custom-product",
                        original_filename=custom_product.original_filename,
                        file_size=custom_product.file_size,
                        mime_type=custom_product.mime_type,
                        s3_key=custom_product.s3_key,
                        s3_url=custom_product.s3_url,
                    )

        PolicyService._send_welcome_email(
            policies, coi_bytes, coi_number, policy_documents
        )

    @staticmethod
    def _upload_and_store_document(
        policy: Policy,
        user,
        pdf_bytes: bytes,
        title: str,
        file_type: str,
        category: str = "policy",
        policy_numbers: list[str] = None,
        organization=None,
    ) -> str | None:
        filename = f"{title} - {policy.policy_number}.pdf"
        result = S3Service.upload_file(
            UploadFileInput(
                file=BytesIO(pdf_bytes),
                path_prefix=f"policies/{policy.id}/documents",
                original_filename=filename,
                content_type="application/pdf",
            )
        )
        if result:
            doc_kwargs = dict(
                user=user,
                category=category,
                title=title,
                policy_numbers=policy_numbers or [policy.policy_number],
                effective_date=policy.effective_date,
                expiration_date=policy.expiration_date,
                file_type=file_type,
                original_filename=filename,
                file_size=len(pdf_bytes),
                mime_type="application/pdf",
                s3_key=result["s3_key"],
                s3_url=result["s3_url"],
            )
            if organization:
                doc_kwargs["organization"] = organization
            UserDocument.objects.create(**doc_kwargs)
        return filename

    @staticmethod
    def _upload_and_store_coi_document(
        policy: Policy, user, pdf_bytes: bytes, coi_number: str, organization=None
    ) -> str | None:
        filename = f"Certificate of Insurance - {coi_number}.pdf"
        result = S3Service.upload_file(
            UploadFileInput(
                file=BytesIO(pdf_bytes),
                path_prefix=f"policies/{policy.id}/documents",
                original_filename=filename,
                content_type="application/pdf",
            )
        )
        if result:
            doc_kwargs = dict(
                user=user,
                category="certificate",
                title="Certificate of Insurance",
                policy_numbers=[coi_number],
                effective_date=policy.effective_date,
                expiration_date=policy.expiration_date,
                file_type="certificate-of-insurance",
                original_filename=filename,
                file_size=len(pdf_bytes),
                mime_type="application/pdf",
                s3_key=result["s3_key"],
                s3_url=result["s3_url"],
            )
            if organization:
                doc_kwargs["organization"] = organization
            UserDocument.objects.create(**doc_kwargs)
        return filename

    @staticmethod
    def _generate_and_store_policy_documents(
        policy: Policy, user, all_policies: list[Policy] = None, organization=None
    ) -> list[tuple[str, bytes]]:
        documents = []

        cgl_coverages = {CGL_COVERAGE, HNOA_COVERAGE}
        policies = all_policies or [policy]
        non_brokered_policies = [p for p in policies if not p.is_brokered]

        techrrg_cgl_policies = [
            p
            for p in policies
            if p.coverage_type in cgl_coverages and p.carrier != NTIC_CARRIER
        ]
        if techrrg_cgl_policies:
            cgl_anchor = min(techrrg_cgl_policies, key=lambda p: p.effective_date)
            cgl_bytes = DocumentsGeneratorService.generate_cgl_policy_for_policy(
                cgl_anchor, all_policies
            )
            if cgl_bytes:
                cgl_policy_numbers = [
                    p.policy_number
                    for p in non_brokered_policies
                    if p.coverage_type in cgl_coverages and p.carrier != NTIC_CARRIER
                ]
                filename = PolicyService._upload_and_store_document(
                    cgl_anchor,
                    user,
                    cgl_bytes,
                    "CGL Policy",
                    "cgl-policy",
                    policy_numbers=cgl_policy_numbers or [policy.policy_number],
                    organization=organization,
                )
                documents.append((filename, cgl_bytes))

        non_cgl_non_brokered = [
            p
            for p in policies
            if p.coverage_type not in cgl_coverages and not p.is_brokered
        ]

        techrrg_policies = [
            p for p in non_cgl_non_brokered if p.carrier != NTIC_CARRIER
        ]
        if techrrg_policies:
            tech_policy = min(techrrg_policies, key=lambda p: p.effective_date)
            tech_bytes = DocumentsGeneratorService.generate_tech_policy_for_policy(
                tech_policy, all_policies
            )
            if tech_bytes:
                tech_policy_numbers = [p.policy_number for p in techrrg_policies]
                filename = PolicyService._upload_and_store_document(
                    tech_policy,
                    user,
                    tech_bytes,
                    "Tech Policy",
                    "tech-policy",
                    policy_numbers=tech_policy_numbers or [policy.policy_number],
                    organization=organization,
                )
                documents.append((filename, tech_bytes))

        ntic_cgl_policies = [
            p
            for p in policies
            if p.coverage_type in cgl_coverages and p.carrier == NTIC_CARRIER
        ]
        if ntic_cgl_policies:
            ntic_cgl_anchor = min(ntic_cgl_policies, key=lambda p: p.effective_date)
            ntic_cgl_bytes = (
                DocumentsGeneratorService.generate_ntic_cgl_policy_for_policy(
                    ntic_cgl_anchor, all_policies
                )
            )
            if ntic_cgl_bytes:
                ntic_cgl_policy_numbers = [p.policy_number for p in ntic_cgl_policies]
                filename = PolicyService._upload_and_store_document(
                    ntic_cgl_anchor,
                    user,
                    ntic_cgl_bytes,
                    "CGL Policy",
                    "ntic-cgl-policy",
                    policy_numbers=ntic_cgl_policy_numbers or [policy.policy_number],
                    organization=organization,
                )
                documents.append((filename, ntic_cgl_bytes))

        ntic_tech_policies = [
            p for p in non_cgl_non_brokered if p.carrier == NTIC_CARRIER
        ]
        if ntic_tech_policies:
            ntic_tech_policy = min(ntic_tech_policies, key=lambda p: p.effective_date)
            ntic_tech_bytes = (
                DocumentsGeneratorService.generate_ntic_tech_policy_for_policy(
                    ntic_tech_policy, all_policies
                )
            )
            if ntic_tech_bytes:
                ntic_tech_policy_numbers = [p.policy_number for p in ntic_tech_policies]
                filename = PolicyService._upload_and_store_document(
                    ntic_tech_policy,
                    user,
                    ntic_tech_bytes,
                    "Tech Policy",
                    "ntic-tech-policy",
                    policy_numbers=ntic_tech_policy_numbers or [policy.policy_number],
                    organization=organization,
                )
                documents.append((filename, ntic_tech_bytes))

        return documents

    @staticmethod
    def _send_welcome_email(
        policies: list[Policy],
        coi_bytes: bytes,
        coi_number: str,
        policy_documents: list = None,
    ):
        if not policies:
            return

        first_policy = policies[0]
        quote = first_policy.quote
        policy_numbers = [p.policy_number for p in policies]

        html = render_to_string(
            "emails/welcome.html",
            {
                "company_name": quote.company.entity_legal_name,
                "contact_name": quote.user.get_full_name(),
                "policy_number": coi_number,
                "policy_numbers": policy_numbers,
                "effective_date": first_policy.effective_date.strftime("%B %d, %Y"),
                "expiration_date": first_policy.expiration_date.strftime("%B %d, %Y"),
                "coverages": [COVERAGE_DISPLAY_NAMES[c] for c in quote.coverages],
                "dashboard_url": f"{settings.PORTAL_BASE_URL}/portal",
            },
        )

        attachments = []
        if coi_bytes:
            attachments.append(
                {
                    "filename": f"Certificate of Insurance - {coi_number}.pdf",
                    "content": list(coi_bytes),
                }
            )

        if policy_documents:
            for filename, pdf_bytes in policy_documents:
                attachments.append(
                    {
                        "filename": filename,
                        "content": list(pdf_bytes),
                    }
                )

        EmailService.send(
            SendEmailInput(
                to=[quote.user.email],
                subject=f"🐶 Welcome, {quote.user.get_full_name()}!",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
                attachments=attachments if attachments else None,
            )
        )

    @staticmethod
    def get_policies_for_user(user) -> list[dict]:
        org_id = OrganizationService.get_active_org_id(user)
        policies = Policy.objects.filter(
            quote__organization_id=org_id, status="active"
        ).select_related("quote", "quote__company")
        documents = UserDocument.objects.filter(organization_id=org_id).exclude(
            policy_numbers=[]
        )

        policy_docs_by_type = {}
        certificate_docs_by_number = {}
        custom_product_docs_by_policy = {}
        for doc in documents:
            doc_data = {
                "id": doc.id,
                "title": doc.title,
                "file_type": doc.file_type,
                "original_filename": doc.original_filename,
                "file_size": doc.file_size,
            }
            if doc.category == "certificate":
                for pn in doc.policy_numbers:
                    certificate_docs_by_number.setdefault(pn, []).append(doc_data)
            elif doc.category == "policy" and doc.file_type in (
                "cgl-policy",
                "tech-policy",
                "ntic-cgl-policy",
                "ntic-tech-policy",
            ):
                for pn in doc.policy_numbers:
                    policy_docs_by_type.setdefault(doc.file_type, {}).setdefault(
                        pn, []
                    ).append(doc_data)
            elif doc.file_type == "custom-product":
                for pn in doc.policy_numbers:
                    custom_product_docs_by_policy.setdefault(pn, []).append(doc_data)

        cgl_coverages = {CGL_COVERAGE, HNOA_COVERAGE}

        result = []
        for p in policies:
            if p.is_brokered:
                policy_docs = custom_product_docs_by_policy.get(p.policy_number, [])
            else:
                is_cgl = p.coverage_type in cgl_coverages
                is_ntic = p.carrier == NTIC_CARRIER or getattr(p, "force_ntic", False)
                if is_cgl:
                    file_type = "ntic-cgl-policy" if is_ntic else "cgl-policy"
                else:
                    file_type = "ntic-tech-policy" if is_ntic else "tech-policy"
                docs_by_policy = policy_docs_by_type.get(file_type, {})
                policy_docs = docs_by_policy.get(p.policy_number, [])

            result.append(
                {
                    "id": p.id,
                    "policy_number": p.policy_number,
                    "status": p.status,
                    "coverage_type": p.coverage_type,
                    "coi_number": p.coi_number,
                    "per_occurrence_limit": p.per_occurrence_limit,
                    "aggregate_limit": p.aggregate_limit,
                    "retention": p.retention,
                    "premium": float(p.premium),
                    "monthly_premium": float(p.monthly_premium)
                    if p.monthly_premium
                    else None,
                    "billing_frequency": p.billing_frequency,
                    "effective_date": p.effective_date.isoformat(),
                    "expiration_date": p.expiration_date.isoformat(),
                    "purchased_at": p.purchased_at.isoformat(),
                    "policy_docs": policy_docs,
                    "certificate_docs": certificate_docs_by_number.get(
                        p.coi_number, []
                    ),
                    "is_brokered": p.is_brokered,
                    "carrier": p.carrier,
                    "company_name": p.quote.company.entity_legal_name
                    if p.quote and p.quote.company
                    else None,
                }
            )
        return result

    @staticmethod
    def get_coi_download_url(policy_number: str, user) -> dict:
        org_id = OrganizationService.get_active_org_id(user)
        coi_doc = UserDocument.objects.filter(
            organization_id=org_id,
            policy_numbers__contains=[policy_number],
            file_type="certificate-of-insurance",
        ).first()

        if not coi_doc:
            raise ValueError("Certificate of Insurance not found")

        download_url = S3Service.generate_presigned_url(coi_doc.s3_key)
        return {"download_url": download_url, "filename": coi_doc.original_filename}

    @staticmethod
    def get_recommended_coverages(user) -> list[str]:
        org_id = OrganizationService.get_active_org_id(user)
        policies = Policy.objects.filter(quote__organization_id=org_id)
        owned_coverages = set()
        for policy in policies:
            if policy.coverage_type:
                owned_coverages.add(policy.coverage_type)

        instant_coverages = [c for c in ALL_COVERAGES if not c.startswith("custom-")]
        return [c for c in instant_coverages if c not in owned_coverages][:2]

    @staticmethod
    def _get_stripe_customer_id(user) -> str | None:
        policy = Policy.objects.filter(
            quote__user=user, stripe_customer_id__isnull=False
        ).first()

        if policy and policy.stripe_customer_id:
            return policy.stripe_customer_id

        client = StripeService.get_client()
        customers = client.Customer.list(email=user.email, limit=1)
        if customers.data:
            return customers.data[0].id

        return None

    @staticmethod
    def get_billing_info(user) -> dict:
        if not OrganizationService.can_access_billing(user):
            raise AccessDeniedError("You do not have permission to access billing")

        customer_id = PolicyService._get_stripe_customer_id(user)
        if not customer_id:
            return {
                "has_billing": False,
                "payment_method": None,
                "payment_plans": [],
                "payment_history": [],
            }

        client = StripeService.get_client()

        payment_method = None
        try:
            customer = client.Customer.retrieve(customer_id)
            default_pm_id = getattr(
                customer.invoice_settings, "default_payment_method", None
            )

            if default_pm_id:
                pm = client.PaymentMethod.retrieve(default_pm_id)
                if pm.type == "card" and pm.card:
                    payment_method = {
                        "type": "card",
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    }
                elif pm.type == "link":
                    payment_method = {
                        "type": "link",
                        "brand": "link",
                        "last4": None,
                        "exp_month": None,
                        "exp_year": None,
                    }

            if not payment_method:
                payment_methods = client.PaymentMethod.list(
                    customer=customer_id, limit=1
                )
                if payment_methods.data:
                    pm = payment_methods.data[0]
                    if pm.type == "card" and pm.card:
                        payment_method = {
                            "type": "card",
                            "brand": pm.card.brand,
                            "last4": pm.card.last4,
                            "exp_month": pm.card.exp_month,
                            "exp_year": pm.card.exp_year,
                        }
                    elif pm.type == "link":
                        payment_method = {
                            "type": "link",
                            "brand": "link",
                            "last4": None,
                            "exp_month": None,
                            "exp_year": None,
                        }
        except Exception as e:
            logger.warning(f"Failed to fetch payment methods: {e}")

        org_id = OrganizationService.get_active_org_id(user)
        policies = Policy.objects.filter(quote__organization_id=org_id, status="active")
        payment_plans = []
        for policy in policies:
            payment_plans.append(
                {
                    "policy_number": policy.policy_number,
                    "coverage_type": policy.coverage_type,
                    "billing_frequency": policy.billing_frequency,
                    "premium": float(policy.premium),
                    "monthly_premium": float(policy.monthly_premium)
                    if policy.monthly_premium
                    else None,
                }
            )

        payment_history = []
        try:
            charges = client.Charge.list(customer=customer_id, limit=20)
            for charge in charges.data:
                if charge.status == "succeeded":
                    payment_history.append(
                        {
                            "id": charge.id,
                            "amount": charge.amount / 100,
                            "date": datetime.fromtimestamp(charge.created).isoformat(),
                            "receipt_url": charge.receipt_url,
                            "description": charge.description or "Insurance Payment",
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch charges: {e}")

        return {
            "has_billing": True,
            "payment_method": payment_method,
            "payment_plans": payment_plans,
            "payment_history": payment_history,
        }

    @staticmethod
    def get_billing_portal_url(user) -> str | None:
        if not OrganizationService.can_access_billing(user):
            return None

        customer_id = PolicyService._get_stripe_customer_id(user)
        if not customer_id:
            return None

        return_url = f"{settings.PORTAL_BASE_URL}/portal/billing"
        return StripeService.create_billing_portal_session(customer_id, return_url)

    @staticmethod
    def apply_promo_to_policy(policy: Policy, promo) -> dict:
        if policy.is_brokered:
            raise ValueError("Cannot apply promo codes to brokered policies.")

        if policy.promo_code:
            raise ValueError(
                "Policy already has a promo code applied. Remove it first."
            )

        coupon = promo.coupon
        if not getattr(coupon, "percent_off", None):
            raise ValueError("Only percentage-based promo codes are supported.")

        discount_pct = Decimal(str(coupon.percent_off))
        old_premium = policy.premium
        new_premium = (old_premium * (1 - discount_pct / 100)).quantize(Decimal("0.01"))
        delta = new_premium - old_premium

        policy.promo_code = promo.code
        policy.discount_percentage = discount_pct
        policy.premium = new_premium

        if policy.billing_frequency == "monthly":
            policy.monthly_premium = (new_premium / 12).quantize(Decimal("0.01"))

            if policy.stripe_subscription_id:
                new_monthly_cents = round(float(policy.monthly_premium) * 100)
                StripeService.update_subscription_price(
                    policy.stripe_subscription_id,
                    new_monthly_cents,
                    policy.coverage_type,
                )
        else:
            if policy.stripe_payment_intent_id:
                refund_cents = round(float(abs(delta)) * 100)
                StripeService.create_refund(
                    policy.stripe_payment_intent_id, refund_cents
                )

        policy.save()

        payment_amount = (
            policy.monthly_premium
            if policy.billing_frequency == "monthly"
            else new_premium
        )
        Payment.objects.filter(policy=policy).update(amount=payment_amount)

        PolicyService._create_endorsement_transaction(
            policy,
            delta,
            description=f"Promo code '{promo.code}' applied: ${old_premium} → ${new_premium}",
        )

        return {
            "old_premium": old_premium,
            "new_premium": new_premium,
            "delta": delta,
        }

    @staticmethod
    def _create_endorsement_transaction(
        policy: Policy, premium_delta: Decimal, description: str = ""
    ) -> PolicyTransaction:
        state = policy.quote.company.business_address.state
        accounting_date = date.today()

        tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        gwp_delta = (premium_delta / tax_multiplier).quantize(Decimal("0.01"))
        tax_delta = (premium_delta - gwp_delta).quantize(Decimal("0.01"))

        admin_fee_rate = Decimal(ADMIN_FEE_RATE)
        admin_fee_delta = (gwp_delta * admin_fee_rate).quantize(Decimal("0.01"))

        transaction = PolicyTransaction.objects.create(
            policy=policy,
            transaction_type="endorsement",
            effective_date=date.today(),
            accounting_date=accounting_date,
            gross_written_premium=gwp_delta,
            tax_amount=tax_delta,
            tax_rate=tax_multiplier,
            taxes_assessments_delta=tax_delta if tax_delta != 0 else None,
            total_billed_delta=premium_delta,
            admin_fee_rate=admin_fee_rate,
            admin_fee_amount=admin_fee_delta,
            admin_fee_recipient_entity=ADMIN_FEE_RECIPIENT,
            description=description or None,
        )

        state_tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        allocated_taxes = None
        if state_tax_rate > 1:
            allocated_taxes = (gwp_delta * (state_tax_rate - 1)).quantize(
                Decimal("0.01")
            )

        StateAllocation.objects.create(
            transaction=transaction,
            state=state,
            allocation_method="hq",
            allocation_percent=Decimal("1.0000"),
            allocated_premium=gwp_delta,
            allocated_taxes=allocated_taxes,
        )

        PolicyService.create_cession_for_transaction(transaction)

        return transaction

    @staticmethod
    def create_cession_for_transaction(transaction: PolicyTransaction):
        if transaction.policy.is_brokered:
            return None
        ceded_premium_amount = (
            transaction.gross_written_premium * Decimal(DEFAULT_CEDED_PREMIUM_RATE)
        ).quantize(Decimal("0.01"))
        return Cession.objects.create(
            transaction=transaction,
            treaty_id=DEFAULT_TREATY_ID,
            reinsurance_type=DEFAULT_REINSURANCE_TYPE,
            attachment_point=Decimal(DEFAULT_ATTACHMENT_POINT),
            ceded_premium_rate=Decimal(DEFAULT_CEDED_PREMIUM_RATE),
            ceded_premium_amount=ceded_premium_amount,
            reinsurer_name=DEFAULT_REINSURER_NAME,
        )

    @staticmethod
    def create_transaction_and_allocation(
        policy: Policy, transaction_type: str = "new"
    ) -> PolicyTransaction:
        state = policy.quote.company.business_address.state
        total_premium = policy.premium
        accounting_date = (
            policy.purchased_at.date() if policy.purchased_at else date.today()
        )

        if policy.is_brokered:
            gwp = total_premium
            tax_amount = Decimal("0")
            tax_multiplier = Decimal("1.0")
            admin_fee_rate = None
            admin_fee_amount = None
            admin_fee_recipient = None
        else:
            tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            gwp = (total_premium / tax_multiplier).quantize(Decimal("0.01"))
            tax_amount = (total_premium - gwp).quantize(Decimal("0.01"))
            admin_fee_rate = Decimal(ADMIN_FEE_RATE)
            admin_fee_amount = (gwp * admin_fee_rate).quantize(Decimal("0.01"))
            admin_fee_recipient = ADMIN_FEE_RECIPIENT

        transaction = PolicyTransaction.objects.create(
            policy=policy,
            transaction_type=transaction_type,
            effective_date=policy.effective_date,
            accounting_date=accounting_date,
            gross_written_premium=gwp,
            tax_amount=tax_amount,
            tax_rate=tax_multiplier,
            taxes_assessments_delta=tax_amount if tax_amount > 0 else None,
            total_billed_delta=total_premium,
            collected_amount=total_premium,
            collected_date=accounting_date,
            collector_entity=COLLECTOR_ENTITY,
            admin_fee_rate=admin_fee_rate,
            admin_fee_amount=admin_fee_amount,
            admin_fee_recipient_entity=admin_fee_recipient,
        )

        state_tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        allocated_taxes = None
        if not policy.is_brokered and state_tax_rate > 1:
            allocated_taxes = (gwp * (state_tax_rate - 1)).quantize(Decimal("0.01"))

        StateAllocation.objects.create(
            transaction=transaction,
            state=state,
            allocation_method="hq",
            allocation_percent=Decimal("1.0000"),
            allocated_premium=gwp,
            allocated_taxes=allocated_taxes,
        )

        PolicyService.create_cession_for_transaction(transaction)

        return transaction

    @staticmethod
    def _calculate_proration_factor(policy: Policy) -> Decimal:
        remaining_days = max((policy.expiration_date - date.today()).days, 0)
        total_days = (policy.expiration_date - policy.effective_date).days
        if total_days <= 0:
            return Decimal("0")
        return (Decimal(remaining_days) / Decimal(total_days)).quantize(
            Decimal("0.0001")
        )

    @staticmethod
    def _regenerate_coi_documents(policies: list[Policy], coi_number: str):
        if not policies:
            return
        first_policy = policies[0]
        user = first_policy.quote.user
        organization = first_policy.quote.organization

        policy_numbers = [p.policy_number for p in policies] + [coi_number]
        UserDocument.objects.filter(
            user=user,
            policy_numbers__overlap=policy_numbers,
            file_type__in=[
                "certificate-of-insurance",
                "cgl-policy",
                "tech-policy",
                "ntic-cgl-policy",
                "ntic-tech-policy",
            ],
        ).delete()

        coi_bytes = DocumentsGeneratorService.generate_coi_for_policies(
            policies, coi_number
        )
        if coi_bytes:
            PolicyService._upload_and_store_coi_document(
                first_policy, user, coi_bytes, coi_number, organization
            )

        PolicyService._generate_and_store_policy_documents(
            first_policy, user, policies, organization
        )

    @staticmethod
    def create_surplus_lines_filing(policy: Policy) -> SurplusLinesFiling | None:
        """
        Auto-create a SurplusLinesFiling record for a non-admitted policy.

        Called after policy creation for brokered policies where surplus lines
        filing may be required. Returns None if the policy is admitted (TechRRG/NTIC)
        or if a filing already exists.
        """
        # Only create for brokered policies (non-admitted carriers)
        if not policy.is_brokered:
            return None

        # Skip if filing already exists
        if SurplusLinesFiling.objects.filter(policy=policy).exists():
            return None

        state = policy.principal_state or (
            policy.quote.company.business_address.state
            if policy.quote.company.business_address
            else None
        )
        if not state:
            return None

        from datetime import timedelta

        tax_rate = SURPLUS_LINES_TAX_RATES.get(state, 0.03)  # default 3%
        tax_amount = policy.premium * Decimal(str(tax_rate))
        deadline_days = SURPLUS_LINES_FILING_DEADLINES.get(
            state, SURPLUS_LINES_FILING_DEADLINES["default"]
        )
        filing_deadline = policy.effective_date + timedelta(days=deadline_days)
        stamping_office = SURPLUS_LINES_STAMPING_OFFICES.get(state)

        return SurplusLinesFiling.objects.create(
            policy=policy,
            status="pending",
            filing_state=state,
            stamping_office=stamping_office,
            surplus_lines_tax_rate=Decimal(str(tax_rate)),
            surplus_lines_tax_amount=tax_amount.quantize(Decimal("0.01")),
            binding_date=policy.effective_date,
            filing_deadline=filing_deadline,
        )

    @staticmethod
    def endorse_modify_limits(
        policy: Policy, new_limits: dict, new_premium: Decimal, admin_reason: str
    ) -> dict:
        if policy.status != "active":
            raise ValueError("Can only endorse active policies.")
        if policy.is_brokered:
            raise ValueError("Cannot endorse brokered policies.")

        old_premium = policy.premium
        full_term_delta = new_premium - old_premium
        proration_factor = PolicyService._calculate_proration_factor(policy)
        prorated_delta = (full_term_delta * proration_factor).quantize(Decimal("0.01"))
        invoice_sent = False

        policy.premium = new_premium
        if policy.billing_frequency == "monthly":
            policy.monthly_premium = (new_premium / 12).quantize(Decimal("0.01"))
        policy.limits_retentions = new_limits
        policy.carrier = PolicyService.get_carrier_for_coi(policy, new_limits)
        policy.save()

        if full_term_delta != 0:
            if policy.billing_frequency == "monthly":
                new_monthly_cents = round(float(policy.monthly_premium) * 100)
                StripeService.update_subscription_price(
                    policy.stripe_subscription_id,
                    new_monthly_cents,
                    policy.coverage_type,
                )
                if full_term_delta > 0:
                    Payment.objects.create(
                        policy=policy,
                        stripe_invoice_id=policy.stripe_subscription_id,
                        amount=prorated_delta,
                        status="paid",
                        paid_at=timezone.now(),
                    )
                elif full_term_delta < 0:
                    Payment.objects.create(
                        policy=policy,
                        stripe_invoice_id=policy.stripe_subscription_id,
                        amount=-abs(prorated_delta),
                        status="refunded",
                        paid_at=timezone.now(),
                    )
            else:
                if full_term_delta > 0:
                    charge_cents = round(float(prorated_delta) * 100)
                    charge_description = (
                        f"Endorsement: limits change on {policy.policy_number}"
                    )
                    charge_metadata = {
                        "policy_id": str(policy.id),
                        "type": "endorsement_charge",
                    }
                    try:
                        pi = StripeService.create_one_time_charge(
                            policy.stripe_customer_id,
                            charge_cents,
                            charge_description,
                            charge_metadata,
                        )
                        Payment.objects.create(
                            policy=policy,
                            stripe_invoice_id=pi.id,
                            amount=prorated_delta,
                            status="paid",
                            paid_at=timezone.now(),
                        )
                    except ValueError:
                        invoice = StripeService.create_and_send_invoice(
                            customer_id=policy.stripe_customer_id,
                            line_items=[
                                {
                                    "amount_cents": charge_cents,
                                    "description": charge_description,
                                    "metadata": charge_metadata,
                                }
                            ],
                            description=charge_description,
                            metadata=charge_metadata,
                        )
                        Payment.objects.create(
                            policy=policy,
                            stripe_invoice_id=invoice.id,
                            amount=prorated_delta,
                            status="pending",
                            paid_at=None,
                        )
                        invoice_sent = True
                elif full_term_delta < 0:
                    refund_cents = round(float(abs(prorated_delta)) * 100)
                    try:
                        refund = StripeService.create_refund(
                            policy.stripe_payment_intent_id, refund_cents
                        )
                        Payment.objects.create(
                            policy=policy,
                            stripe_invoice_id=refund.id,
                            amount=-abs(prorated_delta),
                            status="refunded",
                            paid_at=timezone.now(),
                        )
                    except Exception as e:
                        raise ValueError(f"Refund failed: {e}")

        quote = policy.quote
        quote_limits = quote.limits_retentions or {}
        quote_limits[policy.coverage_type] = new_limits
        quote.limits_retentions = quote_limits
        quote.save(update_fields=["limits_retentions"])

        description = f"Limits modified by admin. Reason: {admin_reason}. Premium: ${old_premium} → ${new_premium}"
        PolicyService._create_endorsement_transaction(
            policy, full_term_delta, description=description
        )

        active_policies = list(
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
        )
        PolicyService._regenerate_coi_documents(active_policies, policy.coi_number)

        return {
            "old_premium": old_premium,
            "new_premium": new_premium,
            "full_term_delta": full_term_delta,
            "prorated_delta": prorated_delta,
            "invoice_sent": invoice_sent,
        }

    @staticmethod
    def create_from_direct_invoice(
        quote, stripe_payment_intent_id: str, stripe_customer_id: str, effective_date
    ) -> list:
        if quote.policies.exists():
            raise ValueError("Quote already has policies.")

        expiration_date = effective_date + timedelta(days=365)
        purchased_at = timezone.now()
        state = quote.company.business_address.state
        coi_number = generate_coi_number(state, effective_date)
        regulatory_fields = PolicyService.build_regulatory_fields(
            quote, "annual", effective_date, expiration_date
        )

        discount_pct = None
        if quote.promo_code:
            try:
                discount_pct = quote.promo_code.coupon.percent_off
            except Exception:
                pass

        breakdown = (quote.rating_result or {}).get("breakdown", {})
        policies = []

        for coverage in quote.coverages:
            premium = Decimal(str(breakdown.get(coverage, {}).get("premium", 0)))
            coverage_limits = quote.limits_retentions.get(coverage, {})
            # Determine carrier per-coverage so policy wording docs use the right template
            per_coverage_carrier = PolicyService.get_carrier_for_coverage(
                coverage_limits
            )
            policy = Policy.objects.create(
                quote=quote,
                coverage_type=coverage,
                coi_number=coi_number,
                limits_retentions=coverage_limits,
                carrier=per_coverage_carrier,
                premium=premium,
                billing_frequency="annual",
                promo_code=quote.promo_code,
                discount_percentage=discount_pct,
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_customer_id=stripe_customer_id,
                status="active",
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(policy)
            policies.append(policy)

        # Auto-create surplus lines filings for brokered policies
        for cp in quote.custom_products.all():
            policy = Policy.objects.create(
                quote=quote,
                coverage_type=cp.product_type,
                coi_number=coi_number,
                limits_retentions={
                    "aggregate_limit": cp.aggregate_limit,
                    "per_occurrence_limit": cp.per_occurrence_limit,
                    "retention": cp.retention,
                },
                premium=Decimal(str(cp.price)),
                billing_frequency="annual",
                effective_date=effective_date,
                expiration_date=expiration_date,
                purchased_at=purchased_at,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_customer_id=stripe_customer_id,
                status="active",
                is_brokered=True,
                carrier=cp.carrier or "",
                **regulatory_fields,
            )
            PolicyService.create_transaction_and_allocation(policy)
            # Auto-create surplus lines filing for brokered policies
            try:
                PolicyService.create_surplus_lines_filing(policy)
            except Exception:
                pass  # Non-fatal — don't block policy creation
            policies.append(policy)

        for policy in policies:
            Payment.objects.create(
                policy=policy,
                stripe_invoice_id=stripe_payment_intent_id,
                amount=policy.premium,
                status="paid",
                paid_at=purchased_at,
            )

        quote.status = "purchased"
        quote.save()

        PolicyService.generate_documents_and_send_email(policies, coi_number)
        return policies

    @staticmethod
    def endorse_add_coverage(
        existing_policy: Policy,
        new_coverage_type: str,
        new_limits: dict,
        new_premium: Decimal,
        admin_reason: str,
        is_brokered: bool = False,
        carrier: str = "",
    ) -> dict:
        if existing_policy.status != "active":
            raise ValueError("Can only add coverage to active policies.")

        existing_coverages = Policy.objects.filter(
            coi_number=existing_policy.coi_number, status="active"
        ).values_list("coverage_type", flat=True)
        if new_coverage_type in existing_coverages:
            raise ValueError(
                f"Coverage '{new_coverage_type}' already exists in this COI group."
            )

        proration_factor = PolicyService._calculate_proration_factor(existing_policy)
        prorated_premium = (new_premium * proration_factor).quantize(Decimal("0.01"))
        invoice_sent = False

        reg_fields = {
            "insured_legal_name": existing_policy.insured_legal_name,
            "insured_fein": existing_policy.insured_fein,
            "mailing_address": existing_policy.mailing_address,
            "principal_state": existing_policy.principal_state,
            "paid_to_date": existing_policy.paid_to_date,
        }

        new_policy = Policy.objects.create(
            quote=existing_policy.quote,
            coverage_type=new_coverage_type,
            coi_number=existing_policy.coi_number,
            limits_retentions=new_limits,
            premium=new_premium,
            effective_date=existing_policy.effective_date,
            expiration_date=existing_policy.expiration_date,
            purchased_at=timezone.now(),
            status="active",
            billing_frequency=existing_policy.billing_frequency,
            monthly_premium=(new_premium / 12).quantize(Decimal("0.01"))
            if existing_policy.billing_frequency == "monthly"
            else None,
            stripe_subscription_id=existing_policy.stripe_subscription_id,
            stripe_customer_id=existing_policy.stripe_customer_id,
            is_brokered=is_brokered,
            carrier=carrier if is_brokered else existing_policy.carrier,
            **reg_fields,
        )

        if existing_policy.billing_frequency == "monthly":
            monthly_cents = round(float(new_policy.monthly_premium) * 100)
            StripeService.add_subscription_items(
                existing_policy.stripe_subscription_id,
                [
                    RecurringLineItemInput(
                        name=COVERAGE_DISPLAY_NAMES.get(
                            new_coverage_type, new_coverage_type
                        ),
                        amount_cents=monthly_cents,
                        interval="month",
                        interval_count=1,
                        metadata={
                            "coverage": new_coverage_type,
                            "policy_id": str(new_policy.id),
                        },
                    )
                ],
            )
            if prorated_premium > 0:
                Payment.objects.create(
                    policy=new_policy,
                    stripe_invoice_id=existing_policy.stripe_subscription_id,
                    amount=prorated_premium,
                    status="paid",
                    paid_at=timezone.now(),
                )
        else:
            charge_cents = round(float(prorated_premium) * 100)
            if charge_cents > 0:
                charge_description = f"New coverage: {COVERAGE_DISPLAY_NAMES.get(new_coverage_type, new_coverage_type)} on COI {existing_policy.coi_number}"
                charge_metadata = {
                    "policy_id": str(new_policy.id),
                    "type": "endorsement_add_coverage",
                }
                try:
                    pi = StripeService.create_one_time_charge(
                        existing_policy.stripe_customer_id,
                        charge_cents,
                        charge_description,
                        charge_metadata,
                    )
                    new_policy.stripe_payment_intent_id = pi.id
                    new_policy.save(update_fields=["stripe_payment_intent_id"])
                    Payment.objects.create(
                        policy=new_policy,
                        stripe_invoice_id=pi.id,
                        amount=prorated_premium,
                        status="paid",
                        paid_at=timezone.now(),
                    )
                except ValueError:
                    invoice = StripeService.create_and_send_invoice(
                        customer_id=existing_policy.stripe_customer_id,
                        line_items=[
                            {
                                "amount_cents": charge_cents,
                                "description": charge_description,
                                "metadata": charge_metadata,
                            }
                        ],
                        description=charge_description,
                        metadata=charge_metadata,
                    )
                    Payment.objects.create(
                        policy=new_policy,
                        stripe_invoice_id=invoice.id,
                        amount=prorated_premium,
                        status="pending",
                        paid_at=None,
                    )
                    invoice_sent = True

        quote = existing_policy.quote
        if new_coverage_type not in (quote.coverages or []):
            quote.coverages = list(quote.coverages or []) + [new_coverage_type]
        quote_limits = quote.limits_retentions or {}
        quote_limits[new_coverage_type] = new_limits
        quote.limits_retentions = quote_limits
        quote.save(update_fields=["coverages", "limits_retentions"])

        description = f"Coverage added: {COVERAGE_DISPLAY_NAMES.get(new_coverage_type, new_coverage_type)}. Reason: {admin_reason}"
        PolicyService.create_transaction_and_allocation(new_policy, "endorsement")
        txn = new_policy.transactions.order_by("-created_at").first()
        if txn:
            txn.description = description
            txn.save(update_fields=["description"])

        if not is_brokered:
            active_policies = list(
                Policy.objects.filter(
                    coi_number=existing_policy.coi_number, status="active"
                )
            )
            PolicyService._regenerate_coi_documents(
                active_policies, existing_policy.coi_number
            )

        return {
            "new_policy": new_policy,
            "full_term_premium": new_premium,
            "prorated_premium": prorated_premium,
            "invoice_sent": invoice_sent,
        }

    @staticmethod
    def endorse_remove_coverage(policy: Policy, admin_reason: str) -> dict:
        if policy.status != "active":
            raise ValueError("Can only remove active coverages.")
        if policy.is_brokered:
            raise ValueError("Cannot remove brokered coverages through endorsement.")

        sibling_count = (
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
            .exclude(pk=policy.pk)
            .count()
        )
        if sibling_count == 0:
            raise ValueError(
                "Cannot remove the last coverage in a COI group. Cancel the entire group instead."
            )

        proration_factor = PolicyService._calculate_proration_factor(policy)
        refund_amount = (policy.premium * proration_factor).quantize(Decimal("0.01"))

        if policy.billing_frequency == "monthly":
            StripeService.remove_subscription_item(
                policy.stripe_subscription_id, policy.coverage_type
            )
            if refund_amount > 0:
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=policy.stripe_subscription_id,
                    amount=-refund_amount,
                    status="refunded",
                    paid_at=timezone.now(),
                )
        else:
            if refund_amount > 0 and policy.stripe_payment_intent_id:
                refund_cents = round(float(refund_amount) * 100)
                try:
                    refund = StripeService.create_refund(
                        policy.stripe_payment_intent_id, refund_cents
                    )
                    Payment.objects.create(
                        policy=policy,
                        stripe_invoice_id=refund.id,
                        amount=-refund_amount,
                        status="refunded",
                        paid_at=timezone.now(),
                    )
                except Exception as e:
                    raise ValueError(f"Refund failed: {e}")

        old_premium = policy.premium
        policy.status = "cancelled"
        policy.expiration_date = date.today()
        policy.save()

        quote = policy.quote
        quote.coverages = [
            c for c in (quote.coverages or []) if c != policy.coverage_type
        ]
        quote_limits = quote.limits_retentions or {}
        quote_limits.pop(policy.coverage_type, None)
        quote.limits_retentions = quote_limits
        quote.save(update_fields=["coverages", "limits_retentions"])

        description = f"Coverage removed: {COVERAGE_DISPLAY_NAMES.get(policy.coverage_type, policy.coverage_type)}. Reason: {admin_reason}"
        PolicyService._create_endorsement_transaction(
            policy, -old_premium, description=description
        )

        active_policies = list(
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
        )
        PolicyService._regenerate_coi_documents(active_policies, policy.coi_number)

        return {
            "cancelled_policy": policy,
            "refund_amount": refund_amount,
        }

    @staticmethod
    def endorse_backdate_policy(
        policy: Policy, new_effective_date: date, admin_reason: str
    ) -> dict:
        if policy.status != "active":
            raise ValueError("Can only endorse active policies.")
        if new_effective_date >= policy.effective_date:
            raise ValueError(
                "New effective date must be before the current effective date."
            )
        if (policy.effective_date - new_effective_date).days > 30:
            raise ValueError("Cannot backdate more than 30 days.")

        old_effective = policy.effective_date
        old_premium = policy.premium
        old_total_days = (policy.expiration_date - old_effective).days
        new_total_days = (policy.expiration_date - new_effective_date).days
        extra_days = (old_effective - new_effective_date).days

        new_premium = (
            old_premium * Decimal(new_total_days) / Decimal(old_total_days)
        ).quantize(Decimal("0.01"))
        premium_delta = new_premium - old_premium
        invoice_sent = False

        policy.effective_date = new_effective_date
        policy.premium = new_premium
        policy.save()

        if premium_delta > 0:
            charge_cents = round(float(premium_delta) * 100)
            charge_description = (
                f"Endorsement: backdate effective date on {policy.policy_number}"
            )
            charge_metadata = {
                "policy_id": str(policy.id),
                "type": "endorsement_backdate",
            }

            try:
                pi = StripeService.create_one_time_charge(
                    policy.stripe_customer_id,
                    charge_cents,
                    charge_description,
                    charge_metadata,
                )
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=pi.id,
                    amount=premium_delta,
                    status="paid",
                    paid_at=timezone.now(),
                )
            except ValueError:
                invoice = StripeService.create_and_send_invoice(
                    customer_id=policy.stripe_customer_id,
                    line_items=[
                        {
                            "amount_cents": charge_cents,
                            "description": charge_description,
                            "metadata": charge_metadata,
                        }
                    ],
                    description=charge_description,
                    metadata=charge_metadata,
                )
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=invoice.id,
                    amount=premium_delta,
                    status="pending",
                    paid_at=None,
                )
                invoice_sent = True

        description = f"Effective date backdated by admin. Reason: {admin_reason}. Effective: {old_effective} → {new_effective_date}. Premium: ${old_premium} → ${new_premium}"
        PolicyService._create_endorsement_transaction(
            policy, premium_delta, description=description
        )

        active_policies = list(
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
        )
        PolicyService._regenerate_coi_documents(active_policies, policy.coi_number)

        return {
            "old_effective_date": old_effective,
            "new_effective_date": new_effective_date,
            "old_premium": old_premium,
            "new_premium": new_premium,
            "premium_delta": premium_delta,
            "extra_days": extra_days,
            "invoice_sent": invoice_sent,
        }

    @staticmethod
    def cancel_policy(policy: Policy, admin_reason: str) -> dict:
        if policy.status != "active":
            raise ValueError("Can only cancel active policies.")

        proration_factor = PolicyService._calculate_proration_factor(policy)
        refund_amount = (policy.premium * proration_factor).quantize(Decimal("0.01"))

        sibling_policies = list(
            Policy.objects.filter(
                coi_number=policy.coi_number, status="active"
            ).exclude(pk=policy.pk)
        )
        has_siblings = len(sibling_policies) > 0

        if policy.billing_frequency == "monthly":
            if has_siblings:
                if policy.is_brokered:
                    custom_product = policy.quote.custom_products.filter(
                        product_type=policy.coverage_type
                    ).first()
                    product_id = str(custom_product.id) if custom_product else None
                    StripeService.remove_subscription_item_by_product_id(
                        policy.stripe_subscription_id, product_id
                    )
                else:
                    StripeService.remove_subscription_item(
                        policy.stripe_subscription_id, policy.coverage_type
                    )
            else:
                StripeService.cancel_subscription(policy.stripe_subscription_id)
            if refund_amount > 0:
                Payment.objects.create(
                    policy=policy,
                    stripe_invoice_id=policy.stripe_subscription_id,
                    amount=-refund_amount,
                    status="refunded",
                    paid_at=timezone.now(),
                )
        else:
            if refund_amount > 0 and policy.stripe_payment_intent_id:
                refund_cents = round(float(refund_amount) * 100)
                try:
                    refund = StripeService.create_refund(
                        policy.stripe_payment_intent_id, refund_cents
                    )
                    Payment.objects.create(
                        policy=policy,
                        stripe_invoice_id=refund.id,
                        amount=-refund_amount,
                        status="refunded",
                        paid_at=timezone.now(),
                    )
                except Exception as e:
                    raise ValueError(f"Refund failed: {e}")

        old_premium = policy.premium
        policy.status = "cancelled"
        policy.expiration_date = date.today()
        policy.save()

        quote = policy.quote
        quote.coverages = [
            c for c in (quote.coverages or []) if c != policy.coverage_type
        ]
        quote_limits = quote.limits_retentions or {}
        quote_limits.pop(policy.coverage_type, None)
        quote.limits_retentions = quote_limits
        quote.save(update_fields=["coverages", "limits_retentions"])

        description = f"Policy cancelled: {COVERAGE_DISPLAY_NAMES.get(policy.coverage_type, policy.coverage_type)}. Reason: {admin_reason}"
        PolicyService._create_cancellation_transaction(
            policy, -old_premium, description=description
        )

        if has_siblings:
            PolicyService._regenerate_coi_documents(sibling_policies, policy.coi_number)

        return {
            "cancelled_policy": policy,
            "refund_amount": refund_amount,
        }

    @staticmethod
    def _create_cancellation_transaction(
        policy: Policy, premium_delta: Decimal, description: str = ""
    ) -> PolicyTransaction:
        state = policy.quote.company.business_address.state
        accounting_date = date.today()

        tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        gwp_delta = (premium_delta / tax_multiplier).quantize(Decimal("0.01"))
        tax_delta = (premium_delta - gwp_delta).quantize(Decimal("0.01"))

        admin_fee_rate = Decimal(ADMIN_FEE_RATE)
        admin_fee_delta = (gwp_delta * admin_fee_rate).quantize(Decimal("0.01"))

        transaction = PolicyTransaction.objects.create(
            policy=policy,
            transaction_type="cancel",
            effective_date=date.today(),
            accounting_date=accounting_date,
            gross_written_premium=gwp_delta,
            tax_amount=tax_delta,
            tax_rate=tax_multiplier,
            taxes_assessments_delta=tax_delta if tax_delta != 0 else None,
            total_billed_delta=premium_delta,
            admin_fee_rate=admin_fee_rate,
            admin_fee_amount=admin_fee_delta,
            admin_fee_recipient_entity=ADMIN_FEE_RECIPIENT,
            description=description or None,
        )

        state_tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        allocated_taxes = None
        if state_tax_rate > 1:
            allocated_taxes = (gwp_delta * (state_tax_rate - 1)).quantize(
                Decimal("0.01")
            )

        StateAllocation.objects.create(
            transaction=transaction,
            state=state,
            allocation_method="hq",
            allocation_percent=Decimal("1.0000"),
            allocated_premium=gwp_delta,
            allocated_taxes=allocated_taxes,
        )

        PolicyService.create_cession_for_transaction(transaction)

        return transaction

    @staticmethod
    def create_cancellation_transaction_for_nonpayment(
        policy: Policy,
    ) -> PolicyTransaction:
        premium_delta = -policy.premium
        description = f"Policy cancelled due to non-payment: {COVERAGE_DISPLAY_NAMES.get(policy.coverage_type, policy.coverage_type)}"
        return PolicyService._create_cancellation_transaction(
            policy, premium_delta, description=description
        )

    @staticmethod
    def _create_reinstatement_transaction(
        policy: Policy, reactivation_date: date, admin_username: str
    ) -> PolicyTransaction:
        state = policy.quote.company.business_address.state
        total_premium = policy.premium

        if policy.is_brokered:
            gwp = total_premium
            tax_amount = Decimal("0")
            tax_multiplier = Decimal("1.0")
            admin_fee_rate = None
            admin_fee_amount = None
            admin_fee_recipient = None
        else:
            tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            gwp = (total_premium / tax_multiplier).quantize(Decimal("0.01"))
            tax_amount = (total_premium - gwp).quantize(Decimal("0.01"))
            admin_fee_rate = Decimal(ADMIN_FEE_RATE)
            admin_fee_amount = (gwp * admin_fee_rate).quantize(Decimal("0.01"))
            admin_fee_recipient = ADMIN_FEE_RECIPIENT

        coverage_name = COVERAGE_DISPLAY_NAMES.get(
            policy.coverage_type, policy.coverage_type
        )

        transaction = PolicyTransaction.objects.create(
            policy=policy,
            transaction_type="reinstate",
            effective_date=reactivation_date,
            accounting_date=date.today(),
            gross_written_premium=gwp,
            tax_amount=tax_amount,
            tax_rate=tax_multiplier,
            taxes_assessments_delta=tax_amount if tax_amount > 0 else None,
            total_billed_delta=total_premium,
            collected_amount=total_premium,
            collected_date=date.today(),
            collector_entity=COLLECTOR_ENTITY,
            admin_fee_rate=admin_fee_rate,
            admin_fee_amount=admin_fee_amount,
            admin_fee_recipient_entity=admin_fee_recipient,
            description=f"Policy reinstated by {admin_username}: {coverage_name}",
        )

        state_tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        allocated_taxes = None
        if not policy.is_brokered and state_tax_rate > 1:
            allocated_taxes = (gwp * (state_tax_rate - 1)).quantize(Decimal("0.01"))

        StateAllocation.objects.create(
            transaction=transaction,
            state=state,
            allocation_method="hq",
            allocation_percent=Decimal("1.0000"),
            allocated_premium=gwp,
            allocated_taxes=allocated_taxes,
        )

        PolicyService.create_cession_for_transaction(transaction)

        return transaction

    @staticmethod
    def reactivate_policy(
        policies: list[Policy], reactivation_date: date, admin_username: str
    ) -> dict:
        from django.db import transaction

        if not policies:
            raise ValueError("No policies to reactivate.")

        for policy in policies:
            if policy.status != "cancelled":
                raise ValueError(f"Policy {policy.policy_number} is not cancelled.")
            if policy.billing_frequency != "monthly":
                raise ValueError(
                    f"Policy {policy.policy_number} is not a monthly policy."
                )
            if not policy.stripe_customer_id:
                raise ValueError(
                    f"Policy {policy.policy_number} has no Stripe customer ID."
                )

        customer_id = policies[0].stripe_customer_id

        payment_method = StripeService.get_customer_default_payment_method(customer_id)
        if not payment_method:
            raise ValueError("Customer has no valid payment method on file in Stripe.")

        today = date.today()
        gap_days = (today - reactivation_date).days
        gap_premiums = {}
        if gap_days > 0:
            for policy in policies:
                gap_premium = (
                    policy.monthly_premium * Decimal(gap_days) / Decimal("30.44")
                ).quantize(Decimal("0.01"))
                gap_premiums[policy.pk] = gap_premium

        total_gap = sum(gap_premiums.values(), Decimal("0"))

        new_subscription = None
        gap_invoice = None

        try:
            with transaction.atomic():
                for policy in policies:
                    policy.status = "active"
                    policy.expiration_date = policy.effective_date + timedelta(days=365)
                    policy.save(update_fields=["status", "expiration_date"])

                    quote = policy.quote
                    if policy.coverage_type not in (quote.coverages or []):
                        quote.coverages = (quote.coverages or []) + [
                            policy.coverage_type
                        ]
                        quote.save(update_fields=["coverages"])

                    if (
                        quote.limits_retentions is not None
                        and policy.coverage_type not in quote.limits_retentions
                    ):
                        if policy.limits_retentions:
                            quote.limits_retentions[policy.coverage_type] = (
                                policy.limits_retentions
                            )
                            quote.save(update_fields=["limits_retentions"])

                    PolicyService._create_reinstatement_transaction(
                        policy, reactivation_date, admin_username
                    )

                billing_anchor = int(
                    (datetime.combine(today + timedelta(days=30), time.min)).timestamp()
                )

                line_items = []
                for policy in policies:
                    monthly_cents = round(float(policy.monthly_premium) * 100)
                    line_items.append(
                        RecurringLineItemInput(
                            name=f"Reinstatement - {COVERAGE_DISPLAY_NAMES.get(policy.coverage_type, policy.coverage_type)}",
                            amount_cents=monthly_cents,
                            metadata={
                                "coverage_type": policy.coverage_type,
                                "policy_number": policy.policy_number,
                            },
                        )
                    )

                new_subscription = StripeService.create_direct_subscription(
                    CreateDirectSubscriptionInput(
                        customer_id=customer_id,
                        line_items=line_items,
                        billing_cycle_anchor=billing_anchor,
                        subscription_metadata={"reactivation": "true"},
                    )
                )

                if total_gap > 0:
                    gap_cents = round(float(total_gap) * 100)
                    policy_numbers = ", ".join(p.policy_number for p in policies)
                    gap_invoice = StripeService.create_one_time_invoice(
                        customer_id=customer_id,
                        amount_cents=gap_cents,
                        description=f"Gap premium for reinstated policies: {policy_numbers}",
                    )

                for policy in policies:
                    policy.stripe_subscription_id = new_subscription.id
                    if gap_days > 0:
                        policy.paid_to_date = today
                    else:
                        policy.paid_to_date = today + timedelta(days=30)
                    policy.save(
                        update_fields=["stripe_subscription_id", "paid_to_date"]
                    )

                if total_gap > 0:
                    for policy in policies:
                        gap_amount = gap_premiums.get(policy.pk, Decimal("0"))
                        if gap_amount > 0:
                            Payment.objects.create(
                                policy=policy,
                                stripe_invoice_id=gap_invoice.id if gap_invoice else "",
                                amount=gap_amount,
                                status="pending",
                                paid_at=timezone.now(),
                            )

            coi_number = policies[0].coi_number
            if coi_number:
                active_siblings = list(
                    Policy.objects.filter(coi_number=coi_number, status="active")
                )
                if active_siblings:
                    PolicyService._regenerate_coi_documents(active_siblings, coi_number)

        except Exception:
            if new_subscription:
                try:
                    StripeService.cancel_subscription(new_subscription.id)
                except Exception:
                    logger.exception(
                        "Failed to clean up Stripe subscription after reactivation failure"
                    )
            if gap_invoice:
                try:
                    StripeService.get_client().Invoice.void_invoice(gap_invoice.id)
                except Exception:
                    logger.exception(
                        "Failed to void gap invoice after reactivation failure"
                    )
            raise

        return {
            "reactivated_policies": policies,
            "subscription_id": new_subscription.id,
            "gap_premium": total_gap,
            "gap_invoice_id": gap_invoice.id if gap_invoice else None,
        }
