from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponseRedirect
from ninja import NinjaAPI
from config.docs import Scalar
from quotes.api import router as quotes_router
from policies.api import router as policies_router
from claims.api import router as claims_router
from users.api import router as users_router
from stripe_integration.api import router as stripe_router
from stripe_integration.billing_api import router as billing_router
from certificates.api import router as certificates_router
from organizations.api import router as organizations_router
from external_api.api import (
    router as external_quotes_router,
    policies_router as external_policies_router,
    public_router as external_public_router,
)
from brokered.api import router as brokered_router
from admin_api.api import router as admin_router
from forms.api import router as forms_router
from common.signing_api import router as signing_router
from common.config_api import router as config_router
from users.session_api import router as sessions_router
from users.totp_api import router as totp_router
from webhooks.api import router as webhooks_router
from emails.api import router as emails_router
from analytics.widgets_api import (
    public_router as metrics_public_router,
    auth_router as metrics_auth_router,
)
from analytics.api import router as analytics_router
from analysis.api import router as analysis_router
from document_management.api import (
    router as document_management_router,
    public_share_view,
)
from demos.api import router as demos_router
from aib.api import router as aib_router
from common.exceptions import register_exception_handlers

admin.site.site_header = "Corgi Insurance"
admin.site.site_title = "Corgi Insurance"
admin.site.index_title = "Dashboard"

api = NinjaAPI()

register_exception_handlers(api)

api.add_router("/quotes", quotes_router)
api.add_router("/policies", policies_router)
api.add_router("/claims", claims_router)
api.add_router("/users", users_router)
api.add_router("/stripe", stripe_router)
api.add_router("/billing", billing_router)
api.add_router("/certificates", certificates_router)
api.add_router("/organizations", organizations_router)
api.add_router("/brokered", brokered_router)
api.add_router("/admin", admin_router)
api.add_router("/forms", forms_router)
api.add_router("/signing", signing_router)
api.add_router("/auth/sessions", sessions_router)
api.add_router("/auth/totp", totp_router)
api.add_router("/webhooks", webhooks_router)
api.add_router("/emails", emails_router)
api.add_router("/metrics", metrics_public_router)
api.add_router("/metrics", metrics_auth_router)
api.add_router("/analytics", analytics_router)
api.add_router("/analysis", analysis_router)
api.add_router("/document-management", document_management_router)
api.add_router("/config", config_router)
api.add_router("/demos", demos_router)
api.add_router("/aib", aib_router)

