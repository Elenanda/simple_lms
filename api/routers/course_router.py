"""
api/routers/course_router.py
Endpoints untuk manajemen Course & Lesson — dengan Redis Caching

GET  /api/courses                           - List courses (publik, pagination + filter) [CACHED 5 min]
GET  /api/courses/{id}                      - Detail course (publik)                      [CACHED 10 min]
POST /api/courses                           - Buat course (Instructor only)               [Invalidate cache]
PATCH /api/courses/{id}                     - Update course (Owner only)                  [Invalidate cache]
DELETE /api/courses/{id}                    - Hapus course (Admin only)                   [Invalidate cache]

GET  /api/courses/{id}/lessons              - List lesson dalam course (publik)
POST /api/courses/{id}/lessons              - Tambah lesson (Instructor owner)
PATCH /api/courses/{id}/lessons/{lesson_id} - Update lesson (Instructor owner)
DELETE /api/courses/{id}/lessons/{lesson_id}- Hapus lesson (Instructor owner)

Caching Strategy:
  - Cache miss  → query DB → serialize → simpan ke Redis
  - Cache hit   → return langsung dari Redis (tanpa DB query)
  - Invalidasi  → hapus key terkait pada write operations
"""

from typing import Optional, List
from django.http import HttpRequest
from django.db.models import Count
from ninja import Router, Query
from ninja.errors import HttpError

from core.models import Course, Category, Lesson
from api.auth import jwt_auth, is_instructor, is_admin
from api.schemas import (
    CourseIn, CourseUpdateIn, CourseOut, CourseListOut,
    PaginatedCourseOut, MessageOut,
    LessonIn, LessonOut, LessonUpdateIn,
)
from services import cache as course_cache
from services.mongodb import log_activity

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
    Response di-cache di Redis selama **5 menit**.
    Cache otomatis di-invalidasi saat ada course baru / update / delete.
    """
    # ── Cache Check ──
    cached = course_cache.get_course_list(page, page_size, search, category_id, instructor_id)
    if cached is not None:
        return PaginatedCourseOut.model_validate(cached)

    # ── DB Query ──
    qs = Course.objects.select_related("category", "instructor").all()

    if search:
        qs = qs.filter(title__icontains=search)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if instructor_id:
        qs = qs.filter(instructor_id=instructor_id)

    qs    = qs.order_by("-created_at")
    total = qs.count()
    offset = (page - 1) * page_size
    courses = list(qs[offset: offset + page_size])

    result = PaginatedCourseOut(
        total=total, page=page, page_size=page_size,
        results=courses,
    )

    # ── Store to Cache ──
    course_cache.set_course_list(
        page, page_size, search, category_id, instructor_id,
        result.model_dump(mode='json'),
    )

    return result


# ─────────────────────────────────────────────
# GET /courses/{id}  — Publik
# ─────────────────────────────────────────────
@router.get("/{course_id}", response=CourseOut, auth=None)
def get_course(request: HttpRequest, course_id: int):
    """
    Detail satu course lengkap dengan jumlah enrollment.
    Response di-cache di Redis selama **10 menit**.
    """
    # ── Cache Check ──
    cached = course_cache.get_course_detail(course_id)
    if cached is not None:
        return CourseOut.model_validate(cached)

    # ── DB Query ──
    try:
        course = (
            Course.objects
            .select_related("category", "instructor")
            .annotate(enrollment_count=Count("enrollments"))
            .get(pk=course_id)
        )
    except Course.DoesNotExist:
        raise HttpError(404, f"Course dengan id={course_id} tidak ditemukan.")

    # ── Store to Cache ──
    course_cache.set_course_detail(course_id, CourseOut.from_orm(course).model_dump(mode='json'))

    return course


# ─────────────────────────────────────────────
# POST /courses  — Instructor only
# ─────────────────────────────────────────────
@router.post("", response={201: CourseOut}, auth=jwt_auth)
@is_instructor
def create_course(request: HttpRequest, data: CourseIn):
    """
    Buat course baru. **Hanya Instructor** yang bisa mengakses endpoint ini.
    Cache list courses akan di-invalidasi otomatis.
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
    course = Course.objects.select_related("category", "instructor").get(pk=course.pk)

    # ── Invalidasi cache list ──
    course_cache.invalidate_all_course_lists()

    # ── Activity Log (MongoDB) ──
    log_activity(
        user_id=request.auth.pk,
        action="CREATE_COURSE",
        resource_type="course",
        resource_id=course.pk,
        metadata={"title": course.title},
    )

    return 201, course


# ─────────────────────────────────────────────
# PATCH /courses/{id}  — Owner (instructor) only
# ─────────────────────────────────────────────
@router.patch("/{course_id}", response=CourseOut, auth=jwt_auth)
@is_instructor
def update_course(request: HttpRequest, course_id: int, data: CourseUpdateIn):
    """
    Update sebagian data course. **Hanya instructor pemilik** course ini.
    Cache detail + list akan di-invalidasi.
    """
    try:
        course = Course.objects.select_related("category", "instructor").get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

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

    # ── Invalidasi cache ──
    course_cache.invalidate_course(course_id)

    # ── Activity Log ──
    log_activity(
        user_id=request.auth.pk,
        action="UPDATE_COURSE",
        resource_type="course",
        resource_id=course_id,
        metadata={"updated_fields": updated_fields},
    )

    return course


