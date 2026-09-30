"""URL routes for the solar app.

Solar results are exposed via the geospatial buildings/results endpoints, so
this app publishes no HTTP routes of its own.
"""

from __future__ import annotations

from django.urls import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
