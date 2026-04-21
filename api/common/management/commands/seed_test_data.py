"""
Management command to seed realistic test data for the Corgi Insurance platform.

Creates companies, quotes, policies, claims, certificates, documents,
organizations, notifications, and audit log entries — all linked to
sergio@corgi.com for demo purposes.

Usage:
    python manage.py seed_test_data
    python manage.py seed_test_data --flush  # Delete existing test data first
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import User, UserDocument
from organizations.models import Organization, OrganizationMember, OrganizationInvite
from quotes.models import Address, Company, Quote
from policies.models import Policy
from claims.models import Claim
from certificates.models import CustomCertificate
from common.models import Notification, AuditLogEntry


class Command(BaseCommand):
    help = "Seed realistic test data for demoing the Corgi Insurance platform"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing seeded test data before creating new data",
        )

    def handle(self, *args, **options):
        now = timezone.now()

        # Get or create the main test user
        user, created = User.objects.get_or_create(
            email="sergio@corgi.com",
            defaults={
                "first_name": "Sergio",
                "last_name": "Garcia",
                "company_name": "Corgi Insurance",
                "is_active": True,
            },
        )
        if created:
            user.set_password("testpass123")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {user.email}"))
        else:
            self.stdout.write(f"Using existing user: {user.email}")

        # Get or create personal org
        personal_org = Organization.objects.filter(owner=user, is_personal=True).first()
        if not personal_org:
            personal_org = Organization.objects.create(
                name=f"{user.first_name}'s Workspace",
                owner=user,
                is_personal=True,
            )
            OrganizationMember.objects.get_or_create(
                organization=personal_org,
                user=user,
                defaults={"role": "owner"},
            )
            self.stdout.write(self.style.SUCCESS("Created personal organization"))

        if options["flush"]:
            self._flush(user, personal_org)

        # ── Companies ────────────────────────────────────────────
        companies = []
        company_data = [
            {
                "entity_legal_name": "TechVault Inc.",
                "type": "corporation",
                "profit_type": "for-profit",
                "business_description": "Cloud-based data management platform for enterprise customers.",
                "last_12_months_revenue": Decimal("3500000.00"),
                "projected_next_12_months_revenue": Decimal("5200000.00"),
                "full_time_employees": 45,
                "part_time_employees": 8,
                "is_technology_company": True,
                "address": {
                    "street_address": "123 Innovation Dr",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94105",
                },
            },
            {
                "entity_legal_name": "GreenLeaf Consulting LLC",
                "type": "llc",
                "profit_type": "for-profit",
                "business_description": "Environmental consulting and sustainability advisory services.",
                "last_12_months_revenue": Decimal("1200000.00"),
                "projected_next_12_months_revenue": Decimal("1800000.00"),
                "full_time_employees": 15,
                "part_time_employees": 3,
                "is_technology_company": False,
                "address": {
                    "street_address": "456 Oak Street",
                    "city": "Portland",
                    "state": "OR",
                    "zip": "97201",
                },
            },
            {
                "entity_legal_name": "MediSync Health Technologies",
                "type": "corporation",
                "profit_type": "for-profit",
                "business_description": "Healthcare SaaS platform for patient data synchronization across providers.",
                "last_12_months_revenue": Decimal("8000000.00"),
                "projected_next_12_months_revenue": Decimal("12000000.00"),
                "full_time_employees": 120,
                "part_time_employees": 15,
                "is_technology_company": True,
                "address": {
                    "street_address": "789 Health Blvd",
                    "suite": "Suite 400",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78701",
                },
            },
        ]

        for cd in company_data:
            addr_data = cd.pop("address")
            addr = Address.objects.create(**addr_data)
            company = Company.objects.create(business_address=addr, **cd)
            companies.append(company)
            self.stdout.write(f"  Created company: {company.entity_legal_name}")

        # ── Quotes ───────────────────────────────────────────────
        quotes_data = [
            {
                "company": companies[0],
                "status": "purchased",
                "coverages": ["technology-errors-and-omissions", "cyber-liability"],
                "quote_amount": Decimal("8250.00"),
                "billing_frequency": "annual",
                "rating_result": {
                    "total_premium": 8250.00,
                    "breakdown": {
                        "technology-errors-and-omissions": {
                            "premium": 4250.00,
                            "status": "quoted",
                        },
                        "cyber-liability": {"premium": 4000.00, "status": "quoted"},
                    },
                },
            },
            {
                "company": companies[0],
                "status": "purchased",
                "coverages": [
                    "directors-and-officers",
                    "employment-practices-liability",
                ],
                "quote_amount": Decimal("6100.00"),
                "billing_frequency": "monthly",
                "rating_result": {
                    "total_premium": 6100.00,
                    "breakdown": {
                        "directors-and-officers": {
                            "premium": 3200.00,
                            "status": "quoted",
                        },
                        "employment-practices-liability": {
                            "premium": 2900.00,
                            "status": "quoted",
                        },
                    },
                },
            },
            {
                "company": companies[1],
                "status": "quoted",
                "coverages": [
                    "commercial-general-liability",
                    "hired-and-non-owned-auto",
                ],
                "quote_amount": Decimal("3700.00"),
                "billing_frequency": "annual",
                "rating_result": {
                    "total_premium": 3700.00,
                    "breakdown": {
                        "commercial-general-liability": {
                            "premium": 2200.00,
                            "status": "quoted",
                        },
                        "hired-and-non-owned-auto": {
                            "premium": 1500.00,
                            "status": "quoted",
                        },
                    },
                },
            },
            {
                "company": companies[2],
                "status": "needs_review",
                "coverages": [
                    "cyber-liability",
                    "technology-errors-and-omissions",
                    "directors-and-officers",
                ],
                "quote_amount": None,
                "billing_frequency": "annual",
                "rating_result": {
                    "total_premium": None,
                    "review_reasons": [
                        {
                            "coverage": "cyber-liability",
                            "reason": "Healthcare data — requires manual underwriting review",
                        },
                    ],
                    "breakdown": {
                        "cyber-liability": {"premium": None, "status": "needs_review"},
                        "technology-errors-and-omissions": {
                            "premium": 5200.00,
                            "status": "quoted",
                        },
                        "directors-and-officers": {
                            "premium": 4800.00,
                            "status": "quoted",
                        },
                    },
                },
            },
            {
                "company": companies[1],
                "status": "draft",
                "coverages": ["commercial-general-liability"],
                "quote_amount": None,
                "billing_frequency": "annual",
                "rating_result": {},
            },
        ]

        created_quotes = []
        for i, qd in enumerate(quotes_data):
            company = qd.pop("company")
            q = Quote.objects.create(
                company=company,
                user=user,
                organization=personal_org,
                **qd,
            )
            if qd["status"] == "purchased":
                q.quoted_at = now - timedelta(days=random.randint(10, 60))
                q.save(update_fields=["quoted_at"])
            created_quotes.append(q)
            self.stdout.write(f"  Created quote: {q.quote_number} ({q.status})")

        # ── Policies ─────────────────────────────────────────────
        policies_data = [
            {
                "quote": created_quotes[0],
                "coverage_type": "technology-errors-and-omissions",
                "premium_amount": Decimal("4250.00"),
                "per_occurrence_limit": 1000000,
                "aggregate_limit": 2000000,
                "retention": 10000,
                "billing_frequency": "annual",
                "status": "active",
            },
            {
                "quote": created_quotes[0],
                "coverage_type": "cyber-liability",
                "premium_amount": Decimal("4000.00"),
                "per_occurrence_limit": 1000000,
                "aggregate_limit": 2000000,
                "retention": 20000,
                "billing_frequency": "annual",
                "status": "active",
            },
            {
                "quote": created_quotes[1],
                "coverage_type": "directors-and-officers",
                "premium_amount": Decimal("3200.00"),
                "per_occurrence_limit": 2000000,
                "aggregate_limit": 2000000,
                "retention": 15000,
                "billing_frequency": "monthly",
                "status": "active",
            },
            {
                "quote": created_quotes[1],
                "coverage_type": "employment-practices-liability",
                "premium_amount": Decimal("2900.00"),
                "per_occurrence_limit": 1000000,
                "aggregate_limit": 1000000,
                "retention": 10000,
                "billing_frequency": "monthly",
                "status": "expired",
            },
        ]

        created_policies = []
        for pd in policies_data:
            from policies.sequences import generate_policy_number

            effective_date = (now - timedelta(days=random.randint(30, 180))).date()
            state = pd["quote"].company.business_address.state
            policy = Policy.objects.create(
                policy_number=generate_policy_number(
                    coverage_type=pd["coverage_type"],
                    state=state,
                    effective_date=effective_date,
                ),
                effective_date=effective_date,
                expiration_date=(now + timedelta(days=random.randint(30, 335))).date(),
                **pd,
            )
            created_policies.append(policy)
            self.stdout.write(
                f"  Created policy: {policy.policy_number} ({policy.coverage_type})"
            )

        # ── Claims ───────────────────────────────────────────────
        claims_data = [
            {
                "policy": created_policies[0],
                "status": "submitted",
                "description": "Client alleges software defect caused data loss during migration. Estimated damages $45,000.",
                "incident_date": (now - timedelta(days=15)).date(),
                "incident_state": "CA",
            },
            {
                "policy": created_policies[1],
                "status": "under_review",
                "description": "Phishing attack compromised employee credentials. 2,300 customer records potentially exposed.",
                "incident_date": (now - timedelta(days=45)).date(),
                "incident_state": "CA",
            },
            {
                "policy": created_policies[2],
                "status": "approved",
                "description": "Former board member alleges breach of fiduciary duty regarding compensation decisions.",
                "incident_date": (now - timedelta(days=90)).date(),
                "incident_state": "TX",
            },
        ]

        for cd in claims_data:
            from common.utils import generate_short_id

            policy = cd.pop("policy")
            claim = Claim.objects.create(
                claim_number=generate_short_id(),
                user=user,
                organization=personal_org,
                policy=policy,
                organization_name=policy.quote.company.entity_legal_name,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone="(415) 555-0123",
                **cd,
            )
            self.stdout.write(f"  Created claim: {claim.claim_number} ({claim.status})")

        # ── Certificates ─────────────────────────────────────────
        cert_holders = [
            ("Amazon Web Services Inc.", "410 Terry Ave N", "Seattle", "WA", "98109"),
            (
                "Google Cloud Platform",
                "1600 Amphitheatre Pkwy",
                "Mountain View",
                "CA",
                "94043",
            ),
            ("Salesforce Inc.", "415 Mission St", "San Francisco", "CA", "94105"),
            ("Microsoft Corporation", "1 Microsoft Way", "Redmond", "WA", "98052"),
            (
                "Stripe Inc.",
                "354 Oyster Point Blvd",
                "South San Francisco",
                "CA",
                "94080",
            ),
        ]

        for i, (name, street, city, state, zipcode) in enumerate(cert_holders):
            coi_base = f"COI-{created_policies[0].coi_number or created_policies[0].policy_number}"
            custom_coi = f"{coi_base}-C{i + 1:03d}"
            CustomCertificate.objects.create(
                user=user,
                organization=personal_org,
                coi_number=created_policies[0].coi_number
                or created_policies[0].policy_number,
                custom_coi_number=custom_coi,
                holder_name=name,
                holder_street_address=street,
                holder_city=city,
                holder_state=state,
                holder_zip=zipcode,
                is_additional_insured=i < 3,
                endorsements=["waiver_of_subrogation"] if i % 2 == 0 else [],
            )
            self.stdout.write(f"  Created certificate for: {name}")

        # ── Documents ────────────────────────────────────────────
        doc_data = [
            ("policy", "Tech E&O Policy Declaration", "tech-eo-declaration.pdf"),
            ("policy", "Cyber Liability Policy", "cyber-policy.pdf"),
            ("policy", "D&O Policy Declaration", "do-declaration.pdf"),
            ("certificate", "Certificate of Insurance - AWS", "coi-aws.pdf"),
            ("certificate", "Certificate of Insurance - Google", "coi-google.pdf"),
            ("endorsement", "Waiver of Subrogation - AWS", "wos-aws.pdf"),
            ("receipt", "Payment Receipt - Annual Premium", "receipt-annual.pdf"),
            ("receipt", "Payment Receipt - Q1", "receipt-q1.pdf"),
            ("loss_run", "Loss Run Report 2025", "loss-run-2025.pdf"),
            ("policy", "EPL Policy Declaration", "epl-declaration.pdf"),
        ]

        for category, title, filename in doc_data:
            UserDocument.objects.create(
                user=user,
                organization=personal_org,
                category=category,
                title=title,
                file_type=category,
                original_filename=filename,
                file_size=random.randint(50000, 500000),
                mime_type="application/pdf",
                s3_key=f"users/{user.id}/documents/{category}/{filename}",
                s3_url=f"https://corgi-docs.s3.amazonaws.com/users/{user.id}/documents/{category}/{filename}",
            )
        self.stdout.write(f"  Created {len(doc_data)} documents")

        # ── Second Organization ──────────────────────────────────
        team_org = Organization.objects.create(
            name="TechVault Insurance Team",
            owner=user,
            is_personal=False,
            industry="Technology",
            phone="(415) 555-0100",
            billing_email="billing@techvault.io",
            website="https://techvault.io",
        )
        OrganizationMember.objects.create(
            organization=team_org, user=user, role="owner"
        )

        # Create additional team members
        team_members = [
            ("emily@techvault.io", "Emily", "Chen", "editor"),
            ("marcus@techvault.io", "Marcus", "Johnson", "viewer"),
            ("sarah@techvault.io", "Sarah", "Williams", "editor"),
        ]
        for email, first, last, role in team_members:
            member_user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "company_name": "TechVault Inc.",
                    "is_active": True,
                },
            )
            if _:
                member_user.set_password("testpass123")
                member_user.save()
            OrganizationMember.objects.get_or_create(
                organization=team_org,
                user=member_user,
                defaults={"role": role},
            )
        self.stdout.write(
            f"  Created organization: {team_org.name} with {len(team_members) + 1} members"
        )

        # Create an invite for the team org
        OrganizationInvite.objects.create(
            organization=team_org,
            code=OrganizationInvite.generate_code(),
            created_by=user,
            default_role="viewer",
            max_uses=10,
        )

        # ── Notifications ────────────────────────────────────────
        notifications = [
            (
                "success",
                "Policy Bound",
                "Your Tech E&O policy has been successfully bound. Policy documents are available in your Documents tab.",
                "/documents",
            ),
            (
                "info",
                "Quote Ready",
                "Your Commercial GL quote is ready for review. Annual premium: $2,200.",
                "/quotes",
            ),
            (
                "warning",
                "Payment Due",
                "Your D&O monthly payment of $266.67 is due in 3 days.",
                "/billing",
            ),
            (
                "claim_update",
                "Claim Update",
                "Your cyber incident claim CLM-2024-001 is now under review by our adjusters.",
                "/claims",
            ),
            (
                "quote_update",
                "Quote Needs Review",
                "Your MediSync quote requires underwriter review for cyber coverage.",
                "/quotes",
            ),
            (
                "system",
                "Welcome to Corgi",
                "Welcome! Your account has been set up. Start by exploring your coverage options.",
                "/quotes",
            ),
        ]

        for ntype, title, message, url in notifications:
            Notification.objects.create(
                user=user,
                organization=personal_org,
                notification_type=ntype,
                title=title,
                message=message,
                action_url=url,
                read_at=now - timedelta(hours=random.randint(1, 48))
                if random.random() > 0.4
                else None,
            )
        self.stdout.write(f"  Created {len(notifications)} notifications")

        # ── Audit Log ────────────────────────────────────────────
        audit_entries = [
            ("create", "Quote", created_quotes[0].quote_number, {}),
            (
                "update",
                "Quote",
                created_quotes[0].quote_number,
                {"status": {"old": "draft", "new": "submitted"}},
            ),
            ("create", "Policy", created_policies[0].policy_number, {}),
            ("login", "User", str(user.id), {}),
            ("create", "Claim", "CLM-SEED-001", {}),
            (
                "update",
                "Policy",
                created_policies[2].policy_number,
                {"billing_frequency": {"old": "annual", "new": "monthly"}},
            ),
        ]

        for action, model, obj_id, changes in audit_entries:
            AuditLogEntry.objects.create(
                user=user,
                action=action,
                model_name=model,
                object_id=obj_id,
                changes=changes,
                ip_address="127.0.0.1",
            )
        self.stdout.write(f"  Created {len(audit_entries)} audit log entries")

        self.stdout.write(self.style.SUCCESS("\n✅ Test data seeded successfully!"))
        self.stdout.write("   User: sergio@corgi.com")
        self.stdout.write(f"   Companies: {len(companies)}")
        self.stdout.write(f"   Quotes: {len(created_quotes)}")
        self.stdout.write(f"   Policies: {len(created_policies)}")
        self.stdout.write("   Claims: 3")
        self.stdout.write(f"   Certificates: {len(cert_holders)}")
        self.stdout.write(f"   Documents: {len(doc_data)}")
        self.stdout.write("   Organizations: 2 (personal + team)")

    def _flush(self, user, personal_org):
        """Delete seeded test data (preserving the user and personal org)."""
        self.stdout.write("Flushing existing test data...")
        AuditLogEntry.objects.filter(user=user).delete()
        Notification.objects.filter(user=user).delete()
        CustomCertificate.objects.filter(user=user).delete()
        Claim.objects.filter(user=user).delete()
        # Delete policies through quotes
        for q in Quote.objects.filter(user=user):
            Policy.objects.filter(quote=q).delete()
        Quote.objects.filter(user=user).delete()
        UserDocument.objects.filter(user=user).delete()
        # Delete non-personal orgs
        for org in Organization.objects.filter(owner=user, is_personal=False):
            OrganizationInvite.objects.filter(organization=org).delete()
            OrganizationMember.objects.filter(organization=org).delete()
            org.delete()
        self.stdout.write(self.style.WARNING("  Existing test data deleted"))
