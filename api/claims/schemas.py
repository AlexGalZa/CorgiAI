from datetime import datetime
from typing import List

from ninja import Schema

from claims.models import Claim


class ClaimCreateSchema(Schema):
    policy_id: int
    organization_name: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    description: str


class ClaimDocumentSchema(Schema):
    id: int
    file_type: str
    original_filename: str
    file_size: int
    mime_type: str
    created_at: datetime


class ClaimResponseSchema(Schema):
    id: int
    claim_number: str
    policy_number: str
    organization_name: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    description: str
    status: str
    documents: List[ClaimDocumentSchema]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_claim(claim: Claim) -> "ClaimResponseSchema":
        return ClaimResponseSchema(
            id=claim.id,
            claim_number=claim.claim_number,
            policy_number=claim.policy.policy_number,
            organization_name=claim.organization_name,
            first_name=claim.first_name,
            last_name=claim.last_name,
            email=claim.email,
            phone_number=claim.phone_number,
            description=claim.description,
            status=claim.status,
            documents=[
                ClaimDocumentSchema(
                    id=doc.id,
                    file_type=doc.file_type,
                    original_filename=doc.original_filename,
                    file_size=doc.file_size,
                    mime_type=doc.mime_type,
                    created_at=doc.created_at,
                )
                for doc in claim.documents.all()
            ],
            created_at=claim.created_at,
            updated_at=claim.updated_at,
        )


class ClaimListItemSchema(Schema):
    id: int
    claim_number: str
    policy_number: str
    status: str
    description: str
    created_at: datetime

    @staticmethod
    def from_claim(claim: Claim) -> "ClaimListItemSchema":
        return ClaimListItemSchema(
            id=claim.id,
            claim_number=claim.claim_number,
            policy_number=claim.policy.policy_number,
            status=claim.status,
            description=claim.description[:200]
            if len(claim.description) > 200
            else claim.description,
            created_at=claim.created_at,
        )
