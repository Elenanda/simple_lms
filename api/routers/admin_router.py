"""
api/routers/admin_router.py
Endpoints khusus Admin untuk manajemen user dan activity logs

GET   /api/admin/users              - List semua user (admin only)
GET   /api/admin/users/{id}         - Detail satu user (admin only)
PATCH /api/admin/users/{id}         - Update role / status user (admin only)
POST  /api/admin/users/{id}/activate    - Aktifkan user (admin only)
POST  /api/admin/users/{id}/deactivate  - Nonaktifkan user (admin only)
GET   /api/admin/activity-logs      - Activity logs dari MongoDB (admin only)
GET   /api/admin/dashboard          - Ringkasan statistik sistem (admin only)
"""

from typing import Optional, List
from django.http import HttpRequest
from ninja import Router, Query
from ninja.errors import HttpError

from core.models import User
from api.auth import jwt_auth, is_admin
from api.schemas import (
    AdminUserOut, AdminUserUpdate, ActivityLogOut, MessageOut,
)

router = Router(tags=["Admin"])


# ─── Helper decorator ─────────────────────────────────────────
def _admin_required(func):
    """Pastikan hanya admin yang bisa akses."""
    import functools
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role != "admin":
            raise HttpError(403, "Akses ditolak. Endpoint ini hanya untuk Admin.")
        return func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# GET /admin/users — Daftar semua user
# ─────────────────────────────────────────────
@router.get("/users", response=List[AdminUserOut], auth=jwt_auth)
@is_admin
def list_users(
    request: HttpRequest,
    role: Optional[str] = Query(default=None, description="Filter by role: admin/instructor/student"),
    is_active: Optional[bool] = Query(default=None, description="Filter by status aktif"),
    search: Optional[str] = Query(default=None, description="Filter by username atau email"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    Daftar semua user dengan filter opsional.
    **Hanya Admin** yang bisa mengakses endpoint ini.
    """
    qs = User.objects.all().order_by("-date_joined")

    if role:
        valid_roles = {"admin", "instructor", "student"}
        if role not in valid_roles:
            raise HttpError(400, f"Role tidak valid. Pilih: {', '.join(valid_roles)}")
        qs = qs.filter(role=role)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))

    offset = (page - 1) * page_size
    users = list(qs[offset: offset + page_size])
    return users


# ─────────────────────────────────────────────
# GET /admin/users/{id} — Detail satu user
# ─────────────────────────────────────────────
@router.get("/users/{user_id}", response=AdminUserOut, auth=jwt_auth)
@is_admin
def get_user(request: HttpRequest, user_id: int):
    """
    Detail informasi satu user.
    **Hanya Admin** yang bisa mengakses.
    """
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise HttpError(404, f"User id={user_id} tidak ditemukan.")


# ─────────────────────────────────────────────
# PATCH /admin/users/{id} — Update role/status user
# ─────────────────────────────────────────────
@router.patch("/users/{user_id}", response=AdminUserOut, auth=jwt_auth)
@is_admin
def update_user(request: HttpRequest, user_id: int, data: AdminUserUpdate):
    """
    Update role dan/atau status aktif seorang user.
    **Hanya Admin** yang bisa mengakses.

    Admin tidak bisa mengubah role/status dirinya sendiri untuk mencegah lockout.
    """
    if user_id == request.auth.pk:
        raise HttpError(400, "Admin tidak dapat mengubah data akun dirinya sendiri.")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise HttpError(404, f"User id={user_id} tidak ditemukan.")

    updated_fields = []
    if data.role is not None:
        user.role = data.role
        updated_fields.append("role")
    if data.is_active is not None:
        user.is_active = data.is_active
        updated_fields.append("is_active")

    if updated_fields:
        user.save(update_fields=updated_fields)

    # Log aktivitas admin
    try:
        from services.mongodb import log_activity
        log_activity(
            user_id=request.auth.pk,
            action="ADMIN_UPDATE_USER",
            resource_type="user",
            resource_id=user_id,
            metadata={"updated_fields": updated_fields},
        )
    except Exception:
        pass

    return user


# ─────────────────────────────────────────────
# POST /admin/users/{id}/deactivate
# ─────────────────────────────────────────────
@router.post("/users/{user_id}/deactivate", response=MessageOut, auth=jwt_auth)
@is_admin
def deactivate_user(request: HttpRequest, user_id: int):
    """
    Nonaktifkan (suspend) sebuah user. User tidak bisa login setelahnya.
    **Hanya Admin** yang bisa mengakses.
    """
    if user_id == request.auth.pk:
        raise HttpError(400, "Admin tidak dapat menonaktifkan akun dirinya sendiri.")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise HttpError(404, f"User id={user_id} tidak ditemukan.")

    if not user.is_active:
        raise HttpError(400, f"User '{user.username}' sudah dalam status nonaktif.")

    user.is_active = False
    user.save(update_fields=["is_active"])

    try:
        from services.mongodb import log_activity
        log_activity(
            user_id=request.auth.pk,
            action="ADMIN_DEACTIVATE_USER",
            resource_type="user",
            resource_id=user_id,
            metadata={"username": user.username},
        )
    except Exception:
        pass

    return MessageOut(message=f"User '{user.username}' berhasil dinonaktifkan.")


# ─────────────────────────────────────────────
# POST /admin/users/{id}/activate
# ─────────────────────────────────────────────
@router.post("/users/{user_id}/activate", response=MessageOut, auth=jwt_auth)
@is_admin
def activate_user(request: HttpRequest, user_id: int):
    """
    Aktifkan kembali sebuah user yang sebelumnya dinonaktifkan.
    **Hanya Admin** yang bisa mengakses.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise HttpError(404, f"User id={user_id} tidak ditemukan.")

    if user.is_active:
        raise HttpError(400, f"User '{user.username}' sudah dalam status aktif.")

    user.is_active = True
    user.save(update_fields=["is_active"])

    try:
        from services.mongodb import log_activity
        log_activity(
            user_id=request.auth.pk,
            action="ADMIN_ACTIVATE_USER",
            resource_type="user",
            resource_id=user_id,
            metadata={"username": user.username},
        )
    except Exception:
        pass

    return MessageOut(message=f"User '{user.username}' berhasil diaktifkan kembali.")


# ─────────────────────────────────────────────
# GET /admin/activity-logs — MongoDB activity logs
# ─────────────────────────────────────────────
@router.get("/activity-logs", auth=jwt_auth)
@is_admin
def get_activity_logs(
    request: HttpRequest,
    limit: int = Query(default=50, ge=1, le=200, description="Jumlah log yang ditampilkan"),
    user_id: Optional[int] = Query(default=None, description="Filter by user_id"),
    action: Optional[str] = Query(default=None, description="Filter by action (LOGIN, ENROLL, dll)"),
):
    """
    Ambil activity log terbaru dari MongoDB.
    Bisa difilter per user atau per jenis action.
    **Hanya Admin** yang bisa mengakses.
    """
    try:
        from services.mongodb import get_db
        db = get_db()
        if db is None:
            return []

        query = {}
        if user_id is not None:
            query["user_id"] = user_id
        if action:
            query["action"] = action.upper()

        logs = list(
            db.activity_logs
            .find(query, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )

        # Konversi datetime ke string agar bisa di-serialize
        for log in logs:
            if "timestamp" in log and hasattr(log["timestamp"], "isoformat"):
                log["timestamp"] = log["timestamp"].isoformat()

        return logs
    except Exception as exc:
        raise HttpError(503, f"MongoDB tidak tersedia: {exc}")


# ─────────────────────────────────────────────
# GET /admin/dashboard — Statistik sistem
# ─────────────────────────────────────────────
@router.get("/dashboard", auth=jwt_auth)
@is_admin
def admin_dashboard(request: HttpRequest):
    """
    Ringkasan statistik sistem: jumlah user, course, enrollment, progress.
    **Hanya Admin** yang bisa mengakses.
    """
    from core.models import Course, Enrollment, Progress
    from django.db.models import Count

    user_stats = User.objects.values("role").annotate(count=Count("id"))
    role_counts = {item["role"]: item["count"] for item in user_stats}

    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()
    total_progress = Progress.objects.filter(is_completed=True).count()

    return {
        "users": {
            "total": User.objects.count(),
            "admin": role_counts.get("admin", 0),
            "instructor": role_counts.get("instructor", 0),
            "student": role_counts.get("student", 0),
            "active": User.objects.filter(is_active=True).count(),
            "inactive": User.objects.filter(is_active=False).count(),
        },
        "courses": {
            "total": total_courses,
        },
        "enrollments": {
            "total": total_enrollments,
        },
        "progress": {
            "completed_lessons": total_progress,
        },
    }
