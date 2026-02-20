from pathlib import Path
import os
import sys
import warnings
from urllib.parse import urlparse

from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables - prioritize local .env, fallback to .env.production
_production_env = BASE_DIR / ".env.production"
_loaded_env = False


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _load_env_file(path: Path) -> bool:
    if path.is_file():
        load_dotenv(dotenv_path=path)
        return True
    return False


_explicit_env_file = os.getenv("DJANGO_ENV_FILE") or os.getenv("ENV_FILE")
if _explicit_env_file:
    explicit_path = Path(_explicit_env_file)
    if not explicit_path.is_absolute():
        explicit_path = BASE_DIR / explicit_path
    if _load_env_file(explicit_path):
        _loaded_env = True
    else:
        warnings.warn(f"Specified env file '{explicit_path}' not found; skipping.", RuntimeWarning)

if not _loaded_env:
    for candidate in (
        BASE_DIR / ".env.local",
        BASE_DIR / ".env",
    ):
        if _load_env_file(candidate):
            _loaded_env = True
            break

if not _loaded_env and _is_truthy(os.getenv("DJANGO_LOAD_PRODUCTION_DOTENV")):
    if _load_env_file(_production_env):
        _loaded_env = True

if not _loaded_env:
    # Load from default .env if it exists in parent directories
    load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    value = value.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return [] if default is None else list(default)
    normalized = raw.replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        if value.strip() == "":
            continue
        return value
    return None


_PLACEHOLDER_HOST_VALUES = {"host", "hostname"}
_PLACEHOLDER_USER_VALUES = {"user", "username"}
_PLACEHOLDER_PASSWORD_VALUES = {"password", "pass"}

# When using runserver, never redirect to HTTPS (runserver only supports HTTP).
RUNNING_RUNSERVER = "runserver" in sys.argv

def _is_placeholder(value: str | None, placeholders: set[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in placeholders


def _database_url_is_placeholder(database_url: str) -> bool:
    normalized = database_url.strip().lower()
    # Quick check for the sample URL in .env.example.
    if "user:password@host" in normalized:
        return True
    parsed = urlparse(database_url)
    placeholder_hits = 0
    if _is_placeholder(parsed.username, _PLACEHOLDER_USER_VALUES):
        placeholder_hits += 1
    if _is_placeholder(parsed.password, _PLACEHOLDER_PASSWORD_VALUES):
        placeholder_hits += 1
    if _is_placeholder(parsed.hostname, _PLACEHOLDER_HOST_VALUES):
        placeholder_hits += 1
    return placeholder_hits >= 2


def _db_vars_placeholder_fields(db_host: str | None, db_user: str | None, db_password: str | None) -> list[str]:
    placeholders = []
    if _is_placeholder(db_host, _PLACEHOLDER_HOST_VALUES):
        placeholders.append("DB_HOST")
    if _is_placeholder(db_user, _PLACEHOLDER_USER_VALUES):
        placeholders.append("DB_USER")
    if _is_placeholder(db_password, _PLACEHOLDER_PASSWORD_VALUES):
        placeholders.append("DB_PASSWORD")
    return placeholders

# Helpful flags derived from environment for consistent HTTPS behavior
BASE_URL_SERVER = os.getenv("BASE_URL_SERVER", "")
SERVER_URL_IS_HTTPS = BASE_URL_SERVER.lower().startswith("https://")
_base_url_hostname = (urlparse(BASE_URL_SERVER).hostname or "").strip().lower() if BASE_URL_SERVER else ""

# Coolify deployment platform support - use COOLIFY_FQDN if available
COOLIFY_FQDN = (os.getenv("COOLIFY_FQDN") or "").strip().lower()
if COOLIFY_FQDN and not _base_url_hostname:
    # If BASE_URL_SERVER is not set but COOLIFY_FQDN is, derive from it
    _base_url_hostname = COOLIFY_FQDN

# --- Core ---
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-this-in-production")
DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "globaldesignerhub.com",
    "www.globaldesignerhub.com",
]
if os.getenv("ALLOWED_HOSTS"):
    # Allow overriding via env (comma-separated)
    ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS").split(",") if h.strip()]

# Add COOLIFY_FQDN to ALLOWED_HOSTS if set
if COOLIFY_FQDN and COOLIFY_FQDN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(COOLIFY_FQDN)
    # Also add www variant if not already present
    if not COOLIFY_FQDN.startswith("www.") and f"www.{COOLIFY_FQDN}" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(f"www.{COOLIFY_FQDN}")
if DEBUG:
    # Allow Django test client and local dev hostnames
    ALLOWED_HOSTS += ["testserver", "0.0.0.0"]
if DEBUG:
    SECURE_SSL_REDIRECT = False
else:
    SECURE_SSL_REDIRECT = True


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  
CSRF_TRUSTED_ORIGINS = [
    "https://globaldesignerhub.com",
    "https://www.globaldesignerhub.com",
]

# If BASE_URL_SERVER is provided, trust/allow its hostname automatically.
if _base_url_hostname:
    if _base_url_hostname not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_base_url_hostname)
    if f"www.{_base_url_hostname}" not in ALLOWED_HOSTS and not _base_url_hostname.startswith("www."):
        ALLOWED_HOSTS.append(f"www.{_base_url_hostname}")

    scheme = (urlparse(BASE_URL_SERVER).scheme or "").strip().lower()
    if scheme in {"http", "https"}:
        origin = f"{scheme}://{_base_url_hostname}"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
    elif COOLIFY_FQDN:
        # If COOLIFY_FQDN is set but BASE_URL_SERVER scheme is missing, use https for production
        # Check COOLIFY_URL for scheme, otherwise default to https
        coolify_url = (os.getenv("COOLIFY_URL") or "").strip().lower()
        if coolify_url.startswith("https://"):
            origin = f"https://{_base_url_hostname}"
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)
        elif not DEBUG:
            # In production without explicit scheme, default to https
            origin = f"https://{_base_url_hostname}"
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)

