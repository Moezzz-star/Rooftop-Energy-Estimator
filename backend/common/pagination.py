"""Shared pagination classes.

Page-number pagination with a project-wide default of 25 items per page and a
hard ceiling of 200 (code-architecture §4). Clients may override the page size
via the ``page_size`` query parameter up to the maximum.
"""

from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class StandardPageNumberPagination(PageNumberPagination):
    """Default page-number pagination used by all list endpoints."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
