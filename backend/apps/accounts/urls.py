"""URL routes for the accounts app (mounted under ``/api/v1/``).

Auth endpoints (login/refresh/register) are public; ``/me/`` and logout require
authentication (code-architecture §4 #1-4).
"""

from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import LogoutView, MeView, RegisterView

# ``TokenObtainPairView`` keys on ``User.USERNAME_FIELD`` (``email``) out of the
# box, so login accepts ``{"email", "password"}`` with no subclass required.
urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="me"),
]