external_api = NinjaAPI(
    urls_namespace="external_api",
    title="Corgi External API",
    docs=Scalar(
        settings={
            "theme": "default",
            "layout": "modern",
            "darkMode": False,
            "forceDarkModeState": "light",
            "primaryColor": "#ff5c00",
            "hideDownloadButton": True,
            "defaultOpenFirstTag": True,
            "customCss": """
            .light-mode, :root {
              --scalar-color-1: #1D1D1D;
              --scalar-color-2: #4E4E4E;
              --scalar-color-3: #969696;
              --scalar-color-accent: #ff5c00;
              --scalar-background-1: #ffffff;
              --scalar-background-2: #f5f6f7;
              --scalar-background-3: #e9e9e9;
              --scalar-background-accent: rgba(255, 92, 0, 0.08);
              --scalar-border-color: #d8dee4;
              --scalar-sidebar-background-1: #ffffff;
              --scalar-sidebar-color-1: #1D1D1D;
              --scalar-sidebar-color-2: #4E4E4E;
              --scalar-sidebar-border-color: #d8dee4;
              --scalar-sidebar-item-hover-background: rgba(246, 246, 246, 0.8);
              --scalar-sidebar-item-active-background: #f6f6f6;
              --scalar-color-green: #00B93B;
              --scalar-color-orange: #ff5c00;
              --scalar-color-blue: #1a73e8;
              --scalar-color-red: #ef4444;
              --scalar-color-purple: #8b5cf6;
            }
        """,
        }
    ),
    docs_url="/docs",
    description="""
## Introduction

API keys are issued by the Corgi team. To get one, contact us — we'll send you a one-time invite token. Redeem it by calling:

```http
POST /api/external/v1/invites/{token}/redeem
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Doe",
  "org_name": "Acme Corp",
  "email": "jane@acme.com"
}
```

The response includes your API key. **Copy it immediately — it is shown only once.**

Once you have a key, pass it as a Bearer token on every request:

```http
Authorization: Bearer cg_live_...
```

---

## Environments

| Prefix | Environment |
|--------|-------------|
| `cg_live_` | Production |

---

## Pagination

List endpoints accept `limit` (max `100`, default `50`) and `offset` query parameters.

---

## Endpoints

### Quotes

#### `POST /quotes` — Create a Quote

Submit a quote request. The rating engine runs synchronously and returns the result immediately.

**Response `status` values:**

| Status | Meaning |
|--------|---------|
| `quoted` | All coverages priced; `quote_amount` is populated |
| `needs_review` | One or more coverages require underwriter review (e.g. past claims, non-tech company) |

---

#### `GET /quotes` — List Quotes

Returns all quotes associated with your organization. Supports `limit` and `offset` pagination.

---

#### `GET /quotes/{identifier}` — Get Quote

Retrieve a single quote by `quote_number` or numeric ID.

---

## Coverage Slugs

Only instant-rated coverages are available through the external API.

| Slug | Name |
|------|------|
| `commercial-general-liability` | Commercial General Liability |
| `technology-errors-and-omissions` | Technology E&O |
| `cyber-liability` | Cyber Liability |
| `directors-and-officers` | Directors & Officers |
| `fiduciary-liability` | Fiduciary Liability |
| `hired-and-non-owned-auto` | Hired & Non-Owned Auto |
| `media-liability` | Media Liability |
| `employment-practices-liability` | Employment Practices Liability |

---

## Company Fields

| Field | Type | Required | Values / Notes |
|-------|------|----------|----------------|
| `entity_legal_name` | string | ✅ | Legal name of the business |
| `organization_type` | string | ✅ | `individual` `partnership` `corporation` `llc` `other` |
| `is_for_profit` | string | ✅ | `for-profit` `not-for-profit` |
| `last_12_months_revenue` | number | ✅ | USD |
| `projected_next_12_months_revenue` | number | ✅ | USD |
| `business_description` | string | ✅ | What the business does |
| `is_technology_company` | boolean | ✅ | Must be `true` for instant pricing; `false` triggers review |
| `has_subsidiaries` | boolean | | Default `false` |
| `planned_acquisitions` | boolean | | Default `false` |
| `planned_acquisitions_details` | string | | Required if `planned_acquisitions` is `true` |
| `full_time_employees` | integer | | |
| `part_time_employees` | integer | | |
| `federal_ein` | string | | Used for company deduplication (e.g. `12-3456789`) |
| `business_start_date` | string | | `YYYY-MM-DD` |
| `estimated_payroll` | number | | USD; used for some coverages |
| `business_address.street_address` | string | ✅ | |
| `business_address.city` | string | ✅ | |
| `business_address.state` | string | ✅ | 2-letter US state code |
| `business_address.zip` | string | ✅ | |
| `business_address.suite` | string | | Optional |

---

## Limits & Retentions

Pass per-coverage limits under `limits_retentions`. All values are USD. Omitting a field uses the coverage default.

```json
"limits_retentions": {
  "technology-errors-and-omissions": {
    "aggregate_limit": 1000000,
    "per_occurrence_limit": 1000000,
    "retention": 10000
  }
}
```

### Available values per coverage

**`technology-errors-and-omissions`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 5000, 10000, 15000, 20000, 25000, 50000

**`cyber-liability`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 20000, 30000, 40000, 50000, 60000

**`directors-and-officers`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 5000, 10000, 15000, 20000, 25000, 50000

**`commercial-general-liability`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 500, 1000, 1500, 2000

**`employment-practices-liability`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 5000, 10000, 15000, 20000, 25000, 50000, 75000, 100000

**`fiduciary-liability`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 10000, 20000, 30000, 40000, 50000, 60000

**`hired-and-non-owned-auto`**
- `aggregate_limit`: 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 300, 500, 1000, 1500, 2000

**`media-liability`**
- `aggregate_limit`: 500000, 1000000, 1500000, 2000000, 3000000, 5000000, 10000000
- `per_occurrence_limit`: 500000, 1000000, 2000000, 3000000, 5000000, 10000000
- `retention`: 1000, 5000, 10000, 15000, 20000, 25000, 50000

---

## Coverage Questionnaires

Pass per-coverage questionnaire answers under `coverage_data`. All fields are optional — omitting them uses defaults, but providing accurate data produces better pricing.

### `technology-errors-and-omissions`

| Field | Type | Values |
|-------|------|--------|
| `services_description` | string | Description of tech services provided |
| `service_criticality` | string | `not-critical` `moderately-critical` `highly-critical` |
| `industry_hazards` | array | `healthcare` `fintech` `govtech` `industrial` `none` |
| `has_liability_protections` | boolean | Contractual liability protections in place |
| `has_quality_assurance` | boolean | Formal QA processes |
| `has_prior_incidents` | boolean | Prior E&O claims or incidents |
| `incident_details` | string | Required if `has_prior_incidents` is `true` |
| `uses_ai` | boolean | Services use or incorporate AI |
| `wants_ai_coverage` | boolean | Opt into AI liability endorsement (requires `uses_ai: true`) |
| `ai_coverage_options` | array | `algorithmic-bias-liability` `ai-intellectual-property-liability` `regulatory-investigation-defense-costs` `hallucination-defamation-liability` `training-data-misuse-liability` `data-poisoning-adversarial-attack` `service-interruption-liability` `bodily-injury-property-damage-autonomous-ai` `deepfake-synthetic-media-liability` `civil-fines-penalties` |

### `cyber-liability`

| Field | Type | Values |
|-------|------|--------|
| `employee_band` | string | `under_25` `25_50` `50_250` `250_500` `500_1000` `over_1000` |
| `sensitive_record_count` | string | `under_10k` `10k_100k` `100k_1m` `over_1m` |
| `all_users_have_unique_logins` | boolean | |
| `security_framework_certified` | string | `yes` `no` `in-progress` |
| `regulatory_sublimit` | string | Regulatory defense sublimit as % of limit: `0` `5` `10` `25` `50` `100` |
| `outsources_it` | boolean | |
| `has_past_incidents` | boolean | Prior cyber incidents or breaches |
| `incident_details` | string | Required if `has_past_incidents` is `true` |
| `maintained_compliance` | boolean | In compliance with applicable regulations |
| `compliance_issues_description` | string | Required if `maintained_compliance` is `false` |
| `data_systems_exposure` | array | `stores-sensitive-data` `maintains-large-volume-data` `critical-tech-service` |
| `security_controls` | array | `mfa-required` `backups-incident-plan` `security-training` `security-assessments` |
| `regulations_subject_to` | array | `none` `gdpr` `ccpa-cpra` `hipaa` `glba` |
| `requires_vendor_security` | string | `Yes` `No` `N/A` (requires `outsources_it: true`) |
| `wants_hipaa_penalties_coverage` | boolean | (requires `hipaa` in `regulations_subject_to`) |

### `directors-and-officers`

| Field | Type | Values |
|-------|------|--------|
| `is_publicly_traded` | boolean | |
| `public_offering_details` | string | Required if `is_publicly_traded` is `true` |
| `has_mergers_acquisitions` | boolean | |
| `mergers_acquisitions_details` | string | Required if `has_mergers_acquisitions` is `true` |
| `board_size` | integer | Total number of board members |
| `independent_directors` | integer | Number of independent directors |
| `director_names` | string | Comma-separated names |
| `has_board_meetings` | boolean | Regular board meetings held |
| `funding_raised` | number | Total funding raised (USD) |
| `funding_date` | string | `YYYY-MM-DD` of last funding round |
| `has_financial_audits` | boolean | Annual financial audits conducted |
| `has_legal_compliance_officer` | boolean | |
| `is_profitable` | boolean | |
| `has_indebtedness` | boolean | Outstanding debt obligations |
| `has_breached_loan_covenants` | boolean | (required if `has_indebtedness` is `true`) |

### `commercial-general-liability`

| Field | Type | Values |
|-------|------|--------|
| `primary_operations_hazard` | string | `low-hazard` `moderate-hazard` `elevated-hazard` `high-hazard` |
| `is_address_primary_office` | boolean | Business address is the primary office |
| `office_square_footage` | string | `up_to_2500` `2501_5000` `5001_10000` `10001_25000` `over_25000` |
| `has_contractual_liability` | boolean | Contractual liability assumed under agreements |
| `has_other_exposures` | boolean | |
| `other_exposures_description` | string | Required if `has_other_exposures` is `true` |
| `has_physical_locations` | boolean | Physical locations beyond primary office |
| `physical_locations_description` | string | Required if `has_physical_locations` is `true` |
| `square_footage` | integer | Total square footage across all locations |
| `has_safety_measures` | boolean or string | `Yes` `No` `N/A` |
| `has_hazardous_materials` | boolean | |
| `hazardous_materials_description` | string | Required if `has_hazardous_materials` is `true` |
| `has_products_completed_operations` | boolean | Products/completed operations exposure |
| `products_completed_operations_description` | string | Required if `true` |
| `has_client_site_work` | boolean | Work performed at client sites |
| `client_site_work_description` | string | Required if `has_client_site_work` is `true` |
| `has_quality_control` | string | `Yes` `No` `N/A` |
| `uses_subcontractors` | boolean | |
| `requires_subcontractor_insurance` | boolean | (required if `uses_subcontractors` is `true`) |

### `employment-practices-liability`

| Field | Type | Values |
|-------|------|--------|
| `average_salary_level` | string | `under-75k` `over-75k` |
| `uses_contractors` | boolean | |
| `wants_contractor_epli` | boolean | Add contractor EPLI coverage (requires `uses_contractors: true`) |
| `has_past_layoffs` | boolean | |
| `past_layoff_details` | string | Required if `has_past_layoffs` is `true` |
| `has_planned_layoffs` | boolean | |
| `planned_layoff_details` | string | Required if `has_planned_layoffs` is `true` |
| `has_hourly_employees` | boolean | |
| `is_wage_compliant` | boolean | (required if `has_hourly_employees` is `true`) |
| `has_third_party_interaction` | boolean | Employees interact with third parties (customers, vendors) |
| `has_third_party_training` | boolean | (required if `has_third_party_interaction` is `true`) |
| `hr_policies` | array | `handbook` `training` `reporting` `dedicated-hr` |
| `geographic_spread` | array | `[{"state": "TX", "employee_count": 5}, ...]` — US employees by state |
| `international_spread` | array | `[{"country": "Canada", "employee_count": 2}, ...]` — international employees |
| `contractor_geographic_spread` | array | Same structure; contractors by US state |
| `contractor_international_spread` | array | Same structure; international contractors |

### `fiduciary-liability`

| Field | Type | Values |
|-------|------|--------|
| `benefit_plans_list` | string | Description of benefit plans offered |
| `total_plan_assets` | string | `under_100k` `100k_500k` `500k_1m` `1m_5m` `5m_25m` `25m_100m` `over_100m` |
| `has_defined_benefit_plan` | boolean | |
| `defined_benefit_funding_percent` | number | Funding percentage (required if `has_defined_benefit_plan` is `true`) |
| `has_company_stock_in_plan` | boolean | |
| `company_stock_details` | string | Required if `has_company_stock_in_plan` is `true` |
| `review_frequency` | string | `annually` `every-2-years` `every-3-years` `other` |
| `review_frequency_other` | string | Required if `review_frequency` is `other` |
| `has_regulatory_issues` | boolean | Past or pending regulatory issues |
| `has_significant_changes` | boolean | Significant plan changes in past 12 months |
| `compliance_issues_description` | string | Required if `has_regulatory_issues` or `has_significant_changes` is `true` |
| `has_fiduciary_committee` | boolean | Formal fiduciary committee in place |
| `has_fiduciary_training` | boolean | Fiduciaries receive regular training |
| `has_past_claims` | boolean | Prior fiduciary liability claims |
| `past_claims_details` | string | Required if `has_past_claims` is `true` |
| `recordkeeper` | string | Name of recordkeeper (optional) |
| `third_party_admin` | string | Name of TPA (optional) |
| `custodian` | string | Name of custodian (optional) |
| `investment_advisor` | string | Name of investment advisor (optional) |
| `benefits_broker` | string | Name of benefits broker (optional) |
| `actuary` | string | Name of actuary (optional) |

### `hired-and-non-owned-auto`

| Field | Type | Values |
|-------|------|--------|
| `driver_band` | string | `0_5` `6_10` `11_25` `26_50` `51_100` `101_250` `251_500` `501_1000` `1001_2000` `2001_plus` |
| `has_drivers_under_25` | boolean | Any drivers under age 25 |
| `driving_frequency` | string | `rarely` `occasionally` `regularly` |
| `travel_distance` | string | `local` `long-distance` |
| `has_driver_safety_measures` | boolean | Formal driver safety program |
| `rents_vehicles` | boolean | Company rents vehicles |
| `rental_vehicle_details` | string | Required if `rents_vehicles` is `true` |
| `has_high_value_vehicles` | boolean | Regularly rents high-value vehicles |
| `high_value_vehicle_details` | string | Required if `has_high_value_vehicles` is `true` |
| `has_past_auto_incidents` | boolean | Prior auto incidents or claims |
| `past_auto_incident_details` | string | Required if `has_past_auto_incidents` is `true` |

### `media-liability`

| Field | Type | Values |
|-------|------|--------|
| `has_media_exposure` | boolean | Business publishes or distributes media content |
| `media_content_types` | array | `company-generated` `user-generated` |
| `original_content_volume` | string | `none` `under_100` `100_999` `1k_4999` `5k_19999` `20k_49999` `50k_plus` (pieces/month) |
| `ugc_content_volume` | string | Same values — user-generated content volume |
| `has_content_moderation` | boolean | Content moderation processes in place |
| `moderation_details` | string | Required if `has_content_moderation` is `true` |
| `has_media_controls` | boolean | Editorial controls and review processes |
| `has_past_complaints` | boolean | Prior copyright, defamation, or IP complaints |
| `past_complaint_details` | string | Required if `has_past_complaints` is `true` |
| `uses_third_party_content` | boolean | Uses licensed or third-party content |
| `has_licenses` | boolean | (required if `uses_third_party_content` is `true`) |

---

## Claims History

Pass under `claims_history`. Both fields are optional.

```json
"claims_history": {
  "loss_history": {
    "has_past_claims": false
  },
  "insurance_history": {}
}
```

Setting `has_past_claims: true` triggers underwriter review regardless of coverage tier.
""",
)
external_api.add_router("/quotes", external_quotes_router)
external_api.add_router("/policies", external_policies_router)
external_api.add_router("", external_public_router)