# --- Canonical host enforcement ---
# Prefer COOLIFY_FQDN if available, then CANONICAL_HOST, then default
CANONICAL_HOST = (
    COOLIFY_FQDN or 
    os.getenv("CANONICAL_HOST") or 
    _base_url_hostname or 
    "globaldesignerhub.com"
).strip().lower()
if CANONICAL_HOST == "":
    CANONICAL_HOST = ""

_canonical_aliases_env = os.getenv("CANONICAL_REDIRECT_HOSTS")
if _canonical_aliases_env:
    CANONICAL_REDIRECT_HOSTS = [
        host.strip().lower()
        for host in _canonical_aliases_env.split(",")
        if host.strip()
    ]
else:
    CANONICAL_REDIRECT_HOSTS = []
    if CANONICAL_HOST:
        if CANONICAL_HOST.startswith("www."):
            CANONICAL_REDIRECT_HOSTS.append(CANONICAL_HOST[4:])
        else:
            CANONICAL_REDIRECT_HOSTS.append(f"www.{CANONICAL_HOST}")

CANONICAL_REDIRECT_HOSTS = [
    host for host in CANONICAL_REDIRECT_HOSTS if host and host != CANONICAL_HOST
]

def _default_forum_url() -> str:
    value = os.getenv("COMMUNITY_FORUM_URL", "https://globaldesignerhub.com/community").strip()
    return value or "https://globaldesignerhub.com/community"

COMMUNITY_FORUM_URL = _default_forum_url()

def _default_ios_app_name() -> str:
    value = os.getenv("IOS_APP_NAME", "GlobalDesignerHub").strip()
    return value or "GlobalDesignerHub"

IOS_APP_NAME = _default_ios_app_name()

# Mobile app distribution links (optional)
IOS_APP_STORE_URL = os.getenv("IOS_APP_STORE_URL", "").strip()
IOS_TESTFLIGHT_URL = os.getenv("IOS_TESTFLIGHT_URL", "").strip()

CANONICAL_DOMAIN_REDIRECT_ENABLED = env_bool(
    "CANONICAL_DOMAIN_REDIRECT_ENABLED",
    default=bool(CANONICAL_HOST) and not DEBUG,
)

