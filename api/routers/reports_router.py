"""
api/routers/reports_router.py
Endpoints untuk Async Report Generation

POST /api/reports/courses/{id}   - Request CSV export (async) → return task_id
GET  /api/reports/tasks/{id}     - Cek status task (PENDING/STARTED/SUCCESS/FAILURE)
GET  /api/reports/analytics/{id} - Aggregasi analytics course dari MongoDB
"""

import functools
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from api.auth import jwt_auth
from api.schemas import TaskStatusOut, CourseAnalyticsOut, MessageOut

router = Router(tags=["Reports & Analytics"])


# ─── Local role decorator (admin atau instructor) ────────────
def _require_admin_or_instructor(func):
    """Decorator: izinkan admin atau instructor mengakses endpoint."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role not in ('admin', 'instructor'):
            raise HttpError(403, "Akses ditolak. Diperlukan role: admin atau instructor.")
        return func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# POST /reports/courses/{id} — Async CSV export
# ─────────────────────────────────────────────
@router.post("/courses/{course_id}", response={202: TaskStatusOut}, auth=jwt_auth)
@_require_admin_or_instructor
def request_course_report(request: HttpRequest, course_id: int):
    """
    Request pembuatan CSV report untuk sebuah course secara **asynchronous**.

    Returns `task_id` yang bisa digunakan untuk cek status di
    `GET /api/reports/tasks/{task_id}`.

    **Akses**: Admin atau Instructor pemilik course.
    """
    from core.models import Course
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    user = request.auth
    if user.role == 'instructor' and course.instructor_id != user.pk:
        raise HttpError(403, "Anda hanya bisa export course milik sendiri.")

    try:
        from tasks.report_tasks import export_course_report
        task = export_course_report.delay(course_id, user.pk)
        return 202, TaskStatusOut(
            task_id=task.id,
            status="PENDING",
            result=None,
        )
    except Exception as exc:
        raise HttpError(503, f"Celery tidak tersedia: {exc}")


# ─────────────────────────────────────────────
# GET /reports/tasks/{task_id} — Status check
# ─────────────────────────────────────────────
@router.get("/tasks/{task_id}", response=TaskStatusOut, auth=jwt_auth)
def get_task_status(request: HttpRequest, task_id: str):
    """
    Cek status Celery task berdasarkan `task_id`.

    Status kemungkinan:
    - `PENDING`  → Antri, belum diproses
    - `STARTED`  → Sedang diproses oleh worker
    - `SUCCESS`  → Selesai, lihat `result` untuk detail
    - `FAILURE`  → Gagal, lihat `result` untuk error message
    """
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        return TaskStatusOut(
            task_id=task_id,
            status=result.status,
            result=result.result if result.ready() else None,
        )
    except Exception as exc:
        raise HttpError(503, f"Tidak dapat mengambil status task: {exc}")


# ─────────────────────────────────────────────
# GET /reports/analytics/{course_id} — MongoDB aggregation
# ─────────────────────────────────────────────
@router.get("/analytics/{course_id}", response=CourseAnalyticsOut, auth=jwt_auth)
@_require_admin_or_instructor
def get_course_analytics(request: HttpRequest, course_id: int):
    """
    Ambil learning analytics dari MongoDB untuk sebuah course.

    Mengembalikan agregasi: jumlah event per tipe (ENROLL, LESSON_COMPLETE, COURSE_COMPLETE).
    """
    from core.models import Course
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    if request.auth.role == 'instructor' and course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda hanya bisa melihat analytics course milik sendiri.")

    from services.mongodb import get_course_activity_summary
    summary = get_course_activity_summary(course_id)

    return CourseAnalyticsOut(
        course_id=course_id,
        course_title=course.title,
        analytics=summary,
    )
