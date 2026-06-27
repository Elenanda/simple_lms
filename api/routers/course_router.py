"""
api/routers/course_router.py
Endpoints untuk manajemen Course

GET  /api/courses             - List courses (publik, pagination + filter)
GET  /api/courses/{id}        - Detail course (publik)
POST /api/courses             - Buat course (Instructor only)
PATCH /api/courses/{id}       - Update course (Owner only)
DELETE /api/courses/{id}      - Hapus course (Admin only)
"""

from typing import Optional
from django.http import HttpRequest
from django.db.models import Count
from ninja import Router, Query
from ninja.errors import HttpError

from core.models import Course, Category
from api.auth import jwt_auth, is_instructor, is_admin
from api.schemas import (
    CourseIn, CourseUpdateIn, CourseOut, CourseListOut,
    PaginatedCourseOut, MessageOut,
)

router = Router(tags=["Courses"])


# ─────────────────────────────────────────────
# GET /courses  — Publik, pagination + filter
# ─────────────────────────────────────────────
@router.get("", response=PaginatedCourseOut, auth=None)
def list_courses(
    request: HttpRequest,
    page: int = Query(default=1, ge=1, description="Nomor halaman (mulai 1)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    search: Optional[str] = Query(default=None, description="Filter judul course"),
    category_id: Optional[int] = Query(default=None, description="Filter by category"),
    instructor_id: Optional[int] = Query(default=None, description="Filter by instructor"),
):
    """
    Ambil daftar course dengan pagination dan opsional filter.
    - **search**: cari berdasarkan kata dalam judul
    - **category_id**: filter by kategori
    - **instructor_id**: filter by instruktur
    """
    qs = Course.objects.select_related("category", "instructor").all()

    if search:
        qs = qs.filter(title__icontains=search)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if instructor_id:
        qs = qs.filter(instructor_id=instructor_id)

    qs = qs.order_by("-created_at")
    total = qs.count()

    offset = (page - 1) * page_size
    courses = qs[offset: offset + page_size]

    return PaginatedCourseOut(
        total=total,
        page=page,
        page_size=page_size,
        results=list(courses),
    )


# ─────────────────────────────────────────────
# GET /courses/{id}  — Publik
# ─────────────────────────────────────────────
@router.get("/{course_id}", response=CourseOut, auth=None)
def get_course(request: HttpRequest, course_id: int):
    """
    Detail satu course lengkap dengan jumlah enrollment.
    """
    try:
        course = (
            Course.objects
            .select_related("category", "instructor")
            .annotate(enrollment_count=Count("enrollments"))
            .get(pk=course_id)
        )
    except Course.DoesNotExist:
        raise HttpError(404, f"Course dengan id={course_id} tidak ditemukan.")

    return course


# ─────────────────────────────────────────────
# POST /courses  — Instructor only
# ─────────────────────────────────────────────
@router.post("", response={201: CourseOut}, auth=jwt_auth)
@is_instructor
def create_course(request: HttpRequest, data: CourseIn):
    """
    Buat course baru. **Hanya Instructor** yang bisa mengakses endpoint ini.
    Instructor otomatis menjadi owner dari course yang dibuat.
    """
    category = None
    if data.category_id:
        try:
            category = Category.objects.get(pk=data.category_id)
        except Category.DoesNotExist:
            raise HttpError(400, f"Category id={data.category_id} tidak ditemukan.")

    course = Course.objects.create(
        title=data.title,
        description=data.description,
        category=category,
        instructor=request.auth,
    )
    # Re-fetch dengan relasi untuk response
    course = Course.objects.select_related("category", "instructor").get(pk=course.pk)
    return 201, course


# ─────────────────────────────────────────────
# PATCH /courses/{id}  — Owner (instructor) only
# ─────────────────────────────────────────────
@router.patch("/{course_id}", response=CourseOut, auth=jwt_auth)
@is_instructor
def update_course(request: HttpRequest, course_id: int, data: CourseUpdateIn):
    """
    Update sebagian data course. **Hanya instructor pemilik** course ini.
    """
    try:
        course = Course.objects.select_related("category", "instructor").get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    # Ownership check
    if course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda bukan pemilik course ini.")

    updated_fields = []
    if data.title is not None:
        course.title = data.title
        updated_fields.append("title")
    if data.description is not None:
        course.description = data.description
        updated_fields.append("description")
    if data.category_id is not None:
        try:
            course.category = Category.objects.get(pk=data.category_id)
            updated_fields.append("category")
        except Category.DoesNotExist:
            raise HttpError(400, f"Category id={data.category_id} tidak ditemukan.")

    if updated_fields:
        course.save(update_fields=updated_fields)

    return course


# ─────────────────────────────────────────────
# DELETE /courses/{id}  — Admin only
# ─────────────────────────────────────────────
@router.delete("/{course_id}", response=MessageOut, auth=jwt_auth)
@is_admin
def delete_course(request: HttpRequest, course_id: int):
    """
    Hapus course. **Hanya Admin** yang bisa menghapus course.
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    title = course.title
    course.delete()
    return MessageOut(message=f"Course '{title}' berhasil dihapus.")