def _timed_check(fn):
    """Run *fn*, return (status_str, elapsed_ms)."""
    import time

    start = time.monotonic()
    try:
        result = fn()
        elapsed = round((time.monotonic() - start) * 1000, 1)
        return result, elapsed
    except Exception as exc:
        elapsed = round((time.monotonic() - start) * 1000, 1)
        return f"error: {exc}", elapsed


def health_check(request):
    import os
    from django.conf import settings
    from django.db import connection

    services = {}

    # ── Required: Database ──
    def check_db():
        connection.ensure_connection()
        return "connected"

    status, ms = _timed_check(check_db)
    services["database"] = {"status": status, "response_ms": ms}

    # ── Optional: Redis ──
    redis_url = getattr(settings, "REDIS_URL", None) or os.getenv("REDIS_URL")
    if redis_url:

        def check_redis():
            import redis as _redis

            r = _redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            return "connected"

        status, ms = _timed_check(check_redis)
    else:
        status, ms = "not configured", 0
    services["redis"] = {"status": status, "response_ms": ms}

    # ── Optional: S3 ──
    s3_bucket = getattr(settings, "S3_BUCKET_NAME", None) or os.getenv("S3_BUCKET_NAME")
    if s3_bucket:

        def check_s3():
            import boto3

            s3 = boto3.client(
                "s3",
                aws_access_key_id=getattr(settings, "S3_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "S3_SECRET_ACCESS_KEY", None),
                region_name=getattr(settings, "S3_REGION", "us-east-1"),
            )
            s3.head_bucket(Bucket=s3_bucket)
            return "connected"

        status, ms = _timed_check(check_s3)
    else:
        status, ms = "not configured", 0
    services["s3"] = {"status": status, "response_ms": ms}

    # ── Optional: Stripe ──
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key:

        def check_stripe():
            import stripe as _stripe

            _stripe.api_key = stripe_key
            _stripe.Account.retrieve()
            return "connected"

        status, ms = _timed_check(check_stripe)
    else:
        status, ms = "not configured", 0
    services["stripe"] = {"status": status, "response_ms": ms}

    # ── Optional: Resend ──
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:

        def check_resend():
            import resend as _resend

            _resend.api_key = resend_key
            _resend.Domains.list()
            return "connected"

        status, ms = _timed_check(check_resend)
    else:
        status, ms = "not configured", 0
    services["resend"] = {"status": status, "response_ms": ms}

    # ── Optional: Sentry ──
    sentry_dsn = os.getenv("SENTRY_DSN")
    services["sentry"] = {
        "status": "configured" if sentry_dsn else "not configured",
        "response_ms": 0,
    }

    # ── Optional: django-q workers ──
    def check_q_workers():
        from django_q.monitor import Stat

        stats = list(Stat.get_all())
        if stats:
            return f"running ({len(stats)} cluster(s))"
        return "no workers detected"

    status, ms = _timed_check(check_q_workers)
    services["task_workers"] = {"status": status, "response_ms": ms}

    # ── Determine overall status ──
    required_services = ["database"]
    optional_services = ["redis", "s3", "stripe", "resend", "sentry", "task_workers"]

    required_ok = all(
        "error" not in str(services[s]["status"]) for s in required_services
    )
    optional_ok = all(
        "error" not in str(services[s]["status"])
        for s in optional_services
        if services[s]["status"] != "not configured"
    )

    if not required_ok:
        overall = "unhealthy"
        http_status = 503
    elif not optional_ok:
        overall = "degraded"
        http_status = 200
    else:
        overall = "healthy"
        http_status = 200

    return JsonResponse(
        {
            "status": overall,
            "version": "1.0.0",
            "services": services,
        },
        status=http_status,
    )


def sentry_debug(request):
    pass


def iframe_view(request, title, url):
    """Render an external app inside the admin layout via iframe."""
    from django.template.response import TemplateResponse

    return TemplateResponse(
        request,
        "admin/iframe_view.html",
        {
            **admin.site.each_context(request),
            "iframe_title": title,
            "iframe_url": url,
            "title": title,
        },
    )


from analytics.admin import register_analytics_admin_urls  # noqa: E402

urlpatterns = [
    path("health/", health_check),
    path("sentry-debug/", sentry_debug),
    path("share/<str:token>", public_share_view, name="public-share-link"),
    path("admin/analytics/", include("explorer.urls")),
    path("admin/knowledge-base/", include("knowledge_base.urls")),
    path(
        "admin/reports/earned-premium/",
        admin.site.admin_view(
            __import__(
                "analytics.admin_views", fromlist=["earned_premium_admin_view"]
            ).earned_premium_admin_view
        ),
        name="analytics_earned_premium_report",
    ),
    path(
        "admin/reports/finance-transactions/",
        admin.site.admin_view(
            __import__(
                "policies.admin", fromlist=["FinanceTransactionsView"]
            ).FinanceTransactionsView
        ),
        name="policies_finance_transactions",
    ),
    path(
        "admin/embed/ops-dashboard/",
        lambda r: HttpResponseRedirect("http://localhost:3001"),
        name="ops-dashboard",
    ),
    path(
        "admin/embed/portal/",
        lambda r: HttpResponseRedirect("http://localhost:3000"),
        name="portal-iframe",
    ),
    *register_analytics_admin_urls(admin.site),
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("api/external/v1/", external_api.urls),
]
