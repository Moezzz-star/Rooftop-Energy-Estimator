"""URL routes for the audit app.

No public HTTP endpoints are exposed at this time (audit is written by other
services and read via the admin). The module still defines ``urlpatterns`` so
``config/urls.py`` can include it unconditionally.
"""

from __future__ import annotations

from django.urls import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
