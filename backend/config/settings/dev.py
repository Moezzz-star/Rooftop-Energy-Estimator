"""Development settings: DEBUG on, permissive CORS, verbose console logging."""

from __future__ import annotations

from config.logging import get_logging_config

from .base import *  # noqa: F403
from .base import env

DEBUG = True

# A predictable, clearly-insecure fallback for local work only. Production
# requires SECRET_KEY via the environment (see prod.py).
SECRET_KEY = env.str("SECRET_KEY", default="dev-insecure-key-change-me")

ALLOWED_HOSTS = ["*"]

# Permissive CORS for the local Vite dev server.
CORS_ALLOW_ALL_ORIGINS = True

LOGGING = get_logging_config(debug=True)
