"""Test settings: fast hashing, eager Celery, isolated PostGIS test database.

The database engine remains PostGIS (spatial fields require it); the actual
server is provided by CI/Docker. Pure-Python unit tests that do not touch the
ORM run without a live database.
"""

from __future__ import annotations

from .base import *  # noqa: F403
from .base import DATABASES

DEBUG = False

SECRET_KEY = "test-insecure-key"

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Fast, insecure password hashing to keep the suite quick.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks synchronously in-process; no broker required.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Dedicated PostGIS test database name (server supplied by CI/Docker).
DATABASES["default"]["TEST"] = {"NAME": "test_rooftop"}

# Storage defaults to the filesystem backend under a throwaway media root.
STORAGE_BACKEND = "filesystem"
