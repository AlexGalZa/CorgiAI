import logging
from io import BytesIO
from typing import List, Optional

from django.conf import settings
from django.template.loader import render_to_string
from ninja import UploadedFile

from claims.models import Claim, ClaimDocument
from claims.schemas import ClaimCreateSchema, ClaimListItemSchema
from common.exceptions import AccessDeniedError
from emails.schemas import SendEmailInput
from emails.service import EmailService
from organizations.service import OrganizationService
from policies.models import Policy
from s3.schemas import UploadFileInput
from s3.service import S3Service
from users.models import User

logger = logging.getLogger(__name__)


class ClaimService:
    @staticmethod
    def submit_claim(
        data: ClaimCreateSchema, files: Optional[List[UploadedFile]], user: User
    ) -> Claim:
        if not OrganizationService.can_edit(user):
            raise AccessDeniedError("You do not have permission to submit claims")

        org_id = OrganizationService.get_active_org_id(user)
        policy = Policy.objects.select_related("quote__user").get(
            id=data.policy_id, quote__organization_id=org_id
        )

        claim = Claim.objects.create(
            user=user,
            organization_id=org_id,
            policy=policy,
            organization_name=data.organization_name,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone_number=data.phone_number,
            description=data.description,
            status="submitted",
        )

        if files:
            for uploaded_file in files:
                file_content = uploaded_file.read()
                result = S3Service.upload_file(
                    UploadFileInput(
                        file=BytesIO(file_content),
                        path_prefix=f"claims/{claim.id}/documents",
                        original_filename=uploaded_file.name,
                        content_type=uploaded_file.content_type,
                    )
                )

                if not result:
                    logger.error(
                        f"Failed to upload file {uploaded_file.name} for claim {claim.claim_number}"
                    )
                    continue

                extension = ""
                if uploaded_file.name and "." in uploaded_file.name:
                    extension = uploaded_file.name.rsplit(".", 1)[-1].lower()

                ClaimDocument.objects.create(
                    claim=claim,
                    file_type=extension or "unknown",
                    original_filename=uploaded_file.name or "unknown",
                    file_size=len(file_content),
                    mime_type=uploaded_file.content_type or "application/octet-stream",
                    s3_key=result["s3_key"],
                    s3_url=result["s3_url"],
                )

        ClaimService._send_admin_notification(claim)

        return claim

    @staticmethod
    def _send_admin_notification(claim: Claim) -> None:
        try:
            html = render_to_string(
                "emails/claim_submitted.html",
                {
                    "claim_number": claim.claim_number,
                    "organization_name": claim.organization_name,
                    "contact_name": f"{claim.first_name} {claim.last_name}",
                    "email": claim.email,
                    "phone_number": claim.phone_number,
                    "policy_number": claim.policy.policy_number,
                    "description": claim.description,
                    "document_count": claim.documents.count(),
                    "admin_url": f"{settings.PORTAL_BASE_URL}/admin/claims/claim/{claim.id}/change/",
                },
            )

            EmailService.send(
                SendEmailInput(
                    to=[settings.CORGI_NOTIFICATION_EMAIL],
                    subject=f"New Claim Submitted: {claim.claim_number}",
                    html=html,
                    from_email=settings.HELLO_CORGI_EMAIL,
                )
            )
        except Exception as e:
            logger.exception(
                f"Failed to send admin notification for claim {claim.claim_number}: {e}"
            )

    @staticmethod
    def get_user_claims(user: User) -> List[ClaimListItemSchema]:
        org_id = OrganizationService.get_active_org_id(user)
        claims = Claim.objects.filter(organization_id=org_id).select_related("policy")
        return [ClaimListItemSchema.from_claim(claim) for claim in claims]

    @staticmethod
    def get_claim_by_number(claim_number: str, user: User) -> Optional[Claim]:
        org_id = OrganizationService.get_active_org_id(user)
        try:
            return (
                Claim.objects.prefetch_related("documents")
                .select_related("policy")
                .get(claim_number=claim_number, organization_id=org_id)
            )
        except Claim.DoesNotExist:
            return None
