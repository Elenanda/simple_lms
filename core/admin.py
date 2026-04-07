from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Course, Lesson, Enrollment, Progress

# --- UBAH BAGIAN INI ---
class CustomUserAdmin(UserAdmin):
    # Menambahkan field 'role' ke halaman edit user
    fieldsets = UserAdmin.fieldsets + (
        ('LMS Role Configuration', {'fields': ('role',)}),
    )
    # Menampilkan 'role' di tabel daftar user
    list_display = ('username', 'email', 'is_staff', 'role')

admin.site.register(User, CustomUserAdmin)
# -----------------------

# Register User dengan field Role tambahan


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)

# Inline model untuk Lesson di dalam Course
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'created_at')
    list_filter = ('category', 'instructor')
    search_fields = ('title', 'description')
    inlines = [LessonInline]

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at')
    list_filter = ('course',)
    search_fields = ('student__username', 'course__title')

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'is_completed')
    list_filter = ('is_completed',)