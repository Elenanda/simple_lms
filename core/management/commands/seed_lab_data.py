"""
Management command: seed_lab_data
Membuat data dummy untuk praktikum profiling:
  - 5 instructor, 50 student
  - 100 course (20 per instructor)
  - 5-10 lesson per course
  - Enrollment acak (setiap student di 10-30 course)
  - Progress acak

Jalankan:
  docker-compose exec web python manage.py seed_lab_data
  docker-compose exec web python manage.py seed_lab_data --reset
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import User, Category, Course, Lesson, Enrollment, Progress


class Command(BaseCommand):
    help = 'Seed lab data: 100 courses, 5 instructors, 50 students, enrollments, progress'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Hapus semua data lama sebelum seeding',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('🗑  Menghapus data lama...'))
            Progress.objects.all().delete()
            Enrollment.objects.all().delete()
            Lesson.objects.all().delete()
            Course.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(role__in=['instructor', 'student']).delete()
            self.stdout.write(self.style.SUCCESS('✅ Data lama dihapus'))

        self.stdout.write('📦 Membuat kategori...')
        categories = []
        category_names = ['Programming', 'Design', 'Data Science', 'Business', 'Marketing']
        for name in category_names:
            cat, _ = Category.objects.get_or_create(name=name)
            categories.append(cat)

        self.stdout.write('👩‍🏫 Membuat 5 instructor...')
        instructors = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                username=f'instructor{i:02d}',
                defaults={
                    'email': f'instructor{i:02d}@lab.edu',
                    'password': make_password('password123'),
                    'role': 'instructor',
                    'first_name': f'Dosen{i}',
                    'last_name': 'LMS',
                    'is_staff': False,
                }
            )
            if not created:
                user.role = 'instructor'
                user.save()
            instructors.append(user)

        self.stdout.write('🎓 Membuat 50 student...')
        students = []
        for i in range(1, 51):
            user, created = User.objects.get_or_create(
                username=f'student{i:03d}',
                defaults={
                    'email': f'student{i:03d}@lab.edu',
                    'password': make_password('password123'),
                    'role': 'student',
                    'first_name': f'Mahasiswa{i}',
                    'last_name': 'LMS',
                }
            )
            if not created:
                user.role = 'student'
                user.save()
            students.append(user)

        self.stdout.write('📚 Membuat 100 course...')
        courses = []
        for i in range(1, 101):
            instructor = instructors[(i - 1) % len(instructors)]
            category = random.choice(categories)
            course, _ = Course.objects.get_or_create(
                title=f'Course {i:03d}: {category.name} Level {(i % 5) + 1}',
                defaults={
                    'description': (
                        f'Deskripsi lengkap untuk Course {i:03d}. '
                        f'Diajarkan oleh {instructor.get_full_name()} '
                        f'di kategori {category.name}. '
                        'Cocok untuk pemula hingga menengah.'
                    ),
                    'category': category,
                    'instructor': instructor,
                }
            )
            courses.append(course)

        self.stdout.write('📖 Membuat 5–10 lesson per course...')
        lessons_created = 0
        all_lessons = []
        for course in courses:
            if Lesson.objects.filter(course=course).exists():
                all_lessons.extend(list(Lesson.objects.filter(course=course)))
                continue
            n_lessons = random.randint(5, 10)
            bulk = [
                Lesson(
                    course=course,
                    title=f'Lesson {j}: Materi {j} - {course.title}',
                    content=f'Konten lengkap untuk lesson {j} dari {course.title}. ' * 5,
                    order=j,
                )
                for j in range(1, n_lessons + 1)
            ]
            created = Lesson.objects.bulk_create(bulk)
            all_lessons.extend(created)
            lessons_created += len(created)
        self.stdout.write(f'   → {lessons_created} lesson baru dibuat')

        self.stdout.write('📋 Membuat enrollment (10–30 course per student)...')
        enrollments_created = 0
        all_enrollments = []
        for student in students:
            n_enroll = random.randint(10, 30)
            chosen_courses = random.sample(courses, min(n_enroll, len(courses)))
            for course in chosen_courses:
                enr, created = Enrollment.objects.get_or_create(
                    student=student, course=course
                )
                if created:
                    enrollments_created += 1
                all_enrollments.append(enr)
        self.stdout.write(f'   → {enrollments_created} enrollment baru dibuat')

        self.stdout.write('✔  Membuat progress acak...')
        progress_created = 0
        lessons_by_course = {}
        for lesson in all_lessons:
            lessons_by_course.setdefault(lesson.course_id, []).append(lesson)

        for enr in all_enrollments[:200]:  # Batasi untuk performa seeding
            course_lessons = lessons_by_course.get(enr.course_id, [])
            if not course_lessons:
                continue
            sample_lessons = random.sample(course_lessons, min(3, len(course_lessons)))
            for lesson in sample_lessons:
                _, created = Progress.objects.get_or_create(
                    student=enr.student,
                    lesson=lesson,
                    defaults={'is_completed': random.choice([True, False])}
                )
                if created:
                    progress_created += 1

        self.stdout.write(f'   → {progress_created} progress record dibuat')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '🎉 Seeding selesai!\n'
            f'   Instructor : {len(instructors)}\n'
            f'   Student    : {len(students)}\n'
            f'   Course     : {len(courses)}\n'
            f'   Category   : {len(categories)}\n'
            f'   Lesson     : {Lesson.objects.count()}\n'
            f'   Enrollment : {Enrollment.objects.count()}\n'
            f'   Progress   : {Progress.objects.count()}\n'
        ))
        self.stdout.write(self.style.WARNING(
            'Selanjutnya:\n'
            '  1. Akses http://localhost:8000/silk/ untuk memverifikasi Silk\n'
            '  2. Hit baseline endpoints & simpan screenshot Silk\n'
            '  3. Hit optimized endpoints & bandingkan\n'
        ))
