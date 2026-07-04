"""
core/tests/test_auth_api.py
API test untuk endpoint Authentication:
  - POST /api/auth/register
  - POST /api/auth/login
  - POST /api/auth/refresh
  - POST /api/auth/logout
  - GET  /api/auth/me
  - PUT  /api/auth/me
  - RBAC: akses endpoint terbatas per role

Jalankan: python manage.py test core.tests.test_auth_api --verbosity=2
"""

import json
import bcrypt
from django.test import TestCase, Client
from core.models import User


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


BASE = "/api/auth"


class RegisterAPITest(TestCase):
    """Test endpoint POST /api/auth/register."""

    def setUp(self):
        self.client = Client()

    def test_register_success(self):
        """Registrasi berhasil dengan data valid."""
        resp = self.client.post(
            f"{BASE}/register",
            data=json.dumps({
                "username": "newuser",
                "email": "new@test.com",
                "password": "securepass",
                "role": "student",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["username"], "newuser")
        self.assertEqual(data["role"], "student")

    def test_register_duplicate_username(self):
        """Registrasi gagal jika username sudah ada."""
        User.objects.create(
            username="existing",
            email="existing@test.com",
            password=_hash("pass"),
        )
        resp = self.client.post(
            f"{BASE}/register",
            data=json.dumps({
                "username": "existing",
                "email": "other@test.com",
                "password": "somepass1",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_email(self):
        """Registrasi gagal jika email sudah terdaftar."""
        User.objects.create(
            username="userA",
            email="same@test.com",
            password=_hash("pass"),
        )
        resp = self.client.post(
            f"{BASE}/register",
            data=json.dumps({
                "username": "userB",
                "email": "same@test.com",
                "password": "somepass1",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_invalid_role(self):
        """Registrasi gagal jika role tidak valid."""
        resp = self.client.post(
            f"{BASE}/register",
            data=json.dumps({
                "username": "userrole",
                "email": "role@test.com",
                "password": "somepass1",
                "role": "superuser",  # invalid
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 422)

    def test_register_short_password(self):
        """Registrasi gagal jika password terlalu pendek."""
        resp = self.client.post(
            f"{BASE}/register",
            data=json.dumps({
                "username": "shortpass",
                "email": "shortpass@test.com",
                "password": "abc",  # < 8 chars
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 422)


class LoginAPITest(TestCase):
    """Test endpoint POST /api/auth/login."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="loginuser",
            email="login@test.com",
            password=_hash("correctpass"),
            role="student",
            is_active=True,
        )

    def test_login_success(self):
        """Login berhasil dengan kredensial yang benar."""
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "loginuser", "password": "correctpass"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_wrong_password(self):
        """Login gagal dengan password salah."""
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "loginuser", "password": "wrongpass"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_user(self):
        """Login gagal jika username tidak ditemukan."""
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "ghost", "password": "somepass"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_inactive_user(self):
        """Login gagal jika user dinonaktifkan."""
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "loginuser", "password": "correctpass"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class TokenRefreshTest(TestCase):
    """Test endpoint POST /api/auth/refresh."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="refreshuser",
            email="refresh@test.com",
            password=_hash("pass1234"),
            role="student",
            is_active=True,
        )
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "refreshuser", "password": "pass1234"}),
            content_type="application/json",
        )
        self.refresh_token = resp.json()["refresh_token"]

    def test_refresh_success(self):
        """Refresh token valid menghasilkan access token baru."""
        resp = self.client.post(
            f"{BASE}/refresh",
            data=json.dumps({"refresh_token": self.refresh_token}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.json())

    def test_refresh_invalid_token(self):
        """Refresh token tidak valid harus ditolak."""
        resp = self.client.post(
            f"{BASE}/refresh",
            data=json.dumps({"refresh_token": "this.is.invalid"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class MeAPITest(TestCase):
    """Test GET & PUT /api/auth/me."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="meuser",
            email="me@test.com",
            password=_hash("me1234pass"),
            role="student",
            is_active=True,
        )
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "meuser", "password": "me1234pass"}),
            content_type="application/json",
        )
        self.access_token = resp.json()["access_token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

    def test_get_me(self):
        """GET /me mengembalikan profil user yang sedang login."""
        resp = self.client.get(f"{BASE}/me", **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["username"], "meuser")
        self.assertEqual(data["role"], "student")

    def test_get_me_without_token(self):
        """GET /me tanpa token harus mengembalikan 401."""
        resp = self.client.get(f"{BASE}/me")
        self.assertEqual(resp.status_code, 401)

    def test_update_profile(self):
        """PUT /me berhasil mengupdate first_name dan last_name."""
        resp = self.client.put(
            f"{BASE}/me",
            data=json.dumps({"first_name": "Updated", "last_name": "Name"}),
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["first_name"], "Updated")
        self.assertEqual(data["last_name"], "Name")


class LogoutAPITest(TestCase):
    """Test POST /api/auth/logout + token blacklist."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="logoutuser",
            email="logout@test.com",
            password=_hash("logout1234"),
            role="student",
            is_active=True,
        )
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": "logoutuser", "password": "logout1234"}),
            content_type="application/json",
        )
        self.access_token = resp.json()["access_token"]
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

    def test_logout_success(self):
        """Logout berhasil mengembalikan 200 dengan pesan."""
        resp = self.client.post(f"{BASE}/logout", **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("berhasil", resp.json().get("message", "").lower())

    def test_logout_requires_auth(self):
        """Logout tanpa token harus ditolak (401)."""
        resp = self.client.post(f"{BASE}/logout")
        self.assertEqual(resp.status_code, 401)


class RBACBasicTest(TestCase):
    """Test bahwa role-based access control berjalan dengan benar."""

    def setUp(self):
        self.client = Client()
        # Buat user untuk tiap role
        for role in ("admin", "instructor", "student"):
            User.objects.create(
                username=f"rbac_{role}",
                email=f"rbac_{role}@test.com",
                password=_hash("rbac1234"),
                role=role,
                is_active=True,
            )

    def _login(self, role: str) -> str:
        resp = self.client.post(
            f"{BASE}/login",
            data=json.dumps({"username": f"rbac_{role}", "password": "rbac1234"}),
            content_type="application/json",
        )
        return resp.json()["access_token"]

    def test_admin_can_access_admin_dashboard(self):
        """Admin bisa akses /api/admin/dashboard."""
        token = self._login("admin")
        resp = self.client.get(
            "/api/admin/dashboard",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_admin_dashboard(self):
        """Student tidak bisa akses /api/admin/dashboard."""
        token = self._login("student")
        resp = self.client.get(
            "/api/admin/dashboard",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 403)

    def test_instructor_cannot_access_admin_dashboard(self):
        """Instructor tidak bisa akses /api/admin/dashboard."""
        token = self._login("instructor")
        resp = self.client.get(
            "/api/admin/dashboard",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 403)
