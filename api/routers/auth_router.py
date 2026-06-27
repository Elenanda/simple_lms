"""
api/routers/auth_router.py
Endpoints untuk Authentication & User Profile

POST /api/auth/register   - Daftar akun baru
POST /api/auth/login      - Login → JWT tokens
POST /api/auth/refresh    - Refresh access token
GET  /api/auth/me         - Profil saya
PUT  /api/auth/me         - Update profil
"""

import bcrypt
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from core.models import User
from api.auth import (
    jwt_auth,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from api.schemas import (
    RegisterIn, LoginIn, TokenOut, RefreshIn, AccessTokenOut,
    UserOut, UpdateProfileIn, MessageOut,
)

router = Router(tags=["Authentication"])


# ─────────────────────────────────────────────
# POST /register
# ─────────────────────────────────────────────
@router.post("/register", response={201: UserOut, 400: dict}, auth=None)
def register(request: HttpRequest, data: RegisterIn):
    """
    Daftarkan user baru.
    - Role: admin | instructor | student (default: student)
    - Password di-hash menggunakan bcrypt
    """
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan.")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah terdaftar.")

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=hashed,   # disimpan langsung; login kita validasi manual
        role=data.role,
    )
    return 201, user


# ─────────────────────────────────────────────
# POST /login
# ─────────────────────────────────────────────
@router.post("/login", response={200: TokenOut, 401: dict}, auth=None)
def login(request: HttpRequest, data: LoginIn):
    """
    Login dan dapatkan JWT access + refresh token.
    Password divalidasi menggunakan bcrypt.
    """
    try:
        user = User.objects.get(username=data.username)
    except User.DoesNotExist:
        raise HttpError(401, "Username atau password salah.")

    # Validasi password bcrypt
    if not bcrypt.checkpw(data.password.encode(), user.password.encode()):
        # Fallback: Django native check (untuk user yang dibuat via createsuperuser)
        if not user.check_password(data.password):
            raise HttpError(401, "Username atau password salah.")

    if not user.is_active:
        raise HttpError(401, "Akun tidak aktif.")

    return 200, TokenOut(
        access_token=create_access_token(user.pk),
        refresh_token=create_refresh_token(user.pk),
    )


# ─────────────────────────────────────────────
# POST /refresh
# ─────────────────────────────────────────────
@router.post("/refresh", response={200: AccessTokenOut, 401: dict}, auth=None)
def refresh_token(request: HttpRequest, data: RefreshIn):
    """
    Tukarkan refresh token yang valid menjadi access token baru.
    """
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HttpError(401, "Refresh token tidak valid atau sudah kadaluarsa.")
    try:
        user = User.objects.get(pk=int(payload["sub"]))
    except (User.DoesNotExist, ValueError):
        raise HttpError(401, "User tidak ditemukan.")

    return 200, AccessTokenOut(access_token=create_access_token(user.pk))


# ─────────────────────────────────────────────
# GET /me
# ─────────────────────────────────────────────
@router.get("/me", response=UserOut, auth=jwt_auth)
def get_me(request: HttpRequest):
    """Ambil profil user yang sedang login."""
    return request.auth


# ─────────────────────────────────────────────
# PUT /me
# ─────────────────────────────────────────────
@router.put("/me", response=UserOut, auth=jwt_auth)
def update_me(request: HttpRequest, data: UpdateProfileIn):
    """Update profil user (first_name, last_name, email)."""
    user: User = request.auth
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.email is not None:
        if User.objects.exclude(pk=user.pk).filter(email=data.email).exists():
            raise HttpError(400, "Email sudah digunakan oleh akun lain.")
        user.email = data.email
    user.save(update_fields=["first_name", "last_name", "email"])
    return user
