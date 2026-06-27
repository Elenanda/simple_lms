"""
api/routers/enrollment_router.py
Endpoints untuk Enrollment & Progress Tracking

POST /api/enrollments                    - Enroll ke course (Student)
GET  /api/enrollments/my-courses         - Daftar course saya (Student)
POST /api/enrollments/{id}/progress      - Tandai lesson selesai (Student)
"""

from datetime import datetime, timezone
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from core.models import Enrollment, Course, Lesson, Progress
from api.auth import jwt_auth, is_student
from api.schemas import (
    EnrollIn, EnrollmentOut, ProgressIn, ProgressOut, MessageOut,
)

router = Router(tags=["Enrollments"])


# ─────────────────────────────────────────────
# POST /enrollments  — Student only
# ─────────────────────────────────────────────
@router.post("", response={201: EnrollmentOut}, auth=jwt_auth)
@is_student
def enroll_course(request: HttpRequest, data: EnrollIn):
    """
    Enroll student ke course.
    **Hanya Student** yang dapat mendaftar.
    Satu student hanya bisa enroll satu course sekali.
    """
    try:
        course = Course.objects.get(pk=data.course_id)
    except Course.DoesNotExist:
        raise HttpError(404, f"Course id={data.course_id} tidak ditemukan.")

    if Enrollment.objects.filter(student=request.auth, course=course).exists():
        raise HttpError(400, "Anda sudah terdaftar di course ini.")

    enrollment = Enrollment.objects.create(
        student=request.auth,
        course=course,
    )
    # Prefetch course relations untuk response
    enrollment = (
        Enrollment.objects
        .select_related("course", "course__category", "course__instructor")
        .get(pk=enrollment.pk)
    )
    return 201, enrollment


# ─────────────────────────────────────────────
# GET /enrollments/my-courses  — Student only
# ─────────────────────────────────────────────
@router.get("/my-courses", response=list[EnrollmentOut], auth=jwt_auth)
@is_student
def my_courses(request: HttpRequest):
    """
    Daftar semua course yang sedang diikuti oleh student yang login.
    """
    enrollments = (
        Enrollment.objects
        .filter(student=request.auth)
        .select_related("course", "course__category", "course__instructor")
        .order_by("-enrolled_at")
    )
    return list(enrollments)


# ─────────────────────────────────────────────
# POST /enrollments/{id}/progress  — Student only
# ─────────────────────────────────────────────
@router.post("/{enrollment_id}/progress", response={201: ProgressOut}, auth=jwt_auth)
@is_student
def mark_progress(request: HttpRequest, enrollment_id: int, data: ProgressIn):
    """
    Tandai sebuah lesson sebagai selesai (atau batalkan) dalam context enrollment tertentu.
    - **lesson_id**: ID lesson yang ingin ditandai
    - **is_completed**: true = selesai, false = belum selesai
    """
    # Validasi enrollment milik student ini
    try:
        enrollment = Enrollment.objects.select_related("course").get(
            pk=enrollment_id, student=request.auth
        )
    except Enrollment.DoesNotExist:
        raise HttpError(404, "Enrollment tidak ditemukan atau bukan milik Anda.")

    # Validasi lesson ada di course tersebut
    try:
        lesson = Lesson.objects.get(pk=data.lesson_id, course=enrollment.course)
    except Lesson.DoesNotExist:
        raise HttpError(404, f"Lesson id={data.lesson_id} tidak ada dalam course ini.")

    # Upsert progress
    progress, created = Progress.objects.get_or_create(
        student=request.auth,
        lesson=lesson,
        defaults={"is_completed": data.is_completed},
    )
    if not created:
        progress.is_completed = data.is_completed
        progress.completed_at = datetime.now(timezone.utc) if data.is_completed else None
        progress.save(update_fields=["is_completed", "completed_at"])
    elif data.is_completed:
        progress.completed_at = datetime.now(timezone.utc)
        progress.save(update_fields=["completed_at"])

    return 201, ProgressOut(
        id=progress.pk,
        lesson_id=progress.lesson_id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
    )
