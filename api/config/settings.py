from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv()

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-w_(3r_#5jf!%op1de_+89vrx$l%8pl%$-3=q=4&l%#x&nzly+$",
)
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment="development" if DEBUG else "production",
            send_default_pii=True,
            integrations=[
                DjangoIntegration(
                    transaction_style="url",
                    middleware_spans=True,
                ),
                LoggingIntegration(
                    level=None,
                    event_level="ERROR",
                ),
            ],
        )
    except Exception:
        pass

_DEFAULT_ALLOWED_HOSTS = (
    "localhost,127.0.0.1,"
    "app.corgiinsure.com,test.corgiinsure.com,ops.corgiinsure.com,"
    ".corgiinsure.com"
)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", _DEFAULT_ALLOWED_HOSTS).split(",")
    if host.strip()
]


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_q",
    "auditlog",
    "corsheaders",
    "explorer",
    "common",
    "s3",
    "emails",
    "pdf",
    "documents_generator",
    "ai",
    "skyvern",
    "stripe_integration",
    "quotes",
    "policies",
    "producers",
    "claims",
    "users",
    "scripts",
    "certificates",
    "organizations",
    "api_keys",
    "external_api",
    "brokered",
    "forms",
    "sla",
    "carriers",
    "hubspot_sync",
    "products",
    "webhooks",
    "analytics",
    "analysis",
    "document_management",
    "knowledge_base",
    "demos",
    "ninja",
    "aib",
]

AUTH_USER_MODEL = "users.User"

# ═══════ django-q2 Background Tasks ═══════
Q_CLUSTER = {
    "name": "corgi",
    "workers": 2,
    "timeout": 300,
    "retry": 360,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",  # Uses database as broker (Redis config available via REDIS_URL)
    "catch_up": False,
}

MIDDLEWARE = [
    "common.middleware.CorrelationIdMiddleware",
    "common.version_middleware.ApiVersionMiddleware",
    "common.middleware.RequestTimingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.SessionActivityMiddleware",
    "common.middleware.AuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ═══════ Upload Size Limits ═══════
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB max
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "corgi"),
        "USER": os.getenv("DATABASE_USER", "corgi_admin"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "Corg1Secure2026x"),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

# Always allow subdomain origins for SSO cross-app auth
CORS_ALLOWED_ORIGINS += [
    origin.strip()
    for origin in os.getenv("SSO_CORS_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "https://app.corgiinsure.com",
    "https://portal.corgiinsure.com",
    "https://admin.corgiinsure.com",
    "https://policy.corgiinsure.com",
    "https://premium.corgiinsure.com",
    "https://investor.corgiinsure.com",
    "https://corgiinsure.com",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-organization-id",
    "x-correlation-id",
]

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# S3 Configuration
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Email Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
CORGI_NOTIFICATION_EMAIL = "notify@corgi.insure"
HELLO_CORGI_EMAIL = "Corgi <hello@corgi.insure>"
SEND_EMAILS = True
FRONTEND_URL = os.getenv("CORGI_PORTAL_URL", "http://localhost:3000")

# PII Encryption Configuration (V3 #52)
# Generate with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Must be set in production

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ACCESS_TOKEN_LIFETIME = 60 * 60  # 1 hour
JWT_REFRESH_TOKEN_LIFETIME = 60 * 60 * 24 * 7  # 7 days

# SSO Configuration — shared sessions database for cross-app auth
SSO_DATABASE_URL = os.getenv("SSO_DATABASE_URL", "")
SSO_ALLOWED_REDIRECTS = [
    r.strip() for r in os.getenv("SSO_ALLOWED_REDIRECTS", "").split(",") if r.strip()
]
if DEBUG:
    SSO_ALLOWED_REDIRECTS += [
        "http://localhost",
        "http://127.0.0.1",
    ]

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Skyvern Configuration
SKYVERN_API_KEY = os.getenv("SKYVERN_API_KEY")
SKYVERN_WEBHOOK_SECRET = os.getenv("SKYVERN_WEBHOOK_SECRET", "")

# Slack Notifications (V3)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # None = disabled

# HubSpot CRM Sync
HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")  # None = disabled
HUBSPOT_PIPELINE_ID = os.getenv("HUBSPOT_PIPELINE_ID", "default")
HUBSPOT_STAGE_ACTIVE = os.getenv("HUBSPOT_STAGE_ACTIVE", "closedwon")
HUBSPOT_STAGE_PAST_DUE = os.getenv("HUBSPOT_STAGE_PAST_DUE", "closedwon")
HUBSPOT_STAGE_CANCELLED = os.getenv("HUBSPOT_STAGE_CANCELLED", "closedlost")
HUBSPOT_STAGE_EXPIRED = os.getenv("HUBSPOT_STAGE_EXPIRED", "closedlost")
HUBSPOT_STAGE_NON_RENEWED = os.getenv("HUBSPOT_STAGE_NON_RENEWED", "closedlost")
HUBSPOT_WEBHOOK_SECRET = os.getenv(
    "HUBSPOT_WEBHOOK_SECRET", ""
)  # For validating inbound webhooks

# Portal URL
PORTAL_BASE_URL = "http://localhost:3000" if DEBUG else "https://app.corgi.insure"

# Auditlog Configuration
AUDITLOG_CID_GETTER = "common.auditlog_cid.generate_cid"

# ═══════ Caching ═══════
REDIS_URL = os.getenv("REDIS_URL", "")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "db": 1,
            },
            "KEY_PREFIX": "corgi",
            "TIMEOUT": 300,  # 5 minutes default
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "corgi-cache",
            "TIMEOUT": 300,
        }
    }

