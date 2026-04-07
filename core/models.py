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
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'instructor'}, related_name='teaching_courses')
    created_at = models.DateTimeField(auto_now_add=True)

    # Attach Custom Manager
    objects = CourseManager()

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order'] # Mengurutkan berdasarkan field order

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentManager()

    class Meta:
        # Unique Constraint: 1 Student hanya bisa enroll 1 Course yang sama sebanyak 1 kali
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'lesson')

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title} - {'Done' if self.is_completed else 'Ongoing'}"