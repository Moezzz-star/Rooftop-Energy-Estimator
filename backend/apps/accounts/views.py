"""HTTP views for the accounts app.

Views are thin: they validate input via serializers, delegate to
:class:`apps.accounts.services.AccountService`, and shape the response. No
business logic lives here (code-architecture §6).
"""

from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.errors import ValidationError
from common.logging import get_logger

from .models import User
from .serializers import LogoutSerializer, RegisterSerializer, UserSerializer
from .services import AccountService

logger = get_logger("accounts.views")


def _tokens_for(user: Any) -> dict[str, str]:
    """Return a fresh access/refresh token pair for ``user``."""
    refresh = RefreshToken.for_user(user)
    # simplejwt attaches ``access_token`` dynamically; not present in stubs.
    access = str(refresh.access_token)  # type: ignore[attr-defined]
    return {"refresh": str(refresh), "access": access}


class RegisterView(APIView):
    """POST ``/auth/register/`` — create a user and return it with JWT tokens."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    serializer_class = RegisterSerializer

    def post(self, request: Request) -> Response:
        """Register a new account and issue an initial token pair."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = AccountService()
        user = service.register(email=data["email"], password=data["password"])

        body = {"user": UserSerializer(user).data, "tokens": _tokens_for(user)}
        return Response(body, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """POST ``/auth/logout/`` — invalidate the caller's refresh token.

    The project does not enable ``simplejwt``'s ``token_blacklist`` app (it is
    not in ``INSTALLED_APPS`` and this app may not modify config). Logout therefore
    validates the supplied refresh token and best-effort blacklists it when the
    blacklist app is available, otherwise it is a stateless ``205 Reset Content``
    (the client discards its tokens). Documented per the task brief.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request: Request) -> Response:
        """Validate and (best-effort) blacklist the provided refresh token."""
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise ValidationError("Invalid or expired refresh token.") from exc

        try:
            token.blacklist()
            logger.info("Refresh token blacklisted on logout")
        except AttributeError:
            # token_blacklist app not installed: stateless logout.
            logger.info("Stateless logout (token blacklist app not enabled)")

        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """GET ``/me/`` — return the currently authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request: Request) -> Response:
        """Serialize and return ``request.user``."""
        return Response(UserSerializer(cast(User, request.user)).data)
