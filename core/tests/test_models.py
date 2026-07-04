"""
core/tests/test_models.py
Unit test untuk model Django: User, Category, Course, Lesson, Enrollment, Progress

Jalankan: python manage.py test core.tests.test_models --verbosity=2
"""

import bcrypt
from django.test import TestCase
from core.models import User, Category, Course, Lesson, Enrollment, Progress


def make_password(plain: str) -> str:
    """Hash password menggunakan bcrypt (sesuai auth_router.py)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


class UserModelTest(TestCase):
    """Test untuk model User (custom AbstractUser)."""

    def setUp(self):
        self.admin = User.objects.create(
            username="test_admin",
            email="admin@test.com",
            password=make_password("admin123"),
            role="admin",
        )
        self.instructor = User.objects.create(
            username="test_instructor",
            email="instructor@test.com",
            password=make_password("instr123"),
            role="instructor",
        )
        self.student = User.objects.create(
            username="test_student",
            email="student@test.com",
            password=make_password("stud123"),
            role="student",
        )

    def test_user_roles(self):
        """User mempunyai role yang benar."""
        self.assertEqual(self.admin.role, "admin")
        self.assertEqual(self.instructor.role, "instructor")
        self.assertEqual(self.student.role, "student")

    def test_default_role_is_student(self):
        """Default role harus 'student'."""
        user = User.objects.create(
            username="default_role_user",
            email="default@test.com",
            password=make_password("pass123"),
        )
        self.assertEqual(user.role, "student")

    def test_user_is_active_by_default(self):
        """User baru seharusnya aktif by default."""
        self.assertTrue(self.student.is_active)

    def test_user_str(self):
        """__str__ User mengembalikan username."""
        self.assertEqual(str(self.student), "test_student")

    def test_password_is_hashed(self):
        """Password harus disimpan dalam format hash (bukan plain text)."""
        self.assertNotEqual(self.student.password, "stud123")
        # Pastikan format bcrypt (starts with $2b$)
        self.assertTrue(self.student.password.startswith("$2b$"))


class CategoryModelTest(TestCase):
    """Test untuk model Category (termasuk parent/subcategory)."""

    def test_create_root_category(self):
        """Bisa membuat kategori tanpa parent."""
        cat = Category.objects.create(name="Programming")
        self.assertIsNone(cat.parent)
        self.assertEqual(str(cat), "Programming")

    def test_create_subcategory(self):
        """Bisa membuat sub-kategori dengan parent."""
        parent = Category.objects.create(name="Technology")
        child = Category.objects.create(name="Web Development", parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertEqual(str(child), "Technology > Web Development")

    def test_subcategory_in_subcategories_queryset(self):
        """Sub-kategori muncul di related manager 'subcategories'."""
        parent = Category.objects.create(name="Science")
        child1 = Category.objects.create(name="Physics", parent=parent)
        child2 = Category.objects.create(name="Chemistry", parent=parent)
        subcats = list(parent.subcategories.all())
        self.assertIn(child1, subcats)
        self.assertIn(child2, subcats)


class CourseModelTest(TestCase):
    """Test untuk model Course."""

    def setUp(self):
        self.instructor = User.objects.create(
            username="course_instr",
            email="ci@test.com",
            password=make_password("pass"),
            role="instructor",
        )
        self.category = Category.objects.create(name="Test Category")

    def test_create_course(self):
        """Bisa membuat course dengan benar."""
        course = Course.objects.create(
            title="Test Course",
            description="Deskripsi test course minimal.",
            instructor=self.instructor,
            category=self.category,
        )
        self.assertEqual(course.title, "Test Course")
        self.assertEqual(course.instructor, self.instructor)
        self.assertEqual(course.category, self.category)
        self.assertIsNotNone(course.created_at)

    def test_course_str(self):
        """__str__ Course mengembalikan title."""
        course = Course.objects.create(
            title="My Course",
            description="Deskripsi panjang untuk test course ini.",
            instructor=self.instructor,
        )
        self.assertEqual(str(course), "My Course")

    def test_course_without_category(self):
        """Course bisa dibuat tanpa category (nullable FK)."""
        course = Course.objects.create(
            title="No Category Course",
            description="Deskripsi course tanpa category.",
            instructor=self.instructor,
            category=None,
        )
        self.assertIsNone(course.category)


class LessonModelTest(TestCase):
    """Test untuk model Lesson."""

    def setUp(self):
        self.instructor = User.objects.create(
            username="lesson_instr",
            email="li@test.com",
            password=make_password("pass"),
            role="instructor",
        )
        self.course = Course.objects.create(
            title="Lesson Test Course",
            description="Deskripsi course untuk test lesson.",
            instructor=self.instructor,
        )

    def test_create_lesson(self):
        """Bisa membuat lesson yang terkait dengan course."""
        lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson 1",
            content="Konten lesson 1 yang cukup panjang untuk test.",
            order=1,
        )
        self.assertEqual(lesson.course, self.course)
        self.assertEqual(lesson.order, 1)

    def test_lessons_ordered_by_order_field(self):
        """Lesson diurutkan berdasarkan field 'order' secara default."""
        Lesson.objects.create(course=self.course, title="L3", content="Konten panjang L3.", order=3)
        Lesson.objects.create(course=self.course, title="L1", content="Konten panjang L1.", order=1)
        Lesson.objects.create(course=self.course, title="L2", content="Konten panjang L2.", order=2)

        lessons = list(Lesson.objects.filter(course=self.course))
        self.assertEqual(lessons[0].title, "L1")
        self.assertEqual(lessons[1].title, "L2")
        self.assertEqual(lessons[2].title, "L3")

    def test_lesson_str(self):
        """__str__ Lesson mengembalikan format 'Course - Lesson'."""
        lesson = Lesson.objects.create(
            course=self.course,
            title="Lesson Test",
            content="Konten panjang untuk test str method.",
            order=1,
        )
        self.assertIn("Lesson Test Course", str(lesson))
        self.assertIn("Lesson Test", str(lesson))


class EnrollmentModelTest(TestCase):
    """Test untuk model Enrollment."""

    def setUp(self):
        self.instructor = User.objects.create(
            username="enr_instr",
            email="ei@test.com",
            password=make_password("pass"),
            role="instructor",
        )
        self.student = User.objects.create(
            username="enr_student",
            email="es@test.com",
            password=make_password("pass"),
            role="student",
        )
        self.course = Course.objects.create(
            title="Enrollment Test Course",
            description="Deskripsi course untuk test enrollment.",
            instructor=self.instructor,
        )

    def test_create_enrollment(self):
        """Bisa membuat enrollment untuk student dan course."""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.course, self.course)
        self.assertIsNotNone(enrollment.enrolled_at)

    def test_enrollment_unique_constraint(self):
        """Satu student tidak bisa enroll course yang sama dua kali."""
        from django.db import IntegrityError
        Enrollment.objects.create(student=self.student, course=self.course)
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(student=self.student, course=self.course)

    def test_enrollment_str(self):
        """__str__ Enrollment mengembalikan format yang benar."""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.assertIn("enr_student", str(enrollment))
        self.assertIn("Enrollment Test Course", str(enrollment))


class ProgressModelTest(TestCase):
    """Test untuk model Progress."""

    def setUp(self):
        self.instructor = User.objects.create(
            username="prog_instr",
            email="pi@test.com",
            password=make_password("pass"),
            role="instructor",
        )
        self.student = User.objects.create(
            username="prog_student",
            email="ps@test.com",
            password=make_password("pass"),
            role="student",
        )
        self.course = Course.objects.create(
            title="Progress Test Course",
            description="Deskripsi course untuk test progress.",
            instructor=self.instructor,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Progress Test Lesson",
            content="Konten panjang untuk test progress.",
            order=1,
        )
        Enrollment.objects.create(student=self.student, course=self.course)

    def test_create_progress(self):
        """Bisa membuat progress record untuk student dan lesson."""
        progress = Progress.objects.create(
            student=self.student,
            lesson=self.lesson,
            is_completed=False,
        )
        self.assertFalse(progress.is_completed)
        self.assertIsNone(progress.completed_at)

    def test_progress_mark_completed(self):
        """Progress bisa ditandai sebagai selesai."""
        from datetime import datetime, timezone
        progress = Progress.objects.create(
            student=self.student,
            lesson=self.lesson,
            is_completed=False,
        )
        progress.is_completed = True
        progress.completed_at = datetime.now(timezone.utc)
        progress.save(update_fields=["is_completed", "completed_at"])

        refreshed = Progress.objects.get(pk=progress.pk)
        self.assertTrue(refreshed.is_completed)
        self.assertIsNotNone(refreshed.completed_at)

    def test_progress_unique_constraint(self):
        """Satu student tidak bisa punya progress ganda untuk lesson yang sama."""
        from django.db import IntegrityError
        Progress.objects.create(student=self.student, lesson=self.lesson)
        with self.assertRaises(IntegrityError):
            Progress.objects.create(student=self.student, lesson=self.lesson)
