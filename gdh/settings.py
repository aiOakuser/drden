from pathlib import Path
import os
from dotenv import load_dotenv
import socket
import warnings
from urllib.parse import urlparse, unquote
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables - prefer developer overrides, fallback to production
_env_candidates = [
    BASE_DIR / ".env.local",
    BASE_DIR / ".env",
    BASE_DIR / ".env.production",
]

for _env_path in _env_candidates:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        break
else:
    # Load from the default search path if none of the expected files exist
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

# Helpful flags derived from environment for consistent HTTPS behavior
BASE_URL_SERVER = os.getenv("BASE_URL_SERVER", "")
SERVER_URL_IS_HTTPS = BASE_URL_SERVER.lower().startswith("https://")

# --- Core ---
SECRET_KEY = 'django-insecure-ck*q$d@!w83)@m36n=)%3m$jxp6#k53sh86j^i2q*lz1&klq&+'
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
    "designer_portfolio",
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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ compressed static files
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

# --- Database (Prefer DATABASE_URL for persistent DB in production) ---
ENV = (os.getenv("ENV") or "").lower()
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

def _db_settings_from_url(database_url: str):
    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()

    if scheme in {"postgres", "postgresql", "psql", "pgsql"}:
        engine = "django.db.backends.postgresql"
    elif scheme == "mysql":
        engine = "django.db.backends.mysql"
    elif scheme == "sqlite":
        engine = "django.db.backends.sqlite3"
    else:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")

    if engine.endswith("sqlite3"):
        name = parsed.path or (BASE_DIR / "db.sqlite3")
    else:
        # strip leading slash in /dbname
        name = parsed.path[1:] if parsed.path.startswith("/") else parsed.path

    return {
        "ENGINE": engine,
        "NAME": str(name),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }

if DATABASE_URL:
    DATABASES = {"default": _db_settings_from_url(DATABASE_URL)}
else:
    # Default to SQLite unless DB_ENGINE is explicitly set.
    configured_engine = os.getenv("DB_ENGINE") or "django.db.backends.sqlite3"
    db_host_env = os.getenv("DB_HOST", "")
    db_name_env = os.getenv("DB_NAME", "")
    db_user_env = os.getenv("DB_USER", "")

    default_name = (
        str(BASE_DIR / "db.sqlite3") if configured_engine.endswith("sqlite3") else (db_name_env or "postgres")
    )

    DATABASES = {
        "default": {
            "ENGINE": configured_engine,
            "NAME": os.getenv("DB_NAME", default_name),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
        }
    }

    if not str(DATABASES["default"]["ENGINE"]).endswith("sqlite3"):
        DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DB_CONN_MAX_AGE", "60"))

# Fail fast if SQLite is configured in production-like environments.
engine_is_sqlite = DATABASES["default"]["ENGINE"].endswith("sqlite3")
production_like = (not DEBUG)
enforce_persistent_db = os.getenv("ENFORCE_PERSISTENT_DB", "False") == "True"

if production_like and engine_is_sqlite and enforce_persistent_db:
    raise ImproperlyConfigured(
        "SQLite is configured in a production-like environment. Set DATABASE_URL or Postgres DB_* env vars to use a persistent database."
    )

# Warn in any other non-debug scenario as an extra safeguard
if not DEBUG and engine_is_sqlite:
    warnings.warn(
        "SQLite is configured while DEBUG=False. Configure a persistent database via DATABASE_URL to avoid data loss.",
        RuntimeWarning,
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
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = "no-reply@aioak.net"
ADMIN_EMAIL = "chpreddy@gmail.com"


LOGIN_REDIRECT_URL = "designer_dashboard"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "login"
AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
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

# Redirects for social auth
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/dashboard/"
SOCIAL_AUTH_LOGIN_ERROR_URL = "/accounts/login/"
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["email", "profile"]


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