_canonical_scheme_env = (os.getenv("CANONICAL_REDIRECT_SCHEME") or "").strip().lower()
if _canonical_scheme_env in {"http", "https"}:
    CANONICAL_REDIRECT_SCHEME = _canonical_scheme_env
else:
    CANONICAL_REDIRECT_SCHEME = "https" if (not DEBUG or SERVER_URL_IS_HTTPS) else ""

for _host in [CANONICAL_HOST, *CANONICAL_REDIRECT_HOSTS]:
    if _host and _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

# In development (DEBUG=True), do not require HTTPS for cookies to allow local testing,
# unless the configured server URL is HTTPS (e.g., production .env but DEBUG left True).
SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    default=(not DEBUG or SERVER_URL_IS_HTTPS),
)
CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    default=(not DEBUG or SERVER_URL_IS_HTTPS),
)

# Enforce HTTPS redirects in production only. When running runserver, never redirect to HTTPS.
SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    default=(not DEBUG),
)
if DEBUG:
    SECURE_SSL_REDIRECT = False
if RUNNING_RUNSERVER:
    SECURE_SSL_REDIRECT = False  # runserver only supports HTTP; ignore env and DEBUG

# --- Suspicious request filtering / throttling ---
SUSPICIOUS_REQUEST_FILTER_ENABLED = env_bool("SUSPICIOUS_REQUEST_FILTER_ENABLED", default=not DEBUG)
_configured_suspicious_patterns = env_list("SUSPICIOUS_PATH_PATTERNS")
SUSPICIOUS_PATH_PATTERNS = _configured_suspicious_patterns or None
SUSPICIOUS_REQUEST_RATE_LIMIT = int(os.getenv("SUSPICIOUS_REQUEST_RATE_LIMIT", "120"))
SUSPICIOUS_REQUEST_RATE_WINDOW = int(os.getenv("SUSPICIOUS_REQUEST_RATE_WINDOW", "60"))

# Local dev: use http://127.0.0.1:PORT (e.g. 8004) — do not change to https; runserver only supports HTTP.
if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8004",
        "http://127.0.0.1:8006",
        "http://localhost:8000",
        "http://localhost:8004",
        "http://localhost:8006",
    ]

# --- Apps ---
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django_filters",
    "social_django",
    
    # Local
    "designer_portfolio.apps.DesignerPortfolioConfig",
    "marketing",
]

# --- REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "designer Fashion Portfolio API",
    "DESCRIPTION": "REST API for Manya’s fashion portfolio (brand designer).",
    "VERSION": "1.0.0",
}

# --- Middleware ---
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "designer_portfolio.middleware.ForceHttpForLocalhostMiddleware",
    # WhiteNoise should be directly after SecurityMiddleware so static files
    # are served before any custom redirect/throttle middleware runs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "designer_portfolio.middleware.CanonicalDomainRedirectMiddleware",
    "designer_portfolio.middleware.SuspiciousRequestThrottleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "designer_portfolio.middleware.UTMTrackingMiddleware",  # ✅ capture UTM/session attribution
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "gdh.urls"

# --- Static & Media ---
STATIC_URL = "/static/"
# Do not include app static directories here; AppDirectoriesFinder already handles them.
# Keeping this empty avoids duplicate collection of the same files.
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"


def _normalize_storage_location(value: str | None, fallback: str) -> str:
    location = (value or fallback).strip().strip("/")
    return location or fallback.strip("/")


def _media_location(env_name: str, suffix: str) -> str:
    default_location = f"{AWS_S3_MEDIA_LOCATION}/{suffix}"
    return _normalize_storage_location(os.getenv(env_name, default_location), default_location)


AWS_S3_MEDIA_LOCATION = _normalize_storage_location(
    os.getenv("AWS_S3_MEDIA_LOCATION", "media"),
    "media",
)
AWS_S3_DOMAIN_LOCATIONS = {
    "designers_accounts": _media_location(
        "AWS_S3_DESIGNERS_ACCOUNTS_LOCATION",
        "designers/accounts",
    ),
    "viewers_accounts": _media_location(
        "AWS_S3_VIEWERS_ACCOUNTS_LOCATION",
        "viewers/accounts",
    ),
    "techpacks": _media_location("AWS_S3_TECHPACKS_LOCATION", "techpacks"),
    "orders": _media_location("AWS_S3_ORDERS_LOCATION", "orders"),
    "events": _media_location("AWS_S3_EVENTS_LOCATION", "events"),
    "collections": _media_location("AWS_S3_COLLECTIONS_LOCATION", "collections"),
}

