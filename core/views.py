from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min, Sum, Q
from .models import Course, Lesson, Enrollment, Progress, User


# ============================================================
# ENDPOINT 1 — Course List + Instructor (Teacher)
# Demonstrasi: N+1 Problem vs select_related
# ============================================================

def course_list_baseline(request):
    """
    [BASELINE] Mengambil daftar course beserta nama instructor.
    MASALAH: N+1 Query — setiap iterasi memicu query baru ke tabel User
    untuk mengambil instructor.username.
    Untuk N=100 course → 1 (SELECT courses) + 100 (SELECT user per course) = 101 queries.
    """
    courses = Course.objects.all()  # Hanya 1 query untuk courses
    data = []
    for c in courses:
        data.append({
            'id': c.id,
            'course': c.title,
            # ⚠️ Setiap baris ini memicu 1 query tambahan ke tabel User!
            'instructor': c.instructor.username,
            'category': c.category.name if c.category else None,
        })
    return JsonResponse({'data': data, 'count': len(data)})


def course_list_optimized(request):
    """
    [OPTIMIZED] Menggunakan select_related untuk JOIN tabel User & Category
    dalam satu query, sehingga tidak ada query tambahan di dalam loop.
    Total: hanya 1 query (JOIN) untuk semua data.
    """
    courses = Course.objects.select_related('instructor', 'category').all()
    data = []
    for c in courses:
        data.append({
            'id': c.id,
            'course': c.title,
            # ✅ Tidak memicu query baru — data instructor sudah di-JOIN
            'instructor': c.instructor.username,
            'category': c.category.name if c.category else None,
        })
    return JsonResponse({'data': data, 'count': len(data)})


# ============================================================
# ENDPOINT 2 — Course + Members + Lessons + Progress Count
# Demonstrasi: reverse FK N+1 vs prefetch_related + annotate
# ============================================================

def course_members_baseline(request):
    """
    [BASELINE] Mengambil course beserta jumlah member (enrollment),
    jumlah lesson, dan jumlah progress yang selesai.
    MASALAH: Setiap .count() & .filter() di dalam loop memicu query baru.
    Untuk N=100 course → 1 + (100 × 3) = 301 queries.
    """
    courses = Course.objects.all()
    payload = []
    for c in courses:
        # ⚠️ Setiap baris berikut memicu 1 query terpisah!
        member_count = Enrollment.objects.filter(course=c).count()
        lesson_count = Lesson.objects.filter(course=c).count()
        completed_count = Progress.objects.filter(
            lesson__course=c, is_completed=True
        ).count()
        payload.append({
            'id': c.id,
            'course': c.title,
            'member_count': member_count,
            'lesson_count': lesson_count,
            'completed_progress_count': completed_count,
        })
    return JsonResponse({'data': payload, 'count': len(payload)})


def course_members_optimized(request):
    """
    [OPTIMIZED] Menggunakan annotate() untuk menghitung statistik relasi
    langsung di level database dengan GROUP BY — tidak ada loop query.
    Total: hanya 1 query untuk semua data.
    """
    courses = Course.objects.select_related('instructor', 'category').annotate(
        member_count=Count('enrollments', distinct=True),
        lesson_count=Count('lessons', distinct=True),
        completed_progress_count=Count(
            'lessons__progress',
            filter=Q(lessons__progress__is_completed=True),
            distinct=True,
        ),
    ).order_by('id')
    payload = []
    for c in courses:
        payload.append({
            'id': c.id,
            'course': c.title,
            'instructor': c.instructor.username,
            'member_count': c.member_count,
            'lesson_count': c.lesson_count,
            'completed_progress_count': c.completed_progress_count,
        })
    return JsonResponse({'data': payload, 'count': len(payload)})


# ============================================================
# ENDPOINT 3 — Statistik Dashboard Dosen (Instructor)
# Demonstrasi: iterasi Python vs aggregate/annotate SQL
# ============================================================

def course_dashboard_baseline(request):
    """
    [BASELINE] Menghitung statistik dashboard secara manual dalam loop Python.
    MASALAH: Total, jumlah member per course, dan statistik global
    dihitung dengan banyak query terpisah — sangat tidak efisien.
    """
    courses = Course.objects.all()
    course_stats = []
    for c in courses:
        # ⚠️ Setiap iterasi memicu query baru!
        member_count = Enrollment.objects.filter(course=c).count()
        lesson_count = Lesson.objects.filter(course=c).count()
        course_stats.append({
            'id': c.id,
            'title': c.title,
            'member_count': member_count,
            'lesson_count': lesson_count,
        })

    # ⚠️ Statistik global — masing-masing query terpisah!
    total_courses = Course.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_instructors = User.objects.filter(role='instructor').count()
    total_enrollments = Enrollment.objects.count()
    total_lessons = Lesson.objects.count()

    return JsonResponse({
        'global_stats': {
            'total_courses': total_courses,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_enrollments': total_enrollments,
            'total_lessons': total_lessons,
        },
        'course_stats': course_stats,
        'count': len(course_stats),
    })


def course_dashboard_optimized(request):
    """
    [OPTIMIZED] Menggunakan aggregate() untuk statistik global (1 query)
    dan annotate() untuk per-course stats (1 query dengan GROUP BY).
    Total: hanya 2 queries untuk seluruh dashboard.
    """
    # ✅ Semua statistik per-course dalam 1 query dengan annotate
    courses = Course.objects.select_related('instructor', 'category').annotate(
        member_count=Count('enrollments', distinct=True),
        lesson_count=Count('lessons', distinct=True),
    ).order_by('-member_count')

    course_stats = [
        {
            'id': c.id,
            'title': c.title,
            'instructor': c.instructor.username,
            'category': c.category.name if c.category else None,
            'member_count': c.member_count,
            'lesson_count': c.lesson_count,
        }
        for c in courses
    ]

    # ✅ Statistik global dalam 1 query dengan aggregate
    global_stats = {
        'total_courses': Course.objects.aggregate(total=Count('id'))['total'],
        'total_students': User.objects.filter(role='student').aggregate(
            total=Count('id')
        )['total'],
        'total_instructors': User.objects.filter(role='instructor').aggregate(
            total=Count('id')
        )['total'],
        'total_enrollments': Enrollment.objects.aggregate(
            total=Count('id')
        )['total'],
        'total_lessons': Lesson.objects.aggregate(total=Count('id'))['total'],
    }

    return JsonResponse({
        'global_stats': global_stats,
        'course_stats': course_stats,
        'count': len(course_stats),
    })
