"""
core/tests/test_enrollment_api.py
API test untuk endpoint Enrollment & Progress:
  - POST /api/enrollments                   (student only)
  - GET  /api/enrollments/my-courses        (student only)
  - POST /api/enrollments/{id}/progress     (student only)
  - Permission: instructor & admin tidak bisa enroll/progress

Jalankan: python manage.py test core.tests.test_enrollment_api --verbosity=2
"""

import json
import bcrypt
from django.test import TestCase, Client
from core.models import User, Category, Course, Lesson, Enrollment, Progress


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _login(client: Client, username: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    return resp.json()["access_token"]


class EnrollmentAPITest(TestCase):
    """Test POST /api/enrollments (student only)."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="enr_instr",
            email="enr_instr@test.com",
            password=_hash("pass1234"),
            role="instructor",
            is_active=True,
        )
        self.student = User.objects.create(
            username="enr_stud",
            email="enr_stud@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.other_student = User.objects.create(
            username="enr_stud2",
            email="enr_stud2@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Enroll Test Course",
            description="Deskripsi course untuk test enrollment.",
            instructor=self.instructor,
        )
        self.stud_token  = _login(self.client, "enr_stud", "stud1234")
        self.instr_token = _login(self.client, "enr_instr", "pass1234")

    def test_student_can_enroll(self):
        """Student bisa enroll ke sebuah course."""
        resp = self.client.post(
            "/api/enrollments",
            data=json.dumps({"course_id": self.course.pk}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["course"]["id"], self.course.pk)

    def test_instructor_cannot_enroll(self):
        """Instructor tidak bisa enroll ke course (bukan role student)."""
        resp = self.client.post(
            "/api/enrollments",
            data=json.dumps({"course_id": self.course.pk}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.instr_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_cannot_enroll_twice(self):
        """Student tidak bisa enroll ke course yang sama dua kali."""
        Enrollment.objects.create(student=self.student, course=self.course)
        resp = self.client.post(
            "/api/enrollments",
            data=json.dumps({"course_id": self.course.pk}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 400)

    def test_enroll_nonexistent_course(self):
        """Enroll ke course yang tidak ada harus 404."""
        resp = self.client.post(
            "/api/enrollments",
            data=json.dumps({"course_id": 99999}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 404)

    def test_enroll_requires_auth(self):
        """Enroll tanpa token harus ditolak."""
        resp = self.client.post(
            "/api/enrollments",
            data=json.dumps({"course_id": self.course.pk}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class MyCoursesAPITest(TestCase):
    """Test GET /api/enrollments/my-courses (student only)."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="mc_instr",
            email="mc_instr@test.com",
            password=_hash("pass1234"),
            role="instructor",
            is_active=True,
        )
        self.student = User.objects.create(
            username="mc_stud",
            email="mc_stud@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        # Buat 3 course dan enroll student ke 2 dari mereka
        self.courses = []
        for i in range(3):
            c = Course.objects.create(
                title=f"My Course {i}",
                description=f"Deskripsi my course {i} yang cukup panjang.",
                instructor=self.instructor,
            )
            self.courses.append(c)

        Enrollment.objects.create(student=self.student, course=self.courses[0])
        Enrollment.objects.create(student=self.student, course=self.courses[1])
        self.stud_token = _login(self.client, "mc_stud", "stud1234")

    def test_student_sees_only_their_courses(self):
        """Student hanya melihat course yang sudah di-enroll-nya sendiri."""
        resp = self.client.get(
            "/api/enrollments/my-courses",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)

    def test_my_courses_requires_auth(self):
        """Endpoint my-courses harus memerlukan autentikasi."""
        resp = self.client.get("/api/enrollments/my-courses")
        self.assertEqual(resp.status_code, 401)


class ProgressAPITest(TestCase):
    """Test POST /api/enrollments/{id}/progress."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create(
            username="prog_instr",
            email="prog_instr@test.com",
            password=_hash("pass1234"),
            role="instructor",
            is_active=True,
        )
        self.student = User.objects.create(
            username="prog_stud",
            email="prog_stud@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.other_student = User.objects.create(
            username="prog_stud2",
            email="prog_stud2@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Progress Test Course",
            description="Deskripsi course untuk test progress.",
            instructor=self.instructor,
        )
        self.lesson1 = Lesson.objects.create(
            course=self.course,
            title="Lesson 1",
            content="Konten panjang untuk lesson 1 progress test.",
            order=1,
        )
        self.lesson2 = Lesson.objects.create(
            course=self.course,
            title="Lesson 2",
            content="Konten panjang untuk lesson 2 progress test.",
            order=2,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.stud_token  = _login(self.client, "prog_stud", "stud1234")
        self.stud2_token = _login(self.client, "prog_stud2", "stud1234")

    def test_student_can_mark_lesson_complete(self):
        """Student bisa menandai lesson sebagai selesai."""
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson1.pk, "is_completed": True}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["is_completed"])
        self.assertEqual(data["lesson_id"], self.lesson1.pk)

    def test_student_can_unmark_lesson(self):
        """Student bisa menandai lesson sebagai belum selesai."""
        Progress.objects.create(student=self.student, lesson=self.lesson1, is_completed=True)
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson1.pk, "is_completed": False}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json()["is_completed"])

    def test_cannot_mark_progress_for_other_enrollment(self):
        """Student tidak bisa mark progress untuk enrollment milik orang lain."""
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson1.pk, "is_completed": True}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud2_token}",  # student2 != enrollment owner
        )
        self.assertEqual(resp.status_code, 404)

    def test_progress_requires_auth(self):
        """Mark progress tanpa token harus ditolak."""
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson1.pk, "is_completed": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_progress_for_lesson_outside_course(self):
        """Mark progress untuk lesson yang bukan bagian dari course enrollment harus 404."""
        other_course = Course.objects.create(
            title="Other Course",
            description="Deskripsi course lain untuk test.",
            instructor=self.instructor,
        )
        other_lesson = Lesson.objects.create(
            course=other_course,
            title="Other Lesson",
            content="Konten lesson dari course lain.",
            order=1,
        )
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": other_lesson.pk, "is_completed": True}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 404)

    def test_course_completion_triggers_when_all_lessons_done(self):
        """Menyelesaikan semua lesson dalam course tidak menghasilkan error."""
        # Tandai lesson1 selesai
        self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson1.pk, "is_completed": True}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        # Tandai lesson2 selesai (seharusnya trigger certificate task)
        resp = self.client.post(
            f"/api/enrollments/{self.enrollment.pk}/progress",
            data=json.dumps({"lesson_id": self.lesson2.pk, "is_completed": True}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 201)
        # Verifikasi semua lesson selesai
        completed = Progress.objects.filter(
            student=self.student,
            lesson__course=self.course,
            is_completed=True,
        ).count()
        self.assertEqual(completed, 2)


class AdminUserManagementTest(TestCase):
    """Test endpoint Admin user management."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create(
            username="adm_test",
            email="adm_test@test.com",
            password=_hash("admin1234"),
            role="admin",
            is_active=True,
        )
        self.student = User.objects.create(
            username="adm_stud",
            email="adm_stud@test.com",
            password=_hash("stud1234"),
            role="student",
            is_active=True,
        )
        self.admin_token = _login(self.client, "adm_test", "admin1234")
        self.stud_token  = _login(self.client, "adm_stud", "stud1234")

    def test_admin_can_list_users(self):
        """Admin bisa melihat daftar semua user."""
        resp = self.client.get(
            "/api/admin/users",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_student_cannot_list_users(self):
        """Student tidak bisa mengakses admin user list."""
        resp = self.client.get(
            "/api/admin/users",
            HTTP_AUTHORIZATION=f"Bearer {self.stud_token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_deactivate_user(self):
        """Admin bisa menonaktifkan user."""
        resp = self.client.post(
            f"/api/admin/users/{self.student.pk}/deactivate",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_admin_can_activate_user(self):
        """Admin bisa mengaktifkan kembali user yang dinonaktifkan."""
        self.student.is_active = False
        self.student.save()
        resp = self.client.post(
            f"/api/admin/users/{self.student.pk}/activate",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_admin_can_update_user_role(self):
        """Admin bisa mengubah role user."""
        resp = self.client.patch(
            f"/api/admin/users/{self.student.pk}",
            data=json.dumps({"role": "instructor"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["role"], "instructor")

    def test_admin_cannot_deactivate_self(self):
        """Admin tidak bisa menonaktifkan akun dirinya sendiri."""
        resp = self.client.post(
            f"/api/admin/users/{self.admin.pk}/deactivate",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )
        self.assertEqual(resp.status_code, 400)
