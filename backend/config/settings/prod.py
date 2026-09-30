"""Production settings: DEBUG off, security headers on, strict host allowlist.

``SECRET_KEY`` and ``DJANGO_ALLOWED_HOSTS`` MUST be provided by the environment;
importing this module with them unset raises ``ImproperlyConfigured`` so the
service fails fast rather than booting insecurely.
"""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from config.logging import get_logging_config

from .base import *  # noqa: F403
from .base import SECRET_KEY, env

DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is required in production.")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Security headers forced on in production regardless of base defaults.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = get_logging_config(debug=False)
