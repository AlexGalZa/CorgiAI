"""
Additional Insured service for the Corgi Insurance platform.

Handles adding/removing additional insureds from portal, auto-generating
custom COI certificates, and emailing copies to the additional insured.
"""

import logging
from typing import Optional

from django.utils import timezone

from certificates.models import AdditionalInsured, CustomCertificate
from certificates.service import CustomCertificateService
from organizations.service import OrganizationService

logger = logging.getLogger(__name__)


class AdditionalInsuredService:
    @staticmethod
    def list_additional_insureds(user, coi_number: Optional[str] = None) -> list[dict]:
        """List all active additional insureds for the user's organization."""
        org_id = OrganizationService.get_active_org_id(user)

        qs = AdditionalInsured.objects.filter(
            organization_id=org_id,
            status="active",
        ).select_related("certificate")

        if coi_number:
            qs = qs.filter(coi_number=coi_number)

        return [
            {
                "id": ai.pk,
                "coi_number": ai.coi_number,
                "name": ai.name,
                "address": ai.address,
                "email": ai.email,
                "phone": ai.phone,
                "status": ai.status,
                "created_at": ai.created_at.isoformat(),
                "certificate_id": ai.certificate_id,
                "certificate_number": (
                    ai.certificate.custom_coi_number if ai.certificate else None
                ),
            }
            for ai in qs
        ]

    @staticmethod
    def add_additional_insured(
        user,
        coi_number: str,
        name: str,
        address: str = "",
        email: str = "",
        phone: str = "",
    ) -> dict:
        """
        Add an additional insured to a policy's COI.

        Steps:
        1. Create AdditionalInsured record
        2. Auto-generate a custom COI certificate with is_additional_insured=True
        3. Email the COI to the additional insured's email (if provided)

        Returns serialised AdditionalInsured dict.
        """
        from django.conf import settings
        from emails.schemas import SendEmailInput
        from emails.service import EmailService

        org_id = OrganizationService.get_active_org_id(user)

        # Parse address components (basic — accept freeform or "street, city, state zip")
        street, city, state, zip_code = AdditionalInsuredService._parse_address(address)

        # Generate a custom certificate for this additional insured
        try:
            custom_cert = CustomCertificateService.create_and_generate_certificate(
                user=user,
                coi_number=coi_number,
                holder_name=name,
                holder_second_line="",
                holder_street_address=street,
                holder_suite="",
                holder_city=city,
                holder_state=state or "CA",  # fallback state
                holder_zip=zip_code,
                is_additional_insured=True,
                endorsements=[
                    "waiver_of_subrogation"
                ],  # standard for additional insured
                service_location_job="",
                service_location_address="",
                service_you_provide_job="",
                service_you_provide_service="",
            )
        except Exception as e:
            logger.warning(
                "Could not generate custom cert for additional insured %s: %s",
                name,
                e,
            )
            custom_cert = None

        # Create the AdditionalInsured record
        ai = AdditionalInsured.objects.create(
            organization_id=org_id,
            created_by=user,
            coi_number=coi_number,
            name=name,
            address=address,
            email=email,
            phone=phone,
            certificate=custom_cert,
            status="active",
        )

        logger.info(
            "Added additional insured %s (id=%s) to COI %s for org %s",
            name,
            ai.pk,
            coi_number,
            org_id,
        )

        # Auto-regenerate the main policy document with an AI endorsement
        # page so ops no longer has to do it manually in Django (card H4).
        # Run synchronously for this branch — failures must not block AI
        # creation and are logged only.
        try:
            AdditionalInsuredService._regenerate_policy_docs_for_ai(
                user=user, ai=ai, coi_number=coi_number
            )
        except Exception:
            logger.exception(
                "Auto-regenerate of policy doc with AI endorsement failed for AI %s",
                ai.pk,
            )

        # Email the COI to the additional insured if they provided an email
        if email and custom_cert:
            try:
                AdditionalInsuredService._email_coi_to_additional_insured(
                    ai=ai,
                    custom_cert=custom_cert,
                    email=email,
                    settings=settings,
                    EmailService=EmailService,
                    SendEmailInput=SendEmailInput,
                )
            except Exception:
                logger.exception(
                    "Failed to email COI to additional insured %s <%s>",
                    name,
                    email,
                )

        return {
            "id": ai.pk,
            "coi_number": ai.coi_number,
            "name": ai.name,
            "address": ai.address,
            "email": ai.email,
            "phone": ai.phone,
            "status": ai.status,
            "created_at": ai.created_at.isoformat(),
            "certificate_id": custom_cert.pk if custom_cert else None,
            "certificate_number": custom_cert.custom_coi_number
            if custom_cert
            else None,
        }

    @staticmethod
    def remove_additional_insured(user, additional_insured_id: int) -> dict:
        """
        Remove (soft-delete) an additional insured.

        Also revokes the associated certificate.
        """
        org_id = OrganizationService.get_active_org_id(user)

        ai = AdditionalInsured.objects.select_related("certificate").get(
            pk=additional_insured_id,
            organization_id=org_id,
            status="active",
        )

        # Revoke the associated certificate if it exists
        if ai.certificate:
            try:
                CustomCertificateService.revoke_certificate(user, ai.certificate.pk)
            except Exception:
                logger.warning(
                    "Could not revoke certificate %s for additional insured %s",
                    ai.certificate.pk,
                    ai.pk,
                )

        ai.status = "removed"
        ai.removed_at = timezone.now()
        ai.removed_by = user
        ai.save(update_fields=["status", "removed_at", "removed_by", "updated_at"])

        logger.info(
            "Removed additional insured %s (id=%s) from COI %s",
            ai.name,
            ai.pk,
            ai.coi_number,
        )

        return {
            "id": ai.pk,
            "coi_number": ai.coi_number,
            "name": ai.name,
            "status": ai.status,
            "removed_at": ai.removed_at.isoformat(),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _regenerate_policy_docs_for_ai(user, ai: "AdditionalInsured", coi_number: str):
        """
        Resolve the policies tied to *coi_number* and regenerate each of
        their main policy documents with an Additional Insured endorsement
        page. Uses ``DocumentsGeneratorService.regenerate_policy_doc_with_endorsement``.

        Django admin's existing manual endorsement UI continues to work — this
        is purely additive automation.
        """
        from documents_generator.service import DocumentsGeneratorService
        from policies.models import Policy

        policies = list(
            Policy.objects.filter(
                coi_number=coi_number,
                quote__organization_id=ai.organization_id,
                status="active",
            ).select_related("quote__company__business_address")
        )

        if not policies:
            logger.info(
                "No active policies found for COI %s — skipping AI endorsement auto-gen",
                coi_number,
            )
            return

        for policy in policies:
            try:
                DocumentsGeneratorService.regenerate_policy_doc_with_endorsement(
                    policy=policy,
                    additional_insured=ai,
                    user=user,
                    organization=ai.organization,
                )
            except Exception:
                logger.exception(
                    "regenerate_policy_doc_with_endorsement raised for policy %s, AI %s",
                    policy.pk,
                    ai.pk,
                )

    @staticmethod
    def _parse_address(address: str) -> tuple[str, str, str, str]:
        """
        Best-effort parse of freeform address into (street, city, state, zip).

        Tries to detect "Street, City, ST ZIP" pattern.
        Falls back to using the full address as street.
        """
        if not address:
            return ("", "", "", "")

        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 3:
            street = parts[0]
            city = parts[1]
            # Last part might be "ST 12345" or "12345"
            last = parts[-1].strip()
            tokens = last.split()
            if len(tokens) >= 2 and len(tokens[0]) == 2 and tokens[0].isupper():
                state = tokens[0]
                zip_code = tokens[1]
            elif len(tokens) == 1:
                state = ""
                zip_code = tokens[0]
            else:
                state = ""
                zip_code = last
            return (street, city, state, zip_code)

        return (address, "", "", "")

    @staticmethod
    def _email_coi_to_additional_insured(
        ai: "AdditionalInsured",
        custom_cert: "CustomCertificate",
        email: str,
        settings,
        EmailService,
        SendEmailInput,
    ):
        """Send the generated COI PDF to the additional insured via email."""
        from django.template.loader import render_to_string
        from s3.service import S3Service

        # Try to get the PDF bytes from the certificate's document
        pdf_bytes = None
        attachment = None

        if custom_cert.document:
            try:
                s3 = S3Service()
                pdf_bytes = s3.download_file(custom_cert.document.s3_key)
            except Exception:
                logger.warning(
                    "Could not download COI PDF for additional insured email (cert %s)",
                    custom_cert.pk,
                )

        if pdf_bytes:
            import base64

            attachment = {
                "filename": f"COI-{custom_cert.custom_coi_number}.pdf",
                "content": base64.b64encode(pdf_bytes).decode(),
            }

        html = render_to_string(
            "emails/additional_insured_coi.html",
            {
                "name": ai.name,
                "coi_number": custom_cert.custom_coi_number,
                "portal_url": settings.FRONTEND_URL,
            },
        )

        EmailService.send(
            SendEmailInput(
                to=[email],
                subject=f"Your Certificate of Insurance — {custom_cert.custom_coi_number}",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
                attachments=[attachment] if attachment else None,
            )
        )