# ═══════ Rate Limiting ═══════
# Custom rate_limit decorator (common/utils.py) uses Django's cache backend.
# django-ratelimit is available for view-level @ratelimit() if needed.
RATELIMIT_USE_CACHE = "default"
RATELIMIT_ENABLE = os.getenv("RATE_LIMIT_ENABLE", "True") == "True"
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/h")

# ═══════ Structured Logging ═══════
from common.logging import get_logging_config  # noqa: E402

LOGGING = get_logging_config(DEBUG)

# ═══════ Production Security ═══════
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    USE_X_FORWARDED_HOST = True

# ═══════ Reverse-proxy prefix (optional) ═══════
# Only needed when the reverse proxy strips a URL prefix that Django's
# urlpatterns do not already include. With the all-in-one nginx config we
# pass the full path through, so this is a no-op unless explicitly set.
_force_script_name = os.getenv("FORCE_SCRIPT_NAME", "").strip()
if _force_script_name:
    FORCE_SCRIPT_NAME = _force_script_name

# SQL Explorer Configuration
EXPLORER_CONNECTIONS = {"default": "default"}
EXPLORER_AI_API_KEY = OPENAI_API_KEY


def EXPLORER_PERMISSION_VIEW(r):
    return r.user.is_superuser


def EXPLORER_PERMISSION_CHANGE(r):
    return r.user.is_superuser


# ═══════ django-unfold Admin Theme ═══════
from django.templatetags.static import static  # noqa: E402
from django.urls import reverse_lazy  # noqa: E402

