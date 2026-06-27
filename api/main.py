"""
api/main.py
Entry-point Django Ninja API
- Mendaftarkan semua router
- Konfigurasi Swagger UI di /api/docs
"""

from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError

from api.routers.auth_router import router as auth_router
from api.routers.course_router import router as course_router
from api.routers.enrollment_router import router as enrollment_router

# ─────────────────────────────────────────────
# Inisialisasi NinjaAPI
# ─────────────────────────────────────────────
api = NinjaAPI(
    title="Simple LMS REST API",
    version="1.0.0",
    description="""
## 🎓 Simple LMS REST API

REST API lengkap untuk Learning Management System dengan:

- **JWT Authentication** — Access + Refresh token
- **Role-Based Access Control** — Admin, Instructor, Student
- **Pagination & Filtering** — Pada endpoint listing course
- **Ownership Validation** — Instructor hanya bisa edit course miliknya sendiri

### 🔐 Cara Autentikasi
1. Register via `POST /api/auth/register`
2. Login via `POST /api/auth/login` → dapatkan `access_token`
3. Klik tombol **Authorize** di atas, masukkan: `Bearer <access_token>`
4. Semua endpoint protected kini bisa diakses
    """,
    docs_url="/docs",
)

# ─────────────────────────────────────────────
# Daftarkan Router
# ─────────────────────────────────────────────
api.add_router("/auth", auth_router)
api.add_router("/courses", course_router)
api.add_router("/enrollments", enrollment_router)


# ─────────────────────────────────────────────
# Custom Error Handlers
# ─────────────────────────────────────────────
@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    return api.create_response(
        request,
        {"detail": exc.errors},
        status=422,
    )
