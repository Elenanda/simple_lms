"""
core/tests/test_course_api.py
API test untuk endpoint Course dan Lesson:
  - GET  /api/courses             (publik)
  - GET  /api/courses/{id}        (publik)
  - POST /api/courses             (instructor only)
  - PATCH /api/courses/{id}       (instructor owner)
  - DELETE /api/courses/{id}      (admin only)
  - GET  /api/courses/{id}/lessons        (publik)
  - POST /api/courses/{id}/lessons        (instructor owner)
  - PATCH /api/courses/{id}/lessons/{id}  (instructor owner)
  - DELETE /api/courses/{id}/lessons/{id} (instructor owner)

Jalankan: python manage.py test core.tests.test_course_api --verbosity=2
"""

import json
import bcrypt
from django.test import TestCase, Client
from core.models import User, Category, Course, Lesson


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _login(client: Client, username: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    return resp.json()["access_token"]


class CourseListAPITest(TestCase):
    """Test GET /api/courses (publik)."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="cl_instr",
            email="cl_instr@test.com",
            password=_hash("pass1234"),
            role="instructor",
        )
        self.category = Category.objects.create(name="Test Cat")
        # Buat beberapa course
        for i in range(5):
            Course.objects.create(
                title=f"Course {i}",
                description=f"Deskripsi course {i} yang cukup panjang.",
                instructor=self.instructor,
                category=self.category,
            )

    def test_list_courses_public(self):
        """List course tidak memerlukan autentikasi."""
        resp = self.client.get("/api/courses")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertIn("results", data)
        self.assertEqual(data["total"], 5)

    def test_list_courses_pagination(self):
        """Pagination bekerja dengan benar."""
        resp = self.client.get("/api/courses?page=1&page_size=3")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 3)

    def test_list_courses_search_filter(self):
        """Filter pencarian berdasarkan judul."""
        Course.objects.create(
            title="Django REST API",
            description="Course khusus Django REST.",
            instructor=self.instructor,
        )
        resp = self.client.get("/api/courses?search=Django")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["title"], "Django REST API")

    def test_list_courses_category_filter(self):
        """Filter berdasarkan category_id."""
        resp = self.client.get(f"/api/courses?category_id={self.category.pk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 5)


class CourseDetailAPITest(TestCase):
    """Test GET /api/courses/{id} (publik)."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="cd_instr",
            email="cd_instr@test.com",
            password=_hash("pass1234"),
            role="instructor",
        )
        self.course = Course.objects.create(
            title="Detail Course",
            description="Deskripsi lengkap untuk test detail course.",
            instructor=self.instructor,
        )

    def test_get_course_detail(self):
        """Detail course bisa diakses tanpa login."""
        resp = self.client.get(f"/api/courses/{self.course.pk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["title"], "Detail Course")
        self.assertEqual(data["instructor"]["username"], "cd_instr")

    def test_get_nonexistent_course(self):
        """Akses course yang tidak ada harus 404."""
        resp = self.client.get("/api/courses/99999")
        self.assertEqual(resp.status_code, 404)


class CourseCreateAPITest(TestCase):
    """Test POST /api/courses (instructor only)."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="create_instr",
            email="create_instr@test.com",
            password=_hash("instr1234"),
            role="instructor",
            is_active=True,
        )
        self.student = User.objects.create(
            username="create_stud",
            email="create_stud@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.category = Category.objects.create(name="Create Cat")
        self.instr_token = _login(self.client, "create_instr", "instr1234")
        self.stud_token = _login(self.client, "create_stud", "stud1234")

    def test_instructor_can_create_course(self):
        """Instructor bisa membuat course baru."""
        resp = self.client.post(
            "/api/courses",
            data=json.dumps({
                "title": "New Course",
                "description": "Deskripsi course baru yang cukup panjang.",
                "category_id": self.category.pk,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr_token}",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "New Course")
        self.assertEqual(data["instructor"]["username"], "create_instr")

    def test_student_cannot_create_course(self):
        """Student tidak bisa membuat course."""
        resp = self.client.post(
            "/api/courses",
            data=json.dumps({
                "title": "Student Course",
                "description": "Student seharusnya tidak bisa membuat course.",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_create_course_requires_auth(self):
        """Membuat course tanpa token harus ditolak."""
        resp = self.client.post(
            "/api/courses",
            data=json.dumps({
                "title": "Unauth Course",
                "description": "Course tanpa autentikasi.",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class CourseUpdateDeleteAPITest(TestCase):
    """Test PATCH dan DELETE /api/courses/{id}."""

    def setUp(self):
        self.client = Client()
        self.instructor1 = User.objects.create(
            username="upd_instr1",
            email="upd1@test.com",
            password=_hash("pass1234"),
            role="instructor",
            is_active=True,
        )
        self.instructor2 = User.objects.create(
            username="upd_instr2",
            email="upd2@test.com",
            password=_hash("pass1234"),
            role="instructor",
            is_active=True,
        )
        self.admin = User.objects.create(
            username="upd_admin",
            email="upd_admin@test.com",
            password=_hash("admin1234"),
            role="admin",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Course to Update",
            description="Deskripsi course yang akan diupdate.",
            instructor=self.instructor1,
        )
        self.instr1_token = _login(self.client, "upd_instr1", "pass1234")
        self.instr2_token = _login(self.client, "upd_instr2", "pass1234")
        self.admin_token  = _login(self.client, "upd_admin", "admin1234")

    def test_owner_can_update_course(self):
        """Instructor pemilik bisa mengupdate course-nya."""
        resp = self.client.patch(
            f"/api/courses/{self.course.pk}",
            data=json.dumps({"title": "Updated Title"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr1_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Updated Title")

    def test_non_owner_cannot_update_course(self):
        """Instructor lain tidak bisa mengupdate course orang lain."""
        resp = self.client.patch(
            f"/api/courses/{self.course.pk}",
            data=json.dumps({"title": "Hacked Title"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr2_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_delete_course(self):
        """Admin bisa menghapus course."""
        resp = self.client.delete(
            f"/api/courses/{self.course.pk}",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

    def test_instructor_cannot_delete_course(self):
        """Instructor tidak bisa menghapus course (hanya admin)."""
        resp = self.client.delete(
            f"/api/courses/{self.course.pk}",
            HTTP_AUTHORIZATION=f"Bearer {self.instr1_token}",
        )
        self.assertEqual(resp.status_code, 403)


class LessonAPITest(TestCase):
    """Test endpoint Lesson CRUD."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="les_instr",
            email="les_instr@test.com",
            password=_hash("les1234"),
            role="instructor",
            is_active=True,
        )
        self.other_instructor = User.objects.create(
            username="les_other",
            email="les_other@test.com",
            password=_hash("les1234"),
            role="instructor",
            is_active=True,
        )
        self.student = User.objects.create(
            username="les_stud",
            email="les_stud@test.com",
            password=_hash("les1234"),
            role="student",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Lesson Test Course",
            description="Deskripsi course untuk test lesson CRUD.",
            instructor=self.instructor,
        )
        self.instr_token = _login(self.client, "les_instr", "les1234")
        self.other_token = _login(self.client, "les_other", "les1234")
        self.stud_token  = _login(self.client, "les_stud", "les1234")

    def test_list_lessons_public(self):
        """List lesson tidak memerlukan autentikasi."""
        Lesson.objects.create(
            course=self.course,
            title="Test Lesson",
            content="Konten panjang untuk lesson test.",
            order=1,
        )
        resp = self.client.get(f"/api/courses/{self.course.pk}/lessons")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_owner_can_create_lesson(self):
        """Instructor pemilik bisa menambahkan lesson."""
        resp = self.client.post(
            f"/api/courses/{self.course.pk}/lessons",
            data=json.dumps({
                "title": "New Lesson",
                "content": "Konten lesson baru yang cukup panjang.",
                "order": 1,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr_token}",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "New Lesson")
        self.assertEqual(data["course_id"], self.course.pk)

    def test_non_owner_cannot_create_lesson(self):
        """Instructor lain tidak bisa menambahkan lesson ke course orang lain."""
        resp = self.client.post(
            f"/api/courses/{self.course.pk}/lessons",
            data=json.dumps({
                "title": "Unauthorized Lesson",
                "content": "Konten yang tidak seharusnya bisa dibuat.",
                "order": 1,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.other_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_create_lesson(self):
        """Student tidak bisa menambahkan lesson."""
        resp = self.client.post(
            f"/api/courses/{self.course.pk}/lessons",
            data=json.dumps({
                "title": "Student Lesson",
                "content": "Student tidak seharusnya bisa membuat lesson.",
                "order": 1,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_update_lesson(self):
        """Instructor pemilik bisa mengupdate lesson."""
        lesson = Lesson.objects.create(
            course=self.course,
            title="Old Title",
            content="Konten lama yang akan diupdate.",
            order=1,
        )
        resp = self.client.patch(
            f"/api/courses/{self.course.pk}/lessons/{lesson.pk}",
            data=json.dumps({"title": "Updated Lesson Title"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Updated Lesson Title")

    def test_owner_can_delete_lesson(self):
        """Instructor pemilik bisa menghapus lesson."""
        lesson = Lesson.objects.create(
            course=self.course,
            title="To Delete",
            content="Konten lesson yang akan dihapus.",
            order=1,
        )
        resp = self.client.delete(
            f"/api/courses/{self.course.pk}/lessons/{lesson.pk}",
            HTTP_AUTHORIZATION=f"Bearer {self.instr_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Lesson.objects.filter(pk=lesson.pk).exists())

    def test_lessons_ordered_by_order_field(self):
        """Lesson dikembalikan terurut berdasarkan field 'order'."""
        Lesson.objects.create(course=self.course, title="L3", content="Konten L3 panjang.", order=3)
        Lesson.objects.create(course=self.course, title="L1", content="Konten L1 panjang.", order=1)
        Lesson.objects.create(course=self.course, title="L2", content="Konten L2 panjang.", order=2)

        resp = self.client.get(f"/api/courses/{self.course.pk}/lessons")
        self.assertEqual(resp.status_code, 200)
        lessons = resp.json()
        self.assertEqual(lessons[0]["title"], "L1")
        self.assertEqual(lessons[1]["title"], "L2")
        self.assertEqual(lessons[2]["title"], "L3")