UNFOLD = {
    "SITE_TITLE": "Corgi Insurance",
    "SITE_HEADER": "Corgi",
    "SITE_URL": PORTAL_BASE_URL,
    "SITE_SYMBOL": "shield",
    "SITE_LOGO": lambda request: static("admin/img/corgi-logo.svg"),
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "any",
            "href": lambda request: static("admin/img/corgi-logo.svg"),
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "THEME": "light",
    "ENVIRONMENT": "config.settings.environment_callback",
    "DASHBOARD_CALLBACK": "config.dashboard.dashboard_callback",
    "STYLES": [
        lambda request: static("unfold/css/styles.css"),
        lambda request: static("admin/css/custom.css"),
    ],
    "SCRIPTS": [
        lambda request: static("admin/js/hide-empty-badges.js"),
    ],
    "COLORS": {
        "primary": {
            "50": "#fff7ed",
            "100": "#ffedd5",
            "200": "#fed7aa",
            "300": "#fdba74",
            "400": "#fb923c",
            "500": "#ff5c00",
            "600": "#ea580c",
            "700": "#c2410c",
            "800": "#9a3412",
            "900": "#7c2d12",
            "950": "#431407",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Navigation",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": "Quotes",
                        "icon": "request_quote",
                        "link": reverse_lazy("admin:quotes_quote_changelist"),
                        "badge": "config.badges.pending_review_count",
                    },
                    {
                        "title": "Policies",
                        "icon": "verified_user",
                        "link": reverse_lazy("admin:policies_policy_changelist"),
                    },
                    {
                        "title": "Claims",
                        "icon": "gavel",
                        "link": reverse_lazy("admin:claims_claim_changelist"),
                        "badge": "config.badges.open_claims_count",
                    },
                    {
                        "title": "Certificates",
                        "icon": "workspace_premium",
                        "link": reverse_lazy(
                            "admin:certificates_customcertificate_changelist"
                        ),
                    },
                    {
                        "title": "Brokered Requests",
                        "icon": "smart_toy",
                        "link": reverse_lazy(
                            "admin:brokered_brokeredquoterequest_changelist"
                        ),
                        "badge": "config.badges.pending_brokered_count",
                    },
                ],
            },
            {
                "title": "Billing",
                "collapsible": True,
                "items": [
                    {
                        "title": "Payments",
                        "icon": "payments",
                        "link": reverse_lazy("admin:policies_payment_changelist"),
                    },
                    {
                        "title": "Transactions",
                        "icon": "receipt_long",
                        "link": reverse_lazy(
                            "admin:policies_policytransaction_changelist"
                        ),
                    },
                    {
                        "title": "State Allocations",
                        "icon": "map",
                        "link": reverse_lazy(
                            "admin:policies_stateallocation_changelist"
                        ),
                    },
                    {
                        "title": "Cessions",
                        "icon": "percent",
                        "link": reverse_lazy("admin:policies_cession_changelist"),
                    },
                    {
                        "title": "Renewals",
                        "icon": "autorenew",
                        "link": reverse_lazy("admin:policies_policyrenewal_changelist"),
                    },
                ],
            },
            {
                "title": "Users & Orgs",
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": "Organizations",
                        "icon": "corporate_fare",
                        "link": reverse_lazy(
                            "admin:organizations_organization_changelist"
                        ),
                    },
                    {
                        "title": "Members",
                        "icon": "groups",
                        "link": reverse_lazy(
                            "admin:organizations_organizationmember_changelist"
                        ),
                    },
                    {
                        "title": "Invites",
                        "icon": "mail",
                        "link": reverse_lazy(
                            "admin:organizations_organizationinvite_changelist"
                        ),
                    },
                    {
                        "title": "Documents",
                        "icon": "folder_open",
                        "link": reverse_lazy("admin:users_userdocument_changelist"),
                    },
                    {
                        "title": "Producers",
                        "icon": "badge",
                        "link": reverse_lazy("admin:producers_producer_changelist"),
                    },
                    {
                        "title": "API Keys",
                        "icon": "key",
                        "link": reverse_lazy("admin:api_keys_apikey_changelist"),
                    },
                    {
                        "title": "Active Sessions",
                        "icon": "devices",
                        "link": reverse_lazy("admin:users_activesession_changelist"),
                    },
                    {
                        "title": "Login Events",
                        "icon": "login",
                        "link": reverse_lazy("admin:users_loginevent_changelist"),
                    },
                    {
                        "title": "TOTP Devices",
                        "icon": "phonelink_lock",
                        "link": reverse_lazy("admin:users_totpdevice_changelist"),
                    },
                ],
            },
            {
                "title": "Configuration",
                "collapsible": True,
                "items": [
                    {
                        "title": "Coverage Types",
                        "icon": "category",
                        "link": reverse_lazy("admin:quotes_coveragetype_changelist"),
                    },
                    {
                        "title": "Companies",
                        "icon": "business",
                        "link": reverse_lazy("admin:quotes_company_changelist"),
                    },
                    {
                        "title": "Custom Products",
                        "icon": "extension",
                        "link": reverse_lazy("admin:quotes_customproduct_changelist"),
                    },
                    {
                        "title": "Overrides",
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy(
                            "admin:quotes_underwriteroverride_changelist"
                        ),
                    },
                    {
                        "title": "Promo Codes",
                        "icon": "local_offer",
                        "link": reverse_lazy("admin:quotes_promocode_changelist"),
                    },
                    {
                        "title": "Referral Partners",
                        "icon": "handshake",
                        "link": reverse_lazy("admin:quotes_referralpartner_changelist"),
                    },
                    {
                        "title": "Form Definitions",
                        "icon": "dynamic_form",
                        "link": reverse_lazy("admin:forms_formdefinition_changelist"),
                    },
                    {
                        "title": "Form Submissions",
                        "icon": "assignment_turned_in",
                        "link": reverse_lazy("admin:forms_formsubmission_changelist"),
                    },
                    {
                        "title": "Platform Config",
                        "icon": "tune",
                        "link": reverse_lazy("admin:common_platformconfig_changelist"),
                    },
                ],
            },
            {
                "title": "System",
                "collapsible": True,
                "items": [
                    {
                        "title": "Audit Log",
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:common_auditlogentry_changelist"),
                    },
                    {
                        "title": "Data Access Log",
                        "icon": "manage_search",
                        "link": reverse_lazy("admin:common_dataaccesslog_changelist"),
                    },
                    {
                        "title": "Activity History",
                        "icon": "history",
                        "link": reverse_lazy("admin:auditlog_logentry_changelist"),
                    },
                    {
                        "title": "Notifications",
                        "icon": "notifications",
                        "link": reverse_lazy("admin:common_notification_changelist"),
                    },
                    {
                        "title": "Knowledge Base",
                        "icon": "menu_book",
                        "link": "/admin/knowledge-base/",
                    },
                    {
                        "title": "HubSpot Sync Log",
                        "icon": "sync",
                        "link": reverse_lazy(
                            "admin:hubspot_sync_hubspotsynclog_changelist"
                        ),
                    },
                ],
            },
            {
                "title": "External Apps",
                "collapsible": True,
                "items": [
                    {
                        "title": "Ops Dashboard ↗",
                        "icon": "monitoring",
                        "link": "/admin/embed/ops-dashboard/",
                    },
                    {
                        "title": "Portal ↗",
                        "icon": "storefront",
                        "link": "/admin/embed/portal/",
                    },
                    {
                        "title": "SQL Explorer",
                        "icon": "database",
                        "link": "/admin/analytics/",
                    },
                ],
            },
        ],
    },
}


def environment_callback(request):
    from django.conf import settings

    if settings.DEBUG:
        return ["Development", "warning"]
    return ["Production", "success"]
