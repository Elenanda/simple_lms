"""
api/schemas.py
Pydantic Schemas untuk seluruh endpoint REST API
Menggunakan Pydantic v2 (bundled dengan django-ninja 1.x)
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Auth Schemas
# ─────────────────────────────────────────────
class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=150, examples=["john_doe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, examples=["securePass123"])
    role: str = Field(default="student", examples=["student"])

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        allowed = {"admin", "instructor", "student"}
        if v not in allowed:
            raise ValueError(f"Role harus salah satu dari: {', '.join(allowed)}")
        return v


class LoginIn(BaseModel):
    username: str = Field(..., examples=["john_doe"])
    password: str = Field(..., examples=["securePass123"])


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    first_name: str
    last_name: str
    date_joined: datetime

    model_config = {"from_attributes": True}


class UpdateProfileIn(BaseModel):
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    email: Optional[EmailStr] = None


# ─────────────────────────────────────────────
# Category Schemas
# ─────────────────────────────────────────────
class CategoryOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Course Schemas
# ─────────────────────────────────────────────
class CourseOut(BaseModel):
    id: int
    title: str
    description: str
    category: Optional[CategoryOut]
    instructor: UserOut
    created_at: datetime
    enrollment_count: Optional[int] = None

    model_config = {"from_attributes": True}


class CourseListOut(BaseModel):
    id: int
    title: str
    description: str
    category: Optional[CategoryOut]
    instructor: UserOut
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, examples=["Intro to Python"])
    description: str = Field(..., min_length=10, examples=["Belajar Python dari dasar..."])
    category_id: Optional[int] = Field(None, examples=[1])


class CourseUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    category_id: Optional[int] = None


# ─────────────────────────────────────────────
# Pagination Schema
# ─────────────────────────────────────────────
class PaginatedCourseOut(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[CourseListOut]


# ─────────────────────────────────────────────
# Enrollment Schemas
# ─────────────────────────────────────────────
class EnrollIn(BaseModel):
    course_id: int = Field(..., examples=[1])


class EnrollmentOut(BaseModel):
    id: int
    course: CourseListOut
    enrolled_at: datetime

    model_config = {"from_attributes": True}


class ProgressIn(BaseModel):
    lesson_id: int = Field(..., examples=[1])
    is_completed: bool = Field(default=True)


class ProgressOut(BaseModel):
    id: int
    lesson_id: int
    is_completed: bool
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Lesson Schemas
# ─────────────────────────────────────────────
class LessonOut(BaseModel):
    id: int
    title: str
    content: str
    order: int
    course_id: int

    model_config = {"from_attributes": True}


class LessonIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, examples=["Pengenalan Python"])
    content: str = Field(..., min_length=10, examples=["Pada lesson ini kita akan belajar..."])
    order: int = Field(default=0, ge=0, examples=[1])


class LessonUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    order: Optional[int] = Field(None, ge=0)


# ─────────────────────────────────────────────
# Generic Schemas
# ─────────────────────────────────────────────
class MessageOut(BaseModel):
    message: str


class ErrorOut(BaseModel):
    detail: str


# ─────────────────────────────────────────────
# Reports & Analytics Schemas
# ─────────────────────────────────────────────
class TaskStatusOut(BaseModel):
    """Response untuk status Celery task."""
    task_id: str
    status: str   # PENDING | STARTED | SUCCESS | FAILURE
    result: Optional[Any] = None


class CourseAnalyticsOut(BaseModel):
    """Response untuk aggregasi learning analytics dari MongoDB."""
    course_id: int
    course_title: str
    analytics: dict  # {event_type: {count, students}}


# ─────────────────────────────────────────────
# Admin Schemas
# ─────────────────────────────────────────────
class AdminUserOut(BaseModel):
    """User detail untuk admin view (termasuk is_active)."""
    id: int
    username: str
    email: str
    role: str
    first_name: str
    last_name: str
    is_active: bool
    date_joined: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    """Payload untuk admin update user (role dan/atau is_active)."""
    role: Optional[str] = Field(None, examples=["student"])
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"admin", "instructor", "student"}
        if v not in allowed:
            raise ValueError(f"Role harus salah satu dari: {', '.join(allowed)}")
        return v


class ActivityLogOut(BaseModel):
    """Satu entry activity log dari MongoDB."""
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    metadata: dict = {}
    timestamp: datetime