# ─────────────────────────────────────────────
# DELETE /courses/{id}  — Admin only
# ─────────────────────────────────────────────
@router.delete("/{course_id}", response=MessageOut, auth=jwt_auth)
@is_admin
def delete_course(request: HttpRequest, course_id: int):
    """
    Hapus course. **Hanya Admin** yang bisa menghapus course.
    Cache detail + list akan di-invalidasi.
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    title = course.title
    course.delete()

    # ── Invalidasi cache ──
    course_cache.invalidate_course(course_id)

    # ── Activity Log ──
    log_activity(
        user_id=request.auth.pk,
        action="DELETE_COURSE",
        resource_type="course",
        resource_id=course_id,
        metadata={"title": title},
    )

    return MessageOut(message=f"Course '{title}' berhasil dihapus.")


# ─────────────────────────────────────────────
# GET /courses/{id}/lessons — Publik
# ─────────────────────────────────────────────
@router.get("/{course_id}/lessons", response=List[LessonOut], auth=None)
def list_lessons(request: HttpRequest, course_id: int):
    """
    Daftar semua lesson dalam sebuah course, diurutkan berdasarkan `order`.
    Endpoint ini **publik** (tidak perlu login).
    """
    try:
        Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    lessons = Lesson.objects.filter(course_id=course_id).order_by("order", "id")
    return list(lessons)


# ─────────────────────────────────────────────
# POST /courses/{id}/lessons — Instructor (owner) only
# ─────────────────────────────────────────────
@router.post("/{course_id}/lessons", response={201: LessonOut}, auth=jwt_auth)
@is_instructor
def create_lesson(request: HttpRequest, course_id: int, data: LessonIn):
    """
    Tambahkan lesson baru ke dalam course.
    **Hanya instructor pemilik** course yang dapat menambahkan lesson.
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    if course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda bukan pemilik course ini.")

    lesson = Lesson.objects.create(
        course=course,
        title=data.title,
        content=data.content,
        order=data.order,
    )

    log_activity(
        user_id=request.auth.pk,
        action="CREATE_LESSON",
        resource_type="lesson",
        resource_id=lesson.pk,
        metadata={"course_id": course_id, "title": lesson.title},
    )

    return 201, lesson


# ─────────────────────────────────────────────
# PATCH /courses/{id}/lessons/{lesson_id} — Instructor (owner) only
# ─────────────────────────────────────────────
@router.patch("/{course_id}/lessons/{lesson_id}", response=LessonOut, auth=jwt_auth)
@is_instructor
def update_lesson(request: HttpRequest, course_id: int, lesson_id: int, data: LessonUpdateIn):
    """
    Update lesson (judul, konten, urutan).
    **Hanya instructor pemilik** course ini.
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    if course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda bukan pemilik course ini.")

    try:
        lesson = Lesson.objects.get(pk=lesson_id, course=course)
    except Lesson.DoesNotExist:
        raise HttpError(404, f"Lesson id={lesson_id} tidak ditemukan di course ini.")

    updated_fields = []
    if data.title is not None:
        lesson.title = data.title
        updated_fields.append("title")
    if data.content is not None:
        lesson.content = data.content
        updated_fields.append("content")
    if data.order is not None:
        lesson.order = data.order
        updated_fields.append("order")

    if updated_fields:
        lesson.save(update_fields=updated_fields)

    log_activity(
        user_id=request.auth.pk,
        action="UPDATE_LESSON",
        resource_type="lesson",
        resource_id=lesson_id,
        metadata={"course_id": course_id, "updated_fields": updated_fields},
    )

    return lesson


# ─────────────────────────────────────────────
# DELETE /courses/{id}/lessons/{lesson_id} — Instructor (owner) only
# ─────────────────────────────────────────────
@router.delete("/{course_id}/lessons/{lesson_id}", response=MessageOut, auth=jwt_auth)
@is_instructor
def delete_lesson(request: HttpRequest, course_id: int, lesson_id: int):
    """
    Hapus lesson dari course.
    **Hanya instructor pemilik** course ini.
    Progress terkait lesson ini akan ikut terhapus (cascade).
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan.")

    if course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda bukan pemilik course ini.")

    try:
        lesson = Lesson.objects.get(pk=lesson_id, course=course)
    except Lesson.DoesNotExist:
        raise HttpError(404, f"Lesson id={lesson_id} tidak ditemukan di course ini.")

    title = lesson.title
    lesson.delete()

    log_activity(
        user_id=request.auth.pk,
        action="DELETE_LESSON",
        resource_type="lesson",
        resource_id=lesson_id,
        metadata={"course_id": course_id, "title": title},
    )

    return MessageOut(message=f"Lesson '{title}' berhasil dihapus.")
