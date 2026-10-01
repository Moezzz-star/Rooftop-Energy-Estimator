"""Base Django settings shared by all environments.

Environment-specific modules (``dev``, ``prod``, ``test``) import ``*`` from
here and override as needed. All environment-driven values are read through
``django-environ`` with sane defaults; secrets are never hardcoded.

See ``docs/architecture/code-architecture.md`` §6 and
``docs/architecture/system-architecture.md`` §3-4 for the authoritative
conventions this module implements.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import environ

from config.logging import get_logging_config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# backend/config/settings/base.py -> BASE_DIR = backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Load a local .env file when present (never committed with secrets).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
# Dev/test provide a fallback in their own modules; base requires an explicit
# value so production never boots with an insecure default.
SECRET_KEY: str = env.str("SECRET_KEY", default="")

DEBUG: bool = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
]

# Domain apps are implemented by other engineers; they are pre-registered here
# so those engineers only need to fill in each app package. App label names:
# accounts, projects, analyses, geospatial, imagery, solar, ml_models, jobs,
# exports, audit.
LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.projects",
    "apps.analyses",
    "apps.geospatial",
    "apps.imagery",
    "apps.solar",
    "apps.ml_models",
    "apps.jobs",
    "apps.exports",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database (PostGIS)
# ---------------------------------------------------------------------------
# DATABASE_URL is parsed by django-environ; the engine is forced to the PostGIS
# backend so GeoDjango features are available.
DATABASES: dict[str, dict[str, Any]] = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgis://postgres:postgres@localhost:5432/rooftop",
    ),
}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env.str("MEDIA_ROOT", default=str(BASE_DIR / "media")))

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exception_handler.drf_exception_handler",
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402  (grouped with its consumer)

SIMPLE_JWT: dict[str, Any] = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# drf-spectacular
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS: dict[str, Any] = {
    "TITLE": "Rooftop Energy Estimator API",
    "DESCRIPTION": "REST API for rooftop solar PV potential estimation.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = (
    *default_headers,
    "idempotency-key",
)

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
REDIS_URL: str = env.str("REDIS_URL", default="redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Reliability controls (system-arch §3): survive worker loss, never double-ack.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Time limits (seconds): soft raises inside the task, hard kills the worker.
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_SOFT_TIME_LIMIT", default=1500)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_HARD_TIME_LIMIT", default=1800)

CELERY_TASK_DEFAULT_QUEUE = "orchestration"

# Route lightweight orchestration to the ``orchestration`` queue and heavy
# raster/inference/vectorize/pvlib/export work to ``cpu-heavy`` (§3, ADR-0004).
CELERY_TASK_ROUTES: dict[str, dict[str, str]] = {
    "apps.jobs.tasks.run_analysis_pipeline": {"queue": "orchestration"},
    "apps.jobs.tasks.*": {"queue": "orchestration"},
    "apps.imagery.tasks.*": {"queue": "cpu-heavy"},
    "apps.geospatial.tasks.*": {"queue": "cpu-heavy"},
    "apps.solar.tasks.*": {"queue": "cpu-heavy"},
    "apps.ml_models.tasks.*": {"queue": "cpu-heavy"},
    "apps.exports.tasks.*": {"queue": "cpu-heavy"},
}

# ---------------------------------------------------------------------------
# Object storage abstraction (system-arch §4)
# ---------------------------------------------------------------------------
# Selects the ObjectStorage implementation returned by common.storage.get_storage.
STORAGE_BACKEND: str = env.str("STORAGE_BACKEND", default="filesystem")

# S3/MinIO configuration consumed only when STORAGE_BACKEND == "s3".
AWS_S3_ENDPOINT_URL: str = env.str("AWS_S3_ENDPOINT_URL", default="")
AWS_STORAGE_BUCKET_NAME: str = env.str("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME: str = env.str("AWS_S3_REGION_NAME", default="")

# Best-effort model presence probe used by the readiness endpoint.
ML_MODEL_PATH: str = env.str("ML_MODEL_PATH", default="")

# ---------------------------------------------------------------------------
# Security defaults (toggled per-environment)
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS: list[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = get_logging_config(debug=DEBUG)