# Use S3 for media in production to avoid losing uploads on deploys
USE_S3_MEDIA = env_bool("USE_S3_MEDIA", default=False)

if USE_S3_MEDIA:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", None)
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", "")
    AWS_S3_SIGNATURE_VERSION = os.getenv("AWS_S3_SIGNATURE_VERSION", "s3v4")
    AWS_QUERYSTRING_AUTH = False

    # Django 5 STORAGES API
    STORAGES = {
        "default": {"BACKEND": "gdh.storages.MediaStorage"},
        "designers_accounts": {"BACKEND": "gdh.storages.DesignersAccountsStorage"},
        "viewers_accounts": {"BACKEND": "gdh.storages.ViewersAccountsStorage"},
        "techpacks": {"BACKEND": "gdh.storages.TechpacksStorage"},
        "orders": {"BACKEND": "gdh.storages.OrdersStorage"},
        "events": {"BACKEND": "gdh.storages.EventsStorage"},
        "collections": {"BACKEND": "gdh.storages.CollectionsStorage"},
        # staticfiles backend adjusted below based on DEBUG
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_S3_MEDIA_LOCATION}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{AWS_S3_MEDIA_LOCATION}/"
    MEDIA_ROOT = None  # S3 does not use local MEDIA_ROOT
else:
    # Local filesystem media (development)
    MEDIA_URL = f"/{AWS_S3_MEDIA_LOCATION}/"
    MEDIA_ROOT = BASE_DIR / AWS_S3_MEDIA_LOCATION

    def _local_storage_options(alias: str) -> dict[str, str]:
        relative_path = AWS_S3_DOMAIN_LOCATIONS[alias]
        media_prefix = f"{AWS_S3_MEDIA_LOCATION}/"
        if relative_path.startswith(media_prefix):
            relative_path = relative_path[len(media_prefix) :]
        if relative_path:
            return {
                "location": str(MEDIA_ROOT / Path(relative_path)),
                "base_url": f"{MEDIA_URL}{relative_path}/",
            }
        return {"location": str(MEDIA_ROOT), "base_url": MEDIA_URL}

    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "designers_accounts": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("designers_accounts"),
        },
        "viewers_accounts": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("viewers_accounts"),
        },
        "techpacks": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("techpacks"),
        },
        "orders": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("orders"),
        },
        "events": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("events"),
        },
        "collections": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": _local_storage_options("collections"),
        },
        # staticfiles backend adjusted below based on DEBUG
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# When not using S3, explicitly allow Django to serve /media/ if enabled.
# Many PaaS setups only serve /static/ (via WhiteNoise) unless /media/ is wired up.
SERVE_MEDIA = env_bool("SERVE_MEDIA", default=not USE_S3_MEDIA)

# In DEBUG and test runs, avoid Manifest storage which requires collectstatic
if DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"}

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "designer_portfolio" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "designer_portfolio.context_processors.dashboard_counts",
                "designer_portfolio.context_processors.active_portfolio_template",
                "designer_portfolio.context_processors.utm_context",  # ✅ expose UTM/session attribution
                "designer_portfolio.context_processors.social_login_providers",
                "designer_portfolio.context_processors.messenger_inbox_count",
                "designer_portfolio.context_processors.referral_context",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    }
]

WSGI_APPLICATION = "gdh.wsgi.application"

# --- CSRF ---
# Use a custom failure view that returns friendlier HTML and JSON responses.
CSRF_FAILURE_VIEW = "designer_portfolio.views.csrf_failure"

# --- Database ---
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
RUNNING_TESTS = "test" in sys.argv

