"""
Tests for the certificates module.

Covers certificate creation, custom COI number generation,
certificate listing (org-scoped), revocation, and search.
"""

from django.test import TestCase
from django.utils import timezone

from certificates.models import CustomCertificate
from certificates.service import CustomCertificateService
from tests.factories import (
    setup_user_with_org,
)


class CustomCOINumberGenerationTest(TestCase):
    """Tests for sequential custom COI number generation."""

    def test_first_certificate_gets_01_suffix(self):
        number = CustomCertificate.generate_custom_coi_number("COI-CA-26-000001")
        self.assertEqual(number, "COI-CA-26-000001-01")

    def test_sequential_numbering(self):
        user, org = setup_user_with_org()
        # Create first certificate
        CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-01",
            holder_name="First Holder",
            holder_street_address="123 Main St",
            holder_city="San Francisco",
            holder_state="CA",
            holder_zip="94104",
        )
        # Second should get -02
        number = CustomCertificate.generate_custom_coi_number("COI-CA-26-000001")
        self.assertEqual(number, "COI-CA-26-000001-02")

    def test_different_coi_numbers_have_independent_sequences(self):
        n1 = CustomCertificate.generate_custom_coi_number("COI-CA-26-000001")
        n2 = CustomCertificate.generate_custom_coi_number("COI-NY-26-000001")
        self.assertEqual(n1, "COI-CA-26-000001-01")
        self.assertEqual(n2, "COI-NY-26-000001-01")


class CustomCertificateModelTest(TestCase):
    """Tests for CustomCertificate model."""

    def test_holder_full_address(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-01",
            holder_name="Acme Corp",
            holder_street_address="456 Oak Ave",
            holder_suite="Suite 200",
            holder_city="Los Angeles",
            holder_state="CA",
            holder_zip="90001",
        )
        address = cert.holder_full_address
        self.assertIn("456 Oak Ave", address)
        self.assertIn("Suite 200", address)
        self.assertIn("Los Angeles, CA 90001", address)

    def test_holder_full_address_without_suite(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-02",
            holder_name="Simple Corp",
            holder_street_address="789 Pine St",
            holder_city="Denver",
            holder_state="CO",
            holder_zip="80201",
        )
        address = cert.holder_full_address
        self.assertNotIn("Suite", address)

    def test_certificate_str_representation(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-03",
            holder_name="Test Holder",
            holder_street_address="123 St",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
        )
        self.assertIn("COI-CA-26-000001-03", str(cert))
        self.assertIn("Test Holder", str(cert))

    def test_default_status_is_active(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-04",
            holder_name="Test",
            holder_street_address="123",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
        )
        self.assertEqual(cert.status, "active")


class CertificateRevocationTest(TestCase):
    """Tests for certificate revocation."""

    def test_revoke_certificate(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-05",
            holder_name="Revocable Corp",
            holder_street_address="123 St",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
            status="active",
        )

        revoked = CustomCertificateService.revoke_certificate(user, cert.id)
        self.assertEqual(revoked.status, "revoked")
        self.assertIsNotNone(revoked.revoked_at)
        self.assertEqual(revoked.revoked_by, user)

    def test_revoke_already_revoked_raises_error(self):
        user, org = setup_user_with_org()
        cert = CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-06",
            holder_name="Already Revoked",
            holder_street_address="123 St",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
            status="revoked",
            revoked_at=timezone.now(),
        )
        with self.assertRaises(ValueError, msg="Certificate is already revoked"):
            CustomCertificateService.revoke_certificate(user, cert.id)


class CertificateListingTest(TestCase):
    """Tests for certificate listing (org-scoped) and search."""

    def test_list_certificates_for_user(self):
        user, org = setup_user_with_org()
        for i in range(3):
            CustomCertificate.objects.create(
                user=user,
                organization=org,
                coi_number="COI-CA-26-000001",
                custom_coi_number=f"COI-CA-26-000001-{i + 10:02d}",
                holder_name=f"Holder {i}",
                holder_street_address="123 St",
                holder_city="City",
                holder_state="CA",
                holder_zip="94000",
            )

        certs = CustomCertificateService.get_certificates_for_user(user)
        self.assertEqual(len(certs), 3)

    def test_list_certificates_org_isolation(self):
        user1, org1 = setup_user_with_org()
        user2, org2 = setup_user_with_org()

        CustomCertificate.objects.create(
            user=user1,
            organization=org1,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-20",
            holder_name="Org1 Holder",
            holder_street_address="123 St",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
        )

        certs_user2 = CustomCertificateService.get_certificates_for_user(user2)
        self.assertEqual(len(certs_user2), 0)

    def test_search_certificates_by_holder_name(self):
        user, org = setup_user_with_org()
        CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-30",
            holder_name="Special Holder Inc",
            holder_street_address="123 St",
            holder_city="City",
            holder_state="CA",
            holder_zip="94000",
        )
        CustomCertificate.objects.create(
            user=user,
            organization=org,
            coi_number="COI-CA-26-000001",
            custom_coi_number="COI-CA-26-000001-31",
            holder_name="Other Company",
            holder_street_address="456 St",
            holder_city="Town",
            holder_state="NY",
            holder_zip="10001",
        )

        result = CustomCertificateService.list_certificates(user, search="Special")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["certificates"][0].holder_name, "Special Holder Inc")

    def test_list_certificates_pagination(self):
        user, org = setup_user_with_org()
        for i in range(25):
            CustomCertificate.objects.create(
                user=user,
                organization=org,
                coi_number="COI-CA-26-000001",
                custom_coi_number=f"COI-CA-26-000001-{i + 40:02d}",
                holder_name=f"Holder {i}",
                holder_street_address="123 St",
                holder_city="City",
                holder_state="CA",
                holder_zip="94000",
            )

        result = CustomCertificateService.list_certificates(user, page=1, page_size=10)
        self.assertEqual(result["total"], 25)
        self.assertEqual(len(result["certificates"]), 10)
        self.assertEqual(result["total_pages"], 3)
        self.assertEqual(result["page"], 1)
