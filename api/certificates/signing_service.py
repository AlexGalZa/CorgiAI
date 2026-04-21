"""
Membership agreement signing service (H5).

Crime and Umbrella products require a signed membership agreement at checkout.
This module provides the integration surface for PDF generation and e-signature
(DocuSign / HelloSign) flows.

All methods currently raise ``NotImplementedError`` — the real implementation
lands when Josh delivers the flow spec. The class is callable from the API so
frontend wiring can be completed ahead of the spec.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quotes.models import Quote


_PENDING_SPEC_MSG = "Pending Josh's spec"


class MembershipAgreementService:
    """Stub for membership agreement PDF generation and e-signature flow."""

    @staticmethod
    def generate_agreement_pdf(quote: "Quote", coverages: list[str]) -> bytes:
        """Generate the membership agreement PDF for the given quote and coverages.

        Args:
            quote: Quote the agreement is being generated for.
            coverages: List of coverage slugs (e.g. ['custom-crime', 'custom-umbrella']).

        Returns:
            PDF bytes.

        Raises:
            NotImplementedError: Until Josh's spec is delivered.
        """
        raise NotImplementedError(_PENDING_SPEC_MSG)

    @staticmethod
    def request_signature(quote: "Quote", email: str) -> str:
        """Request a signature on the membership agreement.

        Args:
            quote: Quote the agreement belongs to.
            email: Signer email address.

        Returns:
            External signature request / envelope ID.

        Raises:
            NotImplementedError: Until Josh's spec is delivered.
        """
        raise NotImplementedError(_PENDING_SPEC_MSG)

    @staticmethod
    def verify_signature(quote: "Quote", signed_id: str) -> bool:
        """Verify that the given signed agreement ID is valid for this quote.

        Args:
            quote: Quote the signed agreement should belong to.
            signed_id: Signed agreement / envelope ID returned by the e-sign provider.

        Returns:
            True if the signature is verified.

        Raises:
            NotImplementedError: Until Josh's spec is delivered.
        """
        raise NotImplementedError(_PENDING_SPEC_MSG)