if RUNNING_TESTS:
    # Keep tests self-contained; avoid requiring a running Postgres instance.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASE_URL = env_first("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL")
    if DATABASE_URL and _database_url_is_placeholder(DATABASE_URL):
        warnings.warn(
            "DATABASE_URL looks like the example placeholder (USER:PASSWORD@HOST). "
            "Unset DATABASE_URL or replace it with real credentials; falling back to DB_*.",
            RuntimeWarning,
        )
        DATABASE_URL = None
    if DATABASE_URL:
        DATABASES = {
            "default": dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=600,
                ssl_require=False,  # set True only if you use managed PG w/ SSL
            )
        }
    else:
        # Allow configuring Postgres via discrete variables (common in Coolify).
        # DB_* is preferred; POSTGRES_* and PG* equivalents are also accepted.
        DB_HOST = env_first("DB_HOST", "POSTGRES_HOST", "PGHOST")
        DB_NAME = env_first("DB_NAME", "POSTGRES_DB", "PGDATABASE")
        DB_USER = env_first("DB_USER", "POSTGRES_USER", "PGUSER")
        DB_PASSWORD = env_first("DB_PASSWORD", "POSTGRES_PASSWORD", "PGPASSWORD")
        DB_PORT_RAW = env_first("DB_PORT", "POSTGRES_PORT", "PGPORT")
        DB_PORT = DB_PORT_RAW or "5432"

        any_db_vars = any([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT_RAW])
        if not any_db_vars:
            raise RuntimeError(
                "DATABASE_URL is required (Postgres only). Alternatively set "
                "DB_HOST/DB_NAME/DB_USER/DB_PASSWORD (or POSTGRES_*/PG* equivalents) "
                "and optional DB_PORT."
            )

        missing = [
            name
            for name, value in {
                "DB_HOST": DB_HOST,
                "DB_NAME": DB_NAME,
                "DB_USER": DB_USER,
                "DB_PASSWORD": DB_PASSWORD,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required database environment variables: "
                + ", ".join(missing)
                + ". Provide DATABASE_URL instead, or set DB_* variables "
                "(Coolify POSTGRES_*/PG* equivalents are also supported)."
            )

        placeholder_fields = _db_vars_placeholder_fields(DB_HOST, DB_USER, DB_PASSWORD)
        if placeholder_fields and {"DB_HOST", "DB_USER"} & set(placeholder_fields):
            raise RuntimeError(
                "Database environment variables look like placeholder values: "
                + ", ".join(placeholder_fields)
                + ". Replace them with real values, or set DATABASE_URL."
            )

        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": DB_NAME,
                "USER": DB_USER,
                "PASSWORD": DB_PASSWORD,
                "HOST": DB_HOST,
                "PORT": DB_PORT,
                "CONN_MAX_AGE": 600,
            }
        }

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Caching ---
# Use Redis only when explicitly enabled to avoid DNS issues in environments
# where a Redis hostname like "designer-redis" is not resolvable.
USE_REDIS = env_bool("USE_REDIS", default=False)
redis_url = os.getenv("REDIS_URL") or os.getenv("CACHE_URL") or "redis://127.0.0.1:6379/1"

if USE_REDIS:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            },
            "TIMEOUT": 60 * 60,  # 1 hour
        }
    }
    # Use cache-backed sessions when Redis is available
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Fallback: local-memory cache and DB-backed sessions (stable across processes)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-designer-cache",
        }
    }

# --- Sessions ---
if USE_REDIS:
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Store sessions in DB when Redis is disabled/missing
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# --- Email ---
# Email Configuration
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
# Allow Gmail app-password alias used by some hosts.
EMAIL_HOST_PASSWORD = env_first("EMAIL_HOST_PASSWORD", "GMAIL_APP_PASSWORD") or ""

# Use console backend in development if no email credentials configured
if DEBUG and not EMAIL_HOST_USER:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", default=False)  # Use SSL for port 465
    EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", 10))  # Connection timeout in seconds

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "GlobalDesignerHub <no-reply@globaldesignerhub.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMIN_EMAIL = "admin@globaldesignerhub.com"
PRETTYPEARL_CONTACT_EMAIL = os.getenv("PRETTYPEARL_CONTACT_EMAIL", "").strip()

# Password reset settings
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours (in seconds)


