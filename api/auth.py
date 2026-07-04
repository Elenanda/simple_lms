"""
api/auth.py
JWT Authentication & Authorization Utilities
- Token generation (access + refresh) — dengan 'jti' untuk blacklist
- Bearer token extraction & validasi
- Role-based decorators: @is_admin, @is_instructor, @is_student
"""

import jwt
import uuid
import functools
from datetime import datetime, timedelta, timezone
from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer

from core.models import User


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES = 60        # 1 jam
REFRESH_TOKEN_EXPIRE_DAYS = 7           # 7 hari
ALGORITHM = "HS256"


# ─────────────────────────────────────────────
# Token Helpers
# ─────────────────────────────────────────────
def create_access_token(user_id: int) -> str:
    """Buat JWT access token dengan expiry 1 jam + jti unik."""
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Buat JWT refresh token dengan expiry 7 hari + jti unik."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode dan validasi JWT token. Return payload dict atau None jika invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(token: str) -> Optional[User]:
    """Ambil User object dari JWT token string."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        return User.objects.get(pk=int(payload["sub"]))
    except (User.DoesNotExist, ValueError, KeyError):
        return None


# ─────────────────────────────────────────────
# Django Ninja Auth Backend
# ─────────────────────────────────────────────
class JWTAuth(HttpBearer):
    """
    Django Ninja authentication backend.
    Validasi header: Authorization: Bearer <token>
    Juga mengecek token blacklist (logout).
    """
    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None

        # Cek blacklist (token sudah di-logout)
        jti = payload.get("jti")
        if jti:
            try:
                from services.cache import is_token_blacklisted
                if is_token_blacklisted(jti):
                    return None  # Token sudah di-revoke
            except Exception:
                pass  # Graceful degrade jika Redis tidak tersedia

        try:
            user = User.objects.get(pk=int(payload["sub"]))
        except (User.DoesNotExist, ValueError, KeyError):
            return None

        if user and user.is_active:
            return user
        return None


jwt_auth = JWTAuth()


# ─────────────────────────────────────────────
# Role-Based Authorization Decorators
# ─────────────────────────────────────────────
def _role_required(*roles):
    """
    Internal factory untuk membuat role decorator.
    Penggunaan: @is_admin, @is_instructor, @is_student
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # request.auth adalah user yang sudah di-set oleh JWTAuth
            user: User = request.auth
            if not user or user.role not in roles:
                from ninja.errors import HttpError
                raise HttpError(403, f"Akses ditolak. Diperlukan role: {', '.join(roles)}")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# Public role decorators
is_admin       = _role_required("admin")
is_instructor  = _role_required("instructor")
is_student     = _role_required("student")
is_admin_or_instructor = _role_required("admin", "instructor")
