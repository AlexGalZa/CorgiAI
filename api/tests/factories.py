"""
Test factories for Corgi Insurance platform.

Provides helper functions to create test data with sensible defaults.
All factories support keyword overrides for customization.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from users.models import User
from organizations.models import Organization, OrganizationMember
from quotes.models import Quote, Company, Address, PromoCode
from policies.models import Policy, Payment
from claims.models import Claim
from forms.models import FormDefinition


def create_test_user(email="test@corgi.com", **kwargs):
    """Create a test user with sensible defaults."""
    defaults = {
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "5551234567",
        "company_name": "Test Corp",
        "is_active": True,
        "is_staff": False,
    }
    defaults.update(kwargs)
    user = User.objects.create_user(email=email, **defaults)
    return user


def create_test_staff_user(email="admin@corgi.com", **kwargs):
    """Create a staff user for admin API tests."""
    kwargs.setdefault("is_staff", True)
    return create_test_user(email=email, **kwargs)


def create_test_org(owner=None, **kwargs):
    """Create a test organization with an owner membership."""
    if owner is None:
        owner = create_test_user(email=f"owner-{timezone.now().timestamp()}@corgi.com")

    defaults = {
        "name": "Test Organization",
        "is_personal": False,
    }
    defaults.update(kwargs)
    org = Organization.objects.create(owner=owner, **defaults)
    OrganizationMember.objects.create(organization=org, user=owner, role="owner")
    return org


def create_personal_org(user):
    """Create a personal org for a user (mimics registration flow)."""
    org = Organization.objects.create(
        name="Personal",
        owner=user,
        is_personal=True,
    )
    OrganizationMember.objects.create(organization=org, user=user, role="owner")
    return org


def create_test_address(**kwargs):
    """Create a test address."""
    defaults = {
        "street_address": "123 Main St",
        "suite": "Suite 100",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94104",
        "country": "US",
    }
    defaults.update(kwargs)
    return Address.objects.create(**defaults)


def create_test_company(**kwargs):
    """Create a test company with address."""
    address_kwargs = kwargs.pop("address_kwargs", {})
    address = kwargs.pop("business_address", None) or create_test_address(
        **address_kwargs
    )

    defaults = {
        "business_address": address,
        "entity_legal_name": "Acme Tech Inc.",
        "type": "corporation",
        "profit_type": "for-profit",
        "federal_ein": "12-3456789",
        "last_12_months_revenue": Decimal("1000000.00"),
        "projected_next_12_months_revenue": Decimal("1500000.00"),
        "full_time_employees": 25,
        "part_time_employees": 5,
        "is_technology_company": True,
        "has_subsidiaries": False,
        "planned_acquisitions": False,
        "business_description": "SaaS platform for insurance management",
    }
    defaults.update(kwargs)
    return Company.objects.create(**defaults)


def create_test_quote(user=None, org=None, **kwargs):
    """Create a test quote with company and address."""
    if user is None:
        user = create_test_user(
            email=f"quote-user-{timezone.now().timestamp()}@corgi.com"
        )
    if org is None:
        org = create_personal_org(user)

    company = kwargs.pop("company", None) or create_test_company()

    defaults = {
        "user": user,
        "organization": org,
        "company": company,
        "status": "draft",
        "coverages": ["commercial-general-liability", "cyber-liability"],
        "available_coverages": ["commercial-general-liability", "cyber-liability"],
        "coverage_data": {},
        "limits_retentions": {
            "commercial-general-liability": {
                "aggregate_limit": 1000000,
                "per_occurrence_limit": 1000000,
                "retention": 0,
            },
            "cyber-liability": {
                "aggregate_limit": 1000000,
                "per_occurrence_limit": 1000000,
                "retention": 10000,
            },
        },
        "billing_frequency": "annual",
        "form_data_snapshot": {
            "coverages": ["commercial-general-liability", "cyber-liability"]
        },
        "completed_steps": ["welcome", "package-selection"],
        "current_step": "products",
    }
    defaults.update(kwargs)
    return Quote.objects.create(**defaults)


def create_test_policy(quote=None, **kwargs):
    """Create a test policy from a quote."""
    if quote is None:
        quote = create_test_quote(status="purchased")

    effective = kwargs.pop("effective_date", date.today())
    expiration = kwargs.pop("expiration_date", effective + timedelta(days=365))

    defaults = {
        "quote": quote,
        "coverage_type": "commercial-general-liability",
        "coi_number": "COI-CA-26-000001",
        "limits_retentions": {
            "aggregate_limit": 1000000,
            "per_occurrence_limit": 1000000,
            "retention": 0,
        },
        "premium": Decimal("5000.00"),
        "effective_date": effective,
        "expiration_date": expiration,
        "purchased_at": timezone.now(),
        "status": "active",
        "billing_frequency": "annual",
        "stripe_payment_intent_id": "pi_test_123",
        "stripe_customer_id": "cus_test_123",
        "insured_legal_name": quote.company.entity_legal_name,
        "insured_fein": quote.company.federal_ein,
        "principal_state": quote.company.business_address.state,
        "mailing_address": {
            "street": quote.company.business_address.street_address,
            "city": quote.company.business_address.city,
            "state": quote.company.business_address.state,
            "zip": quote.company.business_address.zip,
        },
    }
    defaults.update(kwargs)
    return Policy.objects.create(**defaults)


def create_test_claim(user=None, policy=None, **kwargs):
    """Create a test claim."""
    if policy is None:
        policy = create_test_policy()
    if user is None:
        user = policy.quote.user

    org = policy.quote.organization

    defaults = {
        "user": user,
        "organization": org,
        "policy": policy,
        "organization_name": "Acme Tech Inc.",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@acme.com",
        "phone_number": "5559876543",
        "description": "Test claim description",
        "status": "submitted",
    }
    defaults.update(kwargs)
    return Claim.objects.create(**defaults)


def create_test_form_definition(**kwargs):
    """Create a test form definition."""
    defaults = {
        "name": "Test Form",
        "slug": f"test-form-{timezone.now().timestamp()}",
        "version": 1,
        "description": "A test form definition",
        "fields": [
            {
                "key": "company_name",
                "label": "Company Name",
                "field_type": "text",
                "required": True,
                "validation": {"min_length": 1, "max_length": 255},
            },
            {
                "key": "revenue",
                "label": "Annual Revenue",
                "field_type": "number",
                "required": True,
                "validation": {"min": 0},
            },
            {
                "key": "has_employees",
                "label": "Has Employees?",
                "field_type": "select",
                "required": False,
                "options": [
                    {"label": "Yes", "value": "yes"},
                    {"label": "No", "value": "no"},
                ],
            },
            {
                "key": "employee_count",
                "label": "Employee Count",
                "field_type": "number",
                "required": False,
                "validation": {"min": 0, "max": 100000},
            },
        ],
        "conditional_logic": {
            "rules": [
                {
                    "target_field": "employee_count",
                    "action": "show",
                    "conditions": [
                        {
                            "field_key": "has_employees",
                            "operator": "equals",
                            "value": "yes",
                        }
                    ],
                    "match": "all",
                }
            ]
        },
        "rating_field_mappings": {
            "revenue": "revenue",
            "employee_count": "employee_count",
        },
        "coverage_type": "cyber-liability",
        "is_active": True,
    }
    defaults.update(kwargs)
    return FormDefinition.objects.create(**defaults)


def create_test_promo_code(**kwargs):
    """Create a test promo code."""
    defaults = {
        "code": f"TEST{int(timezone.now().timestamp())}",
        "discount_type": "percentage",
        "discount_value": Decimal("20.00"),
        "is_active": True,
    }
    defaults.update(kwargs)
    return PromoCode.objects.create(**defaults)


def create_test_payment(policy=None, **kwargs):
    """Create a test payment record."""
    if policy is None:
        policy = create_test_policy()

    defaults = {
        "policy": policy,
        "stripe_invoice_id": f"pi_test_{int(timezone.now().timestamp())}",
        "amount": policy.premium,
        "status": "paid",
        "paid_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Payment.objects.create(**defaults)


def setup_user_with_org():
    """Create a user with personal org and set active_organization_id + active_org_role."""
    user = create_test_user(email=f"user-{timezone.now().timestamp()}@corgi.com")
    org = create_personal_org(user)
    user.active_organization_id = org.id
    user.active_org_role = "owner"
    return user, org