LOGIN_REDIRECT_URL = "designer_dashboard"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "login"
AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.linkedin.LinkedinOAuth2",
    "social_core.backends.instagram.InstagramOAuth2",
    "designer_portfolio.auth_backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Custom session age when "Remember Me" is checked (default 30 days)
REMEMBER_ME_SESSION_AGE = int(os.getenv("REMEMBER_ME_SESSION_AGE", 60 * 60 * 24 * 30))

# --- Social Authentication (Google) ---
SOCIAL_AUTH_URL_NAMESPACE = "social"
# Force HTTPS redirects for social auth in production or when BASE_URL_SERVER is HTTPS
SOCIAL_AUTH_REDIRECT_IS_HTTPS = env_bool(
    "SOCIAL_AUTH_REDIRECT_IS_HTTPS",
    default=(not DEBUG or SERVER_URL_IS_HTTPS),
)

# Credentials (from env). Prefer explicit SOCIAL_ vars, fallback to GOOGLE_* for convenience
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY") or os.getenv("GOOGLE_CLIENT_ID", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET", "")

# LinkedIn OAuth (optional)
SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY") or os.getenv("LINKEDIN_CLIENT_ID", "")
SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET") or os.getenv("LINKEDIN_CLIENT_SECRET", "")
SOCIAL_AUTH_LINKEDIN_OAUTH2_SCOPE = env_list("SOCIAL_AUTH_LINKEDIN_OAUTH2_SCOPE", default=["r_liteprofile", "r_emailaddress"])
SOCIAL_AUTH_LINKEDIN_OAUTH2_FIELD_SELECTORS = ["emailAddress", "firstName", "lastName"]
SOCIAL_AUTH_LINKEDIN_OAUTH2_EXTRA_DATA = [
    ("id", "id"),
    ("firstName", "first_name"),
    ("lastName", "last_name"),
    ("emailAddress", "email"),
]

# Instagram Basic Display (optional)
SOCIAL_AUTH_INSTAGRAM_KEY = os.getenv("SOCIAL_AUTH_INSTAGRAM_KEY") or os.getenv("INSTAGRAM_CLIENT_ID", "")
SOCIAL_AUTH_INSTAGRAM_SECRET = os.getenv("SOCIAL_AUTH_INSTAGRAM_SECRET") or os.getenv("INSTAGRAM_CLIENT_SECRET", "")
SOCIAL_AUTH_INSTAGRAM_SCOPE = env_list("SOCIAL_AUTH_INSTAGRAM_SCOPE", default=["user_profile"])

# Redirects for social auth
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/dashboard/"
SOCIAL_AUTH_LOGIN_ERROR_URL = "/accounts/login/"
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "email", "profile"]
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {"prompt": "select_account"}
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "designer_portfolio.social_pipeline.ensure_verified_email",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.social_auth.associate_by_email",
    "designer_portfolio.social_pipeline.generate_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "designer_portfolio.social_pipeline.sync_user_details",
    "designer_portfolio.social_pipeline.credit_referral_on_social_signup",
    "designer_portfolio.social_pipeline.send_welcome_notification",
)


# --- WebAuthn / Passkeys ---
_derived_rp_id = os.getenv("WEBAUTHN_RP_ID")
if not _derived_rp_id:
    if BASE_URL_SERVER:
        _derived_rp_id = urlparse(BASE_URL_SERVER).hostname or "localhost"
    else:
        _derived_rp_id = "localhost"

WEBAUTHN_RP_ID = _derived_rp_id
WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "GlobalDesignerHub Designer")

if os.getenv("WEBAUTHN_ORIGIN"):
    WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN").rstrip("/")
elif BASE_URL_SERVER:
    WEBAUTHN_ORIGIN = BASE_URL_SERVER.rstrip("/")
elif DEBUG:
    WEBAUTHN_ORIGIN = "http://localhost:8000"
else:
    WEBAUTHN_ORIGIN = f"https://{WEBAUTHN_RP_ID}"

WEBAUTHN_ALLOW_INSECURE_LOCALHOST = env_bool(
    "WEBAUTHN_ALLOW_INSECURE_LOCALHOST",
    default=DEBUG,
)
