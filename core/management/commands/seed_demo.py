"""
Management command: seed_demo
Membuat data demo untuk final project presentation:
  - 1 admin (admin / Admin@1234)
  - 2 instructor (instructor01, instructor02 / Instructor@1234)
  - 3 student (student01, student02, student03 / Student@1234)
  - 5 category
  - 8 course (dengan lesson)
  - Enrollment & progress demo

Jalankan:
  docker compose exec web python manage.py seed_demo
  docker compose exec web python manage.py seed_demo --reset
"""

import bcrypt
from django.core.management.base import BaseCommand
from core.models import User, Category, Course, Lesson, Enrollment, Progress


def _hash(plain: str) -> str:
    """Hash password menggunakan bcrypt (sesuai auth_router.py)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


class Command(BaseCommand):
    help = "Seed demo data: admin, instructor, student, courses, lessons, enrollments, progress"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus data demo lama sebelum seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("🗑  Menghapus data demo lama..."))
            demo_usernames = [
                "admin", "instructor01", "instructor02",
                "student01", "student02", "student03",
            ]
            Progress.objects.filter(student__username__in=demo_usernames).delete()
            Enrollment.objects.filter(student__username__in=demo_usernames).delete()
            # Hapus course milik demo instructor
            Course.objects.filter(instructor__username__in=demo_usernames).delete()
            User.objects.filter(username__in=demo_usernames).delete()
            Category.objects.filter(name__in=[
                "Pemrograman", "Desain", "Data Science", "Bisnis", "Marketing"
            ]).delete()
            self.stdout.write(self.style.SUCCESS("✅ Data demo lama dihapus"))

        self.stdout.write("─" * 50)
        self.stdout.write("🌱 Mulai seeding data demo...")
        self.stdout.write("─" * 50)

        # ── 1. Admin ──────────────────────────────────
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@simplelms.dev",
                "password": _hash("Admin@1234"),
                "role": "admin",
                "first_name": "Super",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if not created:
            admin.password = _hash("Admin@1234")
            admin.role = "admin"
            admin.is_staff = True
            admin.is_superuser = True
            admin.is_active = True
            admin.save()
        self.stdout.write(f"  ✅ Admin     : admin / Admin@1234 {'(baru)' if created else '(diperbarui)'}")

        # ── 2. Instructor ─────────────────────────────
        instructors = []
        instructor_data = [
            ("instructor01", "Budi", "Santoso", "budi@simplelms.dev"),
            ("instructor02", "Siti", "Rahayu",  "siti@simplelms.dev"),
        ]
        for uname, fname, lname, email in instructor_data:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    "email": email,
                    "password": _hash("Instructor@1234"),
                    "role": "instructor",
                    "first_name": fname,
                    "last_name": lname,
                    "is_active": True,
                },
            )
            if not created:
                user.password = _hash("Instructor@1234")
                user.role = "instructor"
                user.is_active = True
                user.save()
            instructors.append(user)
            self.stdout.write(f"  ✅ Instructor : {uname} / Instructor@1234 {'(baru)' if created else '(diperbarui)'}")

        # ── 3. Student ────────────────────────────────
        students = []
        student_data = [
            ("student01", "Andi",  "Wijaya",  "andi@example.com"),
            ("student02", "Dewi",  "Lestari", "dewi@example.com"),
            ("student03", "Rizky", "Pratama", "rizky@example.com"),
        ]
        for uname, fname, lname, email in student_data:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    "email": email,
                    "password": _hash("Student@1234"),
                    "role": "student",
                    "first_name": fname,
                    "last_name": lname,
                    "is_active": True,
                },
            )
            if not created:
                user.password = _hash("Student@1234")
                user.role = "student"
                user.is_active = True
                user.save()
            students.append(user)
            self.stdout.write(f"  ✅ Student    : {uname} / Student@1234 {'(baru)' if created else '(diperbarui)'}")

        # ── 4. Category ───────────────────────────────
        self.stdout.write("\n📂 Membuat kategori...")
        cat_names = ["Pemrograman", "Desain", "Data Science", "Bisnis", "Marketing"]
        categories = {}
        for name in cat_names:
            cat, _ = Category.objects.get_or_create(name=name)
            categories[name] = cat
        self.stdout.write(f"  ✅ {len(categories)} kategori dibuat")

        # ── 5. Course + Lesson ────────────────────────
        self.stdout.write("\n📚 Membuat course dan lesson...")
        course_data = [
            {
                "title": "Python untuk Pemula",
                "description": "Pelajari dasar-dasar Python mulai dari variabel, loop, hingga function. Cocok untuk yang belum pernah coding.",
                "category": "Pemrograman",
                "instructor": instructors[0],
                "lessons": [
                    ("Perkenalan Python",         "Python adalah bahasa pemrograman tingkat tinggi yang mudah dipelajari. Pada lesson ini kita akan mengenal sejarah dan filosofi Python.", 1),
                    ("Variabel dan Tipe Data",    "Belajar cara mendeklarsikan variabel dan memahami tipe data dasar seperti int, float, string, dan boolean.", 2),
                    ("Kontrol Alur (if/else)",    "Memahami logika percabangan dengan if, elif, dan else untuk membuat program yang lebih dinamis.", 3),
                    ("Perulangan (for & while)",  "Mengulang eksekusi kode dengan for loop dan while loop beserta penggunaan break dan continue.", 4),
                    ("Function & Module",         "Membuat fungsi reusable dan menggunakan module standar Python seperti math dan datetime.", 5),
                ],
            },
            {
                "title": "Django REST API dengan Django Ninja",
                "description": "Bangun REST API modern menggunakan Django dan Django Ninja. Termasuk auth JWT, RBAC, dan dokumentasi Swagger.",
                "category": "Pemrograman",
                "instructor": instructors[0],
                "lessons": [
                    ("Setup Django Project",     "Inisialisasi project Django, konfigurasi virtual environment, dan instalasi django-ninja.", 1),
                    ("Model & Database",         "Mendefinisikan model Django dan melakukan migrasi ke PostgreSQL.", 2),
                    ("Membuat REST Endpoint",    "Membuat endpoint GET, POST, PATCH, DELETE menggunakan Django Ninja Router.", 3),
                    ("JWT Authentication",       "Implementasi login, register, dan proteksi endpoint menggunakan JWT token.", 4),
                    ("Role-Based Access Control","Mengatur hak akses berbeda untuk admin, instructor, dan student.", 5),
                    ("Testing API dengan Swagger","Menggunakan Swagger UI untuk menguji endpoint yang telah dibuat.", 6),
                ],
            },
            {
                "title": "UI/UX Design Fundamental",
                "description": "Memahami prinsip dasar desain antarmuka pengguna dan pengalaman pengguna. Dari wireframe hingga prototype.",
                "category": "Desain",
                "instructor": instructors[1],
                "lessons": [
                    ("Prinsip Desain UI",        "Memahami 8 prinsip golden rules desain interface: konsistensi, feedback, kontrol pengguna, dan lainnya.", 1),
                    ("Color Theory",             "Teori warna untuk desain digital: warna primer, sekunder, komplementer, dan cara membangun color palette.", 2),
                    ("Typography",               "Memilih dan mengkombinasikan font yang tepat untuk meningkatkan keterbacaan dan estetika.", 3),
                    ("Wireframing",              "Membuat wireframe dengan Figma untuk merancang layout sebelum implementasi.", 4),
                    ("Prototyping",              "Membuat interactive prototype untuk menguji alur pengguna sebelum development dimulai.", 5),
                ],
            },
            {
                "title": "Data Science dengan Python",
                "description": "Eksplorasi data, visualisasi, dan machine learning dasar menggunakan Python, Pandas, dan Scikit-learn.",
                "category": "Data Science",
                "instructor": instructors[1],
                "lessons": [
                    ("Pandas untuk Data Wrangling", "Menggunakan library Pandas untuk load, clean, dan transform data dari berbagai format.", 1),
                    ("Visualisasi dengan Matplotlib","Membuat grafik dan chart informatif menggunakan Matplotlib dan Seaborn.", 2),
                    ("Statistik Deskriptif",        "Memahami mean, median, mode, standar deviasi, dan distribusi data.", 3),
                    ("Machine Learning Dasar",      "Pengenalan konsep supervised dan unsupervised learning dengan Scikit-learn.", 4),
                ],
            },
            {
                "title": "Docker untuk Developer",
                "description": "Kontainerisasi aplikasi menggunakan Docker dan orkestrasi dengan Docker Compose.",
                "category": "Pemrograman",
                "instructor": instructors[0],
                "lessons": [
                    ("Konsep Container vs VM",    "Memahami perbedaan container dan virtual machine, serta keunggulan Docker.", 1),
                    ("Dockerfile",                "Menulis Dockerfile untuk membangun image aplikasi Python/Django.", 2),
                    ("Docker Compose",            "Mengorkestrasi multi-container dengan docker-compose.yml: web, db, redis.", 3),
                    ("Volume & Network",          "Memahami persistent storage dengan volume dan komunikasi antar container.", 4),
                ],
            },
            {
                "title": "Digital Marketing Essentials",
                "description": "Strategi pemasaran digital modern: SEO, SEM, content marketing, dan social media marketing.",
                "category": "Marketing",
                "instructor": instructors[1],
                "lessons": [
                    ("Pengenalan Digital Marketing", "Landscape digital marketing 2024: channel, tools, dan metrik yang perlu diketahui.", 1),
                    ("SEO Fundamental",              "On-page dan off-page SEO: keyword research, meta tags, backlink building.", 2),
                    ("Content Marketing",            "Strategi konten: blog, video, infografis untuk menarik dan mempertahankan audiens.", 3),
                ],
            },
            {
                "title": "Business Strategy & Analytics",
                "description": "Framework analisis bisnis modern: SWOT, OKR, dan penggunaan data untuk pengambilan keputusan.",
                "category": "Bisnis",
                "instructor": instructors[1],
                "lessons": [
                    ("SWOT Analysis",       "Cara melakukan analisis SWOT yang efektif dan menggunakannya dalam perencanaan bisnis.", 1),
                    ("OKR Framework",       "Menerapkan Objectives and Key Results untuk menetapkan dan mengukur tujuan organisasi.", 2),
                    ("Business Intelligence","Menggunakan data analytics untuk business decision making.", 3),
                ],
            },
            {
                "title": "Redis & Caching Strategy",
                "description": "Teknik caching dengan Redis untuk meningkatkan performa aplikasi web: cache invalidation, TTL, Pub/Sub.",
                "category": "Pemrograman",
                "instructor": instructors[0],
                "lessons": [
                    ("Mengapa Caching Penting",   "Bottleneck performa aplikasi dan bagaimana caching menyelesaikannya.", 1),
                    ("Redis Data Structures",     "String, Hash, List, Set, Sorted Set di Redis dan kapan menggunakannya.", 2),
                    ("Cache Invalidation Strategy","Teknik invalidasi cache: TTL, event-based, dan write-through.", 3),
                    ("Redis di Django",           "Konfigurasi django-redis dan implementasi caching di Django views.", 4),
                ],
            },
        ]

        courses = []
        for cdata in course_data:
            course, created = Course.objects.get_or_create(
                title=cdata["title"],
                defaults={
                    "description": cdata["description"],
                    "category": categories[cdata["category"]],
                    "instructor": cdata["instructor"],
                },
            )
            courses.append(course)

            # Buat lesson jika belum ada
            if not Lesson.objects.filter(course=course).exists():
                for title, content, order in cdata["lessons"]:
                    Lesson.objects.create(
                        course=course,
                        title=title,
                        content=content,
                        order=order,
                    )

            status = "(baru)" if created else "(sudah ada)"
            lesson_count = Lesson.objects.filter(course=course).count()
            self.stdout.write(
                f"  ✅ [{cdata['category']}] {cdata['title'][:45]:<45} | {lesson_count} lesson {status}"
            )

        # ── 6. Enrollment ─────────────────────────────
        self.stdout.write("\n📋 Membuat enrollment...")
        # student01 enroll di 5 course pertama
        enrollment_plan = {
            students[0]: courses[:5],   # student01 → 5 course
            students[1]: courses[1:6],  # student02 → 5 course
            students[2]: courses[3:],   # student03 → 5 course terakhir
        }

        all_enrollments = []
        for student, enrolled_courses in enrollment_plan.items():
            for course in enrolled_courses:
                enr, created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                )
                if created:
                    all_enrollments.append(enr)

        self.stdout.write(f"  ✅ {Enrollment.objects.filter(student__in=students).count()} enrollment total")

        # ── 7. Progress ───────────────────────────────
        self.stdout.write("\n✔  Membuat progress (sebagian lesson selesai)...")
        progress_count = 0

        # student01: selesaikan semua lesson di course pertama (trigger certificate)
        enr_s1_c1 = Enrollment.objects.filter(student=students[0], course=courses[0]).first()
        if enr_s1_c1:
            for lesson in Lesson.objects.filter(course=courses[0]):
                _, created = Progress.objects.get_or_create(
                    student=students[0],
                    lesson=lesson,
                    defaults={"is_completed": True},
                )
                if created:
                    progress_count += 1

        # student02: selesaikan sebagian lesson di course ke-2
        enr_s2_c2 = Enrollment.objects.filter(student=students[1], course=courses[1]).first()
        if enr_s2_c2:
            for i, lesson in enumerate(Lesson.objects.filter(course=courses[1]).order_by("order")):
                if i < 3:  # Selesaikan 3 dari 6 lesson
                    _, created = Progress.objects.get_or_create(
                        student=students[1],
                        lesson=lesson,
                        defaults={"is_completed": True},
                    )
                    if created:
                        progress_count += 1

        # student03: selesaikan 1 lesson di course terakhir
        enr_s3 = Enrollment.objects.filter(student=students[2], course=courses[3]).first()
        if enr_s3:
            first_lesson = Lesson.objects.filter(course=courses[3]).order_by("order").first()
            if first_lesson:
                _, created = Progress.objects.get_or_create(
                    student=students[2],
                    lesson=first_lesson,
                    defaults={"is_completed": True},
                )
                if created:
                    progress_count += 1

        self.stdout.write(f"  ✅ {progress_count} progress record dibuat")

        # ── Summary ───────────────────────────────────
        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(self.style.SUCCESS("🎉 Seeding data demo selesai!\n"))
        self.stdout.write(self.style.SUCCESS(
            f"   User         : {User.objects.count()} (admin: 1, instructor: 2, student: 3)\n"
            f"   Category     : {Category.objects.count()}\n"
            f"   Course       : {Course.objects.count()}\n"
            f"   Lesson       : {Lesson.objects.count()}\n"
            f"   Enrollment   : {Enrollment.objects.count()}\n"
            f"   Progress     : {Progress.objects.count()}\n"
        ))
        self.stdout.write(self.style.WARNING(
            "Akun Demo:\n"
            "  admin        : admin / Admin@1234\n"
            "  instructor01 : instructor01 / Instructor@1234\n"
            "  instructor02 : instructor02 / Instructor@1234\n"
            "  student01    : student01 / Student@1234\n"
            "  student02    : student02 / Student@1234\n"
            "  student03    : student03 / Student@1234\n"
        ))
