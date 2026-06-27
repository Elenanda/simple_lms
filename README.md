# 🎓 Simple LMS — Django REST API Project

Sistem manajemen pembelajaran (LMS) berbasis **Django 4.2**, lengkap dengan **REST API (Django Ninja)**, **JWT Authentication**, **Role-Based Access Control (RBAC)**, dan **Query Optimization** menggunakan PostgreSQL / SQLite.

---

## 📑 Daftar Isi

1. [Tech Stack](#tech-stack)
2. [Arsitektur Project](#arsitektur-project)
3. [Data Models](#data-models--relasi)
4. [REST API — Endpoint Lengkap](#rest-api--endpoint-lengkap)
5. [Authentication System (JWT)](#authentication-system-jwt)
6. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
7. [Pydantic Schemas](#pydantic-schemas)
8. [Query Optimization](#query-optimization)
9. [Swagger UI Documentation](#swagger-ui-documentation)
10. [Cara Menjalankan Project](#cara-menjalankan-project)
11. [Docker Setup](#docker-setup)
12. [Environment Variables](#environment-variables)
13. [Postman Collection](#postman-collection)
14. [Screenshots](#screenshots)

---

## Tech Stack

| Teknologi | Versi | Fungsi |
|---|---|---|
| Django | 4.2.11 | Web framework |
| Django Ninja | 1.6.2 | REST API + Swagger UI |
| PyJWT | 2.9.0 | JWT token generation & validation |
| bcrypt | 4.2.0 | Password hashing |
| email-validator | 2.3.0 | Pydantic EmailStr support |
| PostgreSQL | 15 | Database produksi (via Docker) |
| SQLite | bawaan | Database dev lokal |
| Django Silk | 5.5.0 | Query profiling |
| Docker + Docker Compose | — | Containerisasi |

---

## Arsitektur Project

```
simple-lms/
├── config/
│   ├── settings.py          # Django settings + JWT config + DB auto-detect
│   ├── urls.py              # Root URL: /api/ → Ninja, /courses/ → core, /silk/
│   └── wsgi.py
├── core/
│   ├── models.py            # 6 Models: User, Category, Course, Lesson, Enrollment, Progress
│   ├── admin.py             # Django Admin config (TabularInline, list_display, dll)
│   ├── views.py             # Lab endpoints: baseline vs optimized
│   ├── urls.py              # /courses/lab/* routes
│   └── fixtures/
│       └── initial_data.json
├── api/
│   ├── main.py              # NinjaAPI instance — Swagger di /api/docs
│   ├── auth.py              # JWTAuth backend + role decorators
│   ├── schemas.py           # 16 Pydantic schemas
│   └── routers/
│       ├── auth_router.py       # /api/auth/* (5 endpoints)
│       ├── course_router.py     # /api/courses/* (5 endpoints)
│       └── enrollment_router.py # /api/enrollments/* (3 endpoints)
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── simple_lms_api.postman_collection.json
```

---

## Data Models & Relasi

Diimplementasikan **6 model utama** di `core/models.py`:

### Diagram Relasi

```
User (AbstractUser + role)
 ├─[instructor]─► Course ──► Category (self-referencing)
 │                  └──► Lesson (ordered)
 └─[student]──► Enrollment ──► Course
                    └──► Progress ──► Lesson
```

### Detail Model

| Model | Relasi Utama | Fitur Khusus |
|---|---|---|
| `User` | — | `role` field: admin/instructor/student |
| `Category` | Self FK (`parent`) | Hierarki sub-kategori |
| `Course` | FK User (instructor), FK Category | Custom Manager, DB Index komposit |
| `Lesson` | FK Course | `Meta ordering` by `order` |
| `Enrollment` | FK User (student), FK Course | `unique_together` (student, course) |
| `Progress` | FK User, FK Lesson | Track `is_completed` + `completed_at` |

### Custom Model Managers

```python
# core/models.py
class CourseManager(models.Manager):
    def for_listing(self):
        return self.get_queryset().select_related('category', 'instructor') \
                                  .prefetch_related('lessons')

class EnrollmentManager(models.Manager):
    def for_student_dashboard(self):
        return self.get_queryset().select_related('course', 'course__category')
```

---

## REST API — Endpoint Lengkap

Base URL: `http://127.0.0.1:8000/api`  
Swagger UI: **http://127.0.0.1:8000/api/docs**

### 🔐 Authentication (`/api/auth`)

| Method | Endpoint | Akses | Deskripsi |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Daftarkan user baru |
| `POST` | `/auth/login` | Public | Login → JWT access + refresh token |
| `POST` | `/auth/refresh` | Public | Tukar refresh token → access token baru |
| `GET` | `/auth/me` | 🔒 Any | Profil user yang sedang login |
| `PUT` | `/auth/me` | 🔒 Any | Update profil (nama, email) |

### 📚 Courses (`/api/courses`)

| Method | Endpoint | Akses | Deskripsi |
|---|---|---|---|
| `GET` | `/courses` | Public | List courses (pagination + filter) |
| `GET` | `/courses/{id}` | Public | Detail course + enrollment count |
| `POST` | `/courses` | 🔒 Instructor | Buat course baru |
| `PATCH` | `/courses/{id}` | 🔒 Instructor (owner) | Update course milik sendiri |
| `DELETE` | `/courses/{id}` | 🔒 Admin | Hapus course |

**Query Parameters `GET /courses`:**
```
page         = 1        (default, min: 1)
page_size    = 10       (default, max: 100)
search       = "python" (filter judul, case-insensitive)
category_id  = 2        (filter by kategori)
instructor_id= 5        (filter by instruktur)
```

### 📋 Enrollments (`/api/enrollments`)

| Method | Endpoint | Akses | Deskripsi |
|---|---|---|---|
| `POST` | `/enrollments` | 🔒 Student | Enroll ke course |
| `GET` | `/enrollments/my-courses` | 🔒 Student | Daftar course yang diikuti |
| `POST` | `/enrollments/{id}/progress` | 🔒 Student | Tandai lesson selesai/belum |

---

## Authentication System (JWT)

### Flow Diagram

```
POST /api/auth/login
  └─► bcrypt.checkpw(password, hash)
      └─► create_access_token(user_id)   [exp: 60 menit, HS256]
          create_refresh_token(user_id)  [exp: 7 hari, HS256]
              └─► Response: { access_token, refresh_token }

Protected Request:
  Header: Authorization: Bearer <access_token>
      └─► JWTAuth.authenticate()
          └─► jwt.decode(token, SECRET_KEY)
              └─► User.objects.get(pk=sub)
                  └─► request.auth = user ✅
```

### Token Payload

```json
// Access Token (exp: +1 jam)
{ "sub": "42", "type": "access", "exp": 1720000000, "iat": 1719996400 }

// Refresh Token (exp: +7 hari)
{ "sub": "42", "type": "refresh", "exp": 1720600000, "iat": 1719996400 }
```

### Password Hashing

```python
# Register — hash dengan bcrypt
hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

# Login — verifikasi
if not bcrypt.checkpw(data.password.encode(), user.password.encode()):
    if not user.check_password(data.password):   # fallback Django native
        raise HttpError(401, "Username atau password salah.")
```

---

## Role-Based Access Control (RBAC)

### Role Decorators (`api/auth.py`)

```python
is_admin               = _role_required("admin")
is_instructor          = _role_required("instructor")
is_student             = _role_required("student")
is_admin_or_instructor = _role_required("admin", "instructor")
```

### Permission Matrix

| Endpoint | Public | Student | Instructor | Admin |
|---|:---:|:---:|:---:|:---:|
| `GET /api/courses` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/courses/{id}` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/courses` | ❌ | ❌ | ✅ | ❌ |
| `PATCH /api/courses/{id}` | ❌ | ❌ | ✅ (owner) | ❌ |
| `DELETE /api/courses/{id}` | ❌ | ❌ | ❌ | ✅ |
| `POST /api/enrollments` | ❌ | ✅ | ❌ | ❌ |
| `GET /api/enrollments/my-courses` | ❌ | ✅ | ❌ | ❌ |
| `POST /api/enrollments/{id}/progress` | ❌ | ✅ | ❌ | ❌ |

### Ownership Validation

Selain role check, instructor hanya bisa mengedit **course miliknya sendiri**:

```python
@router.patch("/{course_id}", auth=jwt_auth)
@is_instructor
def update_course(request, course_id, data):
    course = Course.objects.get(pk=course_id)
    if course.instructor_id != request.auth.pk:
        raise HttpError(403, "Anda bukan pemilik course ini.")
```

---

## Pydantic Schemas

Seluruh schema didefinisikan di `api/schemas.py` menggunakan **Pydantic v2**:

| Schema | Digunakan pada |
|---|---|
| `RegisterIn` | `POST /auth/register` — validasi role, EmailStr, min_length |
| `LoginIn` | `POST /auth/login` |
| `TokenOut` | Response login (access + refresh token) |
| `RefreshIn` / `AccessTokenOut` | `POST /auth/refresh` |
| `UserOut` | Response profil user |
| `UpdateProfileIn` | `PUT /auth/me` — semua field optional |
| `CourseIn` | `POST /courses` — title min 3 char, description min 10 char |
| `CourseUpdateIn` | `PATCH /courses/{id}` — semua field optional |
| `CourseOut` / `CourseListOut` | Response detail & list course |
| `PaginatedCourseOut` | Response list course dengan pagination |
| `CategoryOut` | Nested dalam CourseOut |
| `EnrollIn` | `POST /enrollments` |
| `EnrollmentOut` | Response enrollment |
| `ProgressIn` / `ProgressOut` | `POST /enrollments/{id}/progress` |
| `MessageOut` / `ErrorOut` | Generic response |

---

## Query Optimization

### Lab Endpoints (`/courses/lab/`)

Tersedia 3 pasang endpoint untuk membandingkan performa query sebelum dan sesudah optimasi:

| Endpoint | Masalah | Solusi |
|---|---|---|
| `/lab/course-list/baseline/` | N+1: 1 query/instruktur | `select_related('instructor', 'category')` |
| `/lab/course-members/baseline/` | N+1 reverse FK | `annotate(Count) + prefetch_related` |
| `/lab/course-dashboard/baseline/` | Loop Python untuk statistik | `aggregate / annotate` |

### Hasil Pengujian

- **Unoptimized**: **7 Queries** untuk 3 Course (N+1 Problem)
- **Optimized**: **2 Queries** (SQL JOIN via `select_related`)
- **Efisiensi**: Pengurangan ~71% jumlah query database

**Bukti Eksekusi Terminal:**
![Demo Query Optimization](img/demo_queri.png)

### Django Silk Profiling

Tersedia di **http://127.0.0.1:8000/silk/** — merekam 100% request beserta SQL query dan waktu eksekusi.

---

## Swagger UI Documentation

Swagger UI otomatis di-generate oleh Django Ninja dan dapat diakses di:

**➡️ http://127.0.0.1:8000/api/docs**

### Screenshot Swagger UI

![Swagger UI — Simple LMS REST API](img/swagger-ui.png)

### Cara Autentikasi di Swagger

1. Register via `POST /api/auth/register`
2. Login via `POST /api/auth/login` → salin `access_token` dari response
3. Klik tombol **🔒 Authorize** di pojok kanan atas Swagger
4. Masukkan: `Bearer <access_token>`
5. Semua endpoint protected kini bisa ditest langsung

---

## Cara Menjalankan Project

### A. Development Lokal (SQLite, tanpa Docker)

```bash
# 1. Clone repository
git clone https://github.com/Elenanda/simple_lms.git
cd simple_lms

# 2. Buat & aktifkan virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Jalankan migrasi
python manage.py migrate

# 5. (Opsional) Load data awal
python manage.py loaddata core/fixtures/initial_data.json

# 6. Buat superuser (role: admin)
python manage.py createsuperuser

# 7. Jalankan server
python manage.py runserver
```

**Akses:**
- Swagger API Docs: http://127.0.0.1:8000/api/docs
- Django Admin: http://127.0.0.1:8000/admin
- Silk Profiler: http://127.0.0.1:8000/silk

### B. Quick Test via cURL

```bash
# Register instructor
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"instr1","email":"i@test.com","password":"pass1234","role":"instructor"}'

# Login → dapatkan access_token
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"instr1","password":"pass1234"}'

# Buat course (sebagai instructor)
curl -X POST http://127.0.0.1:8000/api/courses \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Intro to Python","description":"Belajar Python dari dasar hingga OOP"}'

# List courses (publik, dengan pagination)
curl "http://127.0.0.1:8000/api/courses?page=1&page_size=5&search=python"
```

---

## Docker Setup

### Prasyarat

- Docker Desktop / Docker Engine terinstall
- Git

### Menjalankan dengan Docker

```bash
# 1. Salin file env
cp .env.example .env

# 2. Build dan jalankan semua container
docker-compose up --build -d

# 3. Jalankan migrasi di dalam container
docker-compose exec web python manage.py migrate

# 4. (Opsional) Buat superuser
docker-compose exec web python manage.py createsuperuser

# 5. Buka http://localhost:8000
```

### Status Container

**Status Container (Docker Compose):**
![Docker Container Status](img/Docker-Container-Status.png)
![Docker PS Details](img/docker-ps.png)

**Database Logs & Connection:**
![Database Logs](img/db-logs.png)

---

## Environment Variables

Salin `.env.example` menjadi `.env` dan sesuaikan:

```env
SECRET_KEY=your-very-secret-key-here
DEBUG=True

DB_NAME=simple_lms_db
DB_USER=lms_user
DB_PASSWORD=lms_password
DB_HOST=db
DB_PORT=5432
```

| Variable | Deskripsi |
|---|---|
| `SECRET_KEY` | Kunci rahasia Django (digunakan juga untuk signing JWT) |
| `DEBUG` | Mode development: `True` / `False` |
| `DB_HOST` | Jika di-set → gunakan PostgreSQL; jika kosong → SQLite |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Kredensial PostgreSQL |

> **Catatan:** Jika `DB_HOST` tidak di-set, project otomatis menggunakan SQLite untuk development lokal.

---

## Postman Collection

File collection tersedia di root project: **`simple_lms_api.postman_collection.json`**

### Import ke Postman

1. Buka Postman → **Import** → Upload File
2. Pilih `simple_lms_api.postman_collection.json`
3. Set environment variable: `base_url = http://127.0.0.1:8000`
4. Jalankan request **"Login"** → copy nilai `access_token`
5. Set environment variable: `token = <access_token>`
6. Semua request protected sudah otomatis menggunakan token

---

## Screenshots

### Django Admin Interface

![Django Admin Interface](img/django-admin-interface.png)
![Course Lesson Inline](img/Course-Lesson-Inline.png)

### Setup Environment

**Halaman Welcome Django (Localhost:8000):**
![Django Welcome](img/django-welcome.png)

---

## 📊 Project Summary

| Metrik | Nilai |
|---|---|
| Total API Endpoints | **13** |
| Pydantic Schemas | **16** |
| Django Models | **6** |
| Role Decorators | **4** (`is_admin`, `is_instructor`, `is_student`, `is_admin_or_instructor`) |
| Lab Query Endpoints | **6** (3 baseline + 3 optimized) |
| Query Reduction | **~71%** (7 queries → 2 queries) |
| Token Expiry (Access) | **60 menit** |
| Token Expiry (Refresh) | **7 hari** |
