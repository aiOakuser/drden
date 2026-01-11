from pathlib import Path
import os
from dotenv import load_dotenv
import socket
import warnings
from urllib.parse import urlparse, unquote
from django.core.exceptions import ImproperlyConfigured

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

# Helpful flags derived from environment for consistent HTTPS behavior
BASE_URL_SERVER = os.getenv("BASE_URL_SERVER", "")
SERVER_URL_IS_HTTPS = BASE_URL_SERVER.lower().startswith("https://")
_base_url_hostname = (urlparse(BASE_URL_SERVER).hostname or "").strip().lower() if BASE_URL_SERVER else ""

# --- Core ---
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-this-in-production")
DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "globaldesignerhub.com",
    "www.globaldesignerhub.com",
    # AIOAK hosted apps (e.g. finmate.aioak.app)
    "finmate.aioak.app",
]
if os.getenv("ALLOWED_HOSTS"):
    # Allow overriding via env (comma-separated)
    ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS").split(",") if h.strip()]
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
    "https://finmate.aioak.app",
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

# --- Canonical host enforcement ---
CANONICAL_HOST = (os.getenv("CANONICAL_HOST") or "globaldesignerhub.com").strip().lower()
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

# Enforce HTTPS redirects by default in production or when BASE_URL_SERVER is HTTPS
SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    default=(not DEBUG or SERVER_URL_IS_HTTPS),
)

# --- Suspicious request filtering / throttling ---
SUSPICIOUS_REQUEST_FILTER_ENABLED = env_bool("SUSPICIOUS_REQUEST_FILTER_ENABLED", default=not DEBUG)
_configured_suspicious_patterns = env_list("SUSPICIOUS_PATH_PATTERNS")
SUSPICIOUS_PATH_PATTERNS = _configured_suspicious_patterns or None
SUSPICIOUS_REQUEST_RATE_LIMIT = int(os.getenv("SUSPICIOUS_REQUEST_RATE_LIMIT", "120"))
SUSPICIOUS_REQUEST_RATE_WINDOW = int(os.getenv("SUSPICIOUS_REQUEST_RATE_WINDOW", "60"))

# Make local dev origins trusted for CSRF in DEBUG mode
if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
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
        # staticfiles backend adjusted below based on DEBUG
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/"
    MEDIA_ROOT = None  # S3 does not use local MEDIA_ROOT
else:
    # Local filesystem media (development)
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        # staticfiles backend adjusted below based on DEBUG
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

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

# --- Database (PostgreSQL for both local and production) ---
ENV = (os.getenv("ENV") or "").lower()
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
_POSTGRES_SCHEMES = {"postgres", "postgresql", "psql", "pgsql"}
_SQLITE_SCHEMES = {"sqlite", "sqlite3"}


def _sqlite_db_settings(
    path_override: str | None = None,
    *,
    treat_as_relative: bool | None = None,
) -> dict[str, str]:
    """
    Build SQLite settings using either an explicit path override or env defaults.

    treat_as_relative=True forces the resolved path to live under BASE_DIR regardless
    of whether the supplied override starts with a leading slash (useful for sqlite:/// urls).
    """
    env_default = os.getenv("SQLITE_NAME") or os.getenv("DB_NAME") or "designer_db"
    candidate = (path_override or env_default).strip()
    if candidate == "":
        candidate = env_default

    candidate = os.path.expanduser(candidate)
    if candidate in {":memory:", "memory"}:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}

    if treat_as_relative:
        candidate = candidate.lstrip("/\\")

    sqlite_path = Path(candidate)
    if treat_as_relative or not sqlite_path.is_absolute():
        sqlite_path = BASE_DIR / sqlite_path

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(sqlite_path),
    }


def _db_settings_from_url(database_url: str) -> dict[str, str]:
    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()

    if scheme in _SQLITE_SCHEMES:
        raw_path = unquote(parsed.path or "")
        if parsed.netloc:
            raw_path = f"//{parsed.netloc}{raw_path}"
            treat_as_relative = False
        else:
            treat_as_relative = not database_url.startswith("sqlite:////")
        return _sqlite_db_settings(
            path_override=raw_path or None,
            treat_as_relative=treat_as_relative,
        )

    if scheme not in _POSTGRES_SCHEMES:
        raise ImproperlyConfigured(
            "DATABASE_URL must use a PostgreSQL scheme (e.g. postgres://username:password@host:port/dbname or postgresql://username:password@host:port/dbname)."
        )

    path = parsed.path or ""
    if path.startswith("/"):
        path = path[1:]

    host = parsed.hostname or os.getenv("DB_HOST", "127.0.0.1")
    port = parsed.port or os.getenv("DB_PORT", "5432")

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(path or os.getenv("DB_NAME", "designer_db")),
        "USER": unquote(parsed.username or os.getenv("DB_USER", "postgres")),
        "PASSWORD": unquote(parsed.password or os.getenv("DB_PASSWORD", "")),
        "HOST": host,
        "PORT": str(port),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }


def _db_settings_from_env() -> dict[str, str]:
    db_engine = (os.getenv("DB_ENGINE") or "").strip().lower()
    if db_engine in _SQLITE_SCHEMES:
        return _sqlite_db_settings()

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "designer_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }


_db_engine_env = (os.getenv("DB_ENGINE") or "").strip().lower()
_use_sqlite = (_db_engine_env in _SQLITE_SCHEMES) or env_bool("USE_SQLITE", default=False)

_explicit_db_env_present = any(
    (os.getenv(name) or "").strip() != ""
    for name in (
        "DATABASE_URL",
        "DB_URL",
        "DB_ENGINE",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )
)

def _tcp_port_open(host: str, port: int, *, timeout: float = 0.25) -> bool:
    """
    Best-effort reachability check for dev ergonomics.

    We only use this for localhost DB URLs to avoid accidentally masking
    production outages by silently switching databases.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


if _use_sqlite:
    # Explicitly forced via env.
    DATABASES = {"default": _sqlite_db_settings()}
elif DATABASE_URL:
    # Explicit connection string usually wins, but in local/dev it's common for
    # DATABASE_URL to point at localhost even when Postgres isn't running.
    # In that case, fall back to SQLite to keep commands like `migrate` usable.
    parsed = urlparse(DATABASE_URL)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").strip().lower()
    port = int(parsed.port or 5432)

    _is_localhost_postgres = scheme in _POSTGRES_SCHEMES and host in {"localhost", "127.0.0.1", "::1"}
    _allow_localhost_sqlite_fallback = env_bool(
        "ALLOW_SQLITE_FALLBACK_FOR_LOCALHOST_POSTGRES",
        # Only allow the SQLite fallback automatically in DEBUG mode.
        # In container/production environments, localhost refers to *this* container, so
        # falling back can accidentally run production on SQLite and mask DB misconfig.
        default=DEBUG,
    )

    if _is_localhost_postgres and _allow_localhost_sqlite_fallback and not _tcp_port_open(host, port):
        warnings.warn(
            f"PostgreSQL at {host}:{port} is not reachable; falling back to SQLite. "
            "Set ALLOW_SQLITE_FALLBACK_FOR_LOCALHOST_POSTGRES=0 to disable (recommended for production). "
            "If you're deploying in Docker/Coolify, set DB_HOST to your Postgres service name (e.g. 'postgres' or 'db'), not 'localhost'.",
            RuntimeWarning,
        )
        DATABASES = {"default": _sqlite_db_settings()}
    else:
        DATABASES = {"default": _db_settings_from_url(DATABASE_URL)}
elif _explicit_db_env_present:
    # If any DB_* env is provided (even partially), assume Postgres is intended.
    DATABASES = {"default": _db_settings_from_env()}
else:
    # Safe default: if nothing is configured, use local SQLite instead of attempting
    # to connect to Postgres on localhost (common in CI/build containers).
    DATABASES = {"default": _sqlite_db_settings()}

REQUIRE_POSTGRES_DATABASE = env_bool(
    "REQUIRE_POSTGRES_DATABASE",
    # Fail loudly when we're clearly in production (either ENV says so, or the configured
    # base URL is HTTPS). This avoids accidentally running production on SQLite, while
    # still allowing CI/build containers to run management commands without a DB when
    # production env vars are not present.
    default=(not DEBUG and (ENV in {"production", "prod"} or SERVER_URL_IS_HTTPS)),
)

if (
    REQUIRE_POSTGRES_DATABASE
    and DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql"
):
    raise ImproperlyConfigured(
        "PostgreSQL is required for this environment. Set DB_ENGINE=postgres or "
        "disable this check via REQUIRE_POSTGRES_DATABASE=0 if SQLite is acceptable."
    )

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
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

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
ADMIN_EMAIL = "admin@aioak.net"
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
WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "AIOAK Designer")

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
