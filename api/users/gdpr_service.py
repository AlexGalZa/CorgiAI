"""
GDPR service for the Corgi Insurance platform.

Handles:
- Data export: collects all user data into a JSON file and emails it.
- Data deletion: anonymizes PII and soft-deletes records.
"""

import json
import logging
import uuid

from django.utils import timezone

logger = logging.getLogger(__name__)


class GDPRService:
    @staticmethod
    def collect_user_data(user) -> dict:
        """Collect all data associated with a user into a structured dict."""
        from quotes.models import Quote
        from policies.models import Policy, Payment
        from claims.models import Claim
        from certificates.models import Certificate
        from organizations.models import OrganizationMember
        from users.models import UserDocument

        data = {
            "export_date": timezone.now().isoformat(),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "company_name": user.company_name,
                "role": user.role,
                "date_joined": user.created_at.isoformat()
                if hasattr(user, "created_at") and user.created_at
                else None,
                "timezone": user.timezone,
                "notification_preferences": user.notification_preferences,
            },
            "organizations": [],
            "quotes": [],
            "policies": [],
            "claims": [],
            "payments": [],
            "certificates": [],
            "documents": [],
        }

        # Organization memberships
        memberships = OrganizationMember.objects.filter(user=user).select_related(
            "organization"
        )
        for m in memberships:
            data["organizations"].append(
                {
                    "id": m.organization.id,
                    "name": m.organization.name,
                    "role": m.role,
                    "joined_at": m.created_at.isoformat()
                    if hasattr(m, "created_at") and m.created_at
                    else None,
                }
            )

        # Quotes
        quotes = Quote.objects.filter(user=user)
        for q in quotes:
            data["quotes"].append(
                {
                    "id": q.id,
                    "quote_number": q.quote_number,
                    "status": q.status,
                    "coverages": q.coverages,
                    "quote_amount": float(q.quote_amount) if q.quote_amount else None,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
            )

        # Policies
        policies = Policy.objects.filter(quote__user=user).select_related("quote")
        for p in policies:
            data["policies"].append(
                {
                    "id": p.id,
                    "policy_number": p.policy_number,
                    "status": p.status,
                    "coverage_type": p.coverage_type,
                    "carrier": getattr(p, "carrier", None),
                    "effective_date": p.effective_date.isoformat()
                    if p.effective_date
                    else None,
                    "expiration_date": p.expiration_date.isoformat()
                    if p.expiration_date
                    else None,
                    "premium": float(p.premium)
                    if getattr(p, "premium", None)
                    else None,
                }
            )

        # Claims
        claims = Claim.objects.filter(user=user)
        for c in claims:
            data["claims"].append(
                {
                    "id": c.id,
                    "claim_number": c.claim_number,
                    "status": c.status,
                    "description": c.description,
                    "filed_at": c.created_at.isoformat() if c.created_at else None,
                }
            )

        # Payments
        try:
            payments = Payment.objects.filter(policy__quote__user=user).select_related(
                "policy"
            )
            for pay in payments:
                data["payments"].append(
                    {
                        "id": pay.id,
                        "amount": float(pay.amount) if pay.amount else None,
                        "status": getattr(pay, "status", None),
                        "paid_at": pay.created_at.isoformat()
                        if pay.created_at
                        else None,
                        "policy_number": pay.policy.policy_number
                        if pay.policy
                        else None,
                    }
                )
        except Exception as e:
            logger.warning("Could not collect payments for GDPR export: %s", e)

        # Certificates
        try:
            certs = Certificate.objects.filter(
                organization__in=[m.organization for m in memberships]
            )
            for cert in certs:
                data["certificates"].append(
                    {
                        "id": cert.id,
                        "certificate_number": getattr(cert, "certificate_number", None)
                        or getattr(cert, "coi_number", None),
                        "created_at": cert.created_at.isoformat()
                        if cert.created_at
                        else None,
                    }
                )
        except Exception as e:
            logger.warning("Could not collect certificates for GDPR export: %s", e)

        # User documents
        try:
            docs = UserDocument.objects.filter(user=user)
            for doc in docs:
                data["documents"].append(
                    {
                        "id": doc.id,
                        "document_type": getattr(doc, "document_type", None),
                        "file_name": getattr(doc, "file_name", None),
                        "created_at": doc.created_at.isoformat()
                        if doc.created_at
                        else None,
                    }
                )
        except Exception as e:
            logger.warning("Could not collect documents for GDPR export: %s", e)

        return data

    @staticmethod
    def export_user_data(user) -> None:
        """Collect all user data, package as JSON, and email to the user."""
        from emails.service import EmailService
        from emails.schemas import SendEmailInput
        from django.conf import settings

        data = GDPRService.collect_user_data(user)
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1d1d1d;">
            <h2 style="color:#ff5c00;">Your Corgi Data Export</h2>
            <p>Hello {user.first_name or user.email},</p>
            <p>
                As requested, we have prepared an export of all personal data associated with
                your Corgi Insurance account. Please find it attached as a JSON file.
            </p>
            <p>The export includes:</p>
            <ul>
                <li>Account profile information</li>
                <li>Organization memberships</li>
                <li>Insurance quotes</li>
                <li>Active and past policies</li>
                <li>Claims history</li>
                <li>Payment records</li>
                <li>Certificates of Insurance</li>
                <li>Documents</li>
            </ul>
            <p>
                If you did not request this export or have any concerns,
                please contact us at <a href="mailto:privacy@corgi.insure">privacy@corgi.insure</a>.
            </p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
            <p style="color:#9ca3af;font-size:12px;">
                Corgi Insurance Services, Inc. &middot; 425 Bush St, STE 500, San Francisco, CA 94104
            </p>
        </body>
        </html>
        """

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "privacy@corgi.insure")

        EmailService.send(
            SendEmailInput(
                to=[user.email],
                subject="Your Corgi Insurance Data Export",
                html=html,
                from_email=from_email,
                attachments=[
                    {
                        "filename": f"corgi-data-export-{user.id}.json",
                        "content": list(json_bytes),
                        "type": "application/json",
                    }
                ],
            )
        )

        logger.info("GDPR data export sent to user=%s", user.email)

    @staticmethod
    def delete_user_data(user) -> None:
        """Anonymize all PII for a user and deactivate their account."""
        from claims.models import Claim

        anon_id = uuid.uuid4().hex[:8]
        anon_email = f"deleted_{anon_id}@anonymized.invalid"

        # Anonymize user fields
        user.email = anon_email
        user.first_name = "Deleted"
        user.last_name = "User"
        user.phone_number = ""
        user.company_name = ""
        user.avatar_url = None
        user.is_active = False
        user.set_unusable_password()
        user.save(
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "phone_number",
                "company_name",
                "avatar_url",
                "is_active",
                "password",
            ]
        )

        # Anonymize claims (which hold PII directly)
        Claim.objects.filter(user=user).update(
            first_name="Deleted",
            last_name="User",
            email=anon_email,
            phone_number="",
            organization_name="[Anonymized]",
        )

        logger.info(
            "GDPR data deletion completed for original email hash=%s", hash(anon_id)
        )
