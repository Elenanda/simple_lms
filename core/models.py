from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# --- CUSTOM MANAGERS ---
class CourseManager(models.Manager):
    def for_listing(self):
        # Menggunakan select_related untuk Foreign Key (category, instructor)
        # Menggunakan prefetch_related untuk Reverse/Many-to-Many relasi (lessons)
        return self.get_queryset().select_related('category', 'instructor').prefetch_related('lessons')

class EnrollmentManager(models.Manager):
    def for_student_dashboard(self):
        # Optimasi pengambilan data course dan category-nya
        return self.get_queryset().select_related('course', 'course__category')


# --- MODELS ---
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

class Category(models.Model):
    name = models.CharField(max_length=100)
    # Self-referencing untuk sub-kategori
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.parent.name} > {self.name}" if self.parent else self.name

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    # db_index=True — sering difilter/join di endpoint lab
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses', db_index=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'instructor'}, related_name='teaching_courses', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Attach Custom Manager
    objects = CourseManager()

    class Meta:
        indexes = [
            # Index komposit: filter by instructor + order by created_at (dashboard dosen)
            models.Index(fields=['instructor', 'created_at'], name='idx_course_instructor_created'),
            # Index: filter/sort by category (listing)
            models.Index(fields=['category'], name='idx_course_category'),
        ]

    def __str__(self):
        return self.title

class Lesson(models.Model):
    # db_index=True — sering di-JOIN ke Progress dan di-filter by course
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']  # Mengurutkan berdasarkan field order
        indexes = [
            # Index komposit: ambil lessons of course ordered by order
            models.Index(fields=['course', 'order'], name='idx_lesson_course_order'),
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    # db_index=True — sering di-COUNT dan di-JOIN untuk member count
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='enrollments', db_index=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', db_index=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentManager()

    class Meta:
        # Unique Constraint: 1 Student hanya bisa enroll 1 Course yang sama sebanyak 1 kali
        unique_together = ('student', 'course')
        indexes = [
            # Index komposit: count enrollments per course (endpoint course-members)
            models.Index(fields=['course', 'student'], name='idx_enrollment_course_student'),
        ]

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

class Progress(models.Model):
    # db_index=True — sering di-filter by is_completed dan di-JOIN ke Lesson
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='progress', db_index=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress', db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'lesson')
        indexes = [
            # Index komposit: filter progress WHERE is_completed=True AND lesson__course=X
            models.Index(fields=['lesson', 'is_completed'], name='idx_progress_lesson_completed'),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title} - {'Done' if self.is_completed else 'Ongoing'}"