"""
services/cache.py
Redis Caching Helpers untuk Simple LMS

Strategi:
  - Course List   → TTL 5 menit  | key: lms:course_list:{hash_params}
  - Course Detail → TTL 10 menit | key: lms:course_detail:{id}
  - Invalidasi    → delete by key + delete_pattern untuk list keys
"""

import hashlib
from django.core.cache import cache

# ─── TTL Constants ──────────────────────────────
COURSE_LIST_TTL   = 60 * 5   # 5 menit
COURSE_DETAIL_TTL = 60 * 10  # 10 menit


# ─── Key Builders ───────────────────────────────
def _course_list_key(page: int, page_size: int, search, category_id, instructor_id) -> str:
    """Hash seluruh filter params menjadi satu cache key."""
    raw = f"{page}:{page_size}:{search}:{category_id}:{instructor_id}"
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"course_list:{h}"


def _course_detail_key(course_id: int) -> str:
    return f"course_detail:{course_id}"


# ─── Get / Set ──────────────────────────────────
def get_course_list(page, page_size, search, category_id, instructor_id):
    """Return cached course list dict atau None jika cache miss."""
    key = _course_list_key(page, page_size, search, category_id, instructor_id)
    return cache.get(key)


def set_course_list(page, page_size, search, category_id, instructor_id, data: dict):
    """Simpan course list dict ke Redis."""
    key = _course_list_key(page, page_size, search, category_id, instructor_id)
    cache.set(key, data, timeout=COURSE_LIST_TTL)


def get_course_detail(course_id: int):
    """Return cached course detail dict atau None jika cache miss."""
    return cache.get(_course_detail_key(course_id))


def set_course_detail(course_id: int, data: dict):
    """Simpan course detail dict ke Redis."""
    cache.set(_course_detail_key(course_id), data, timeout=COURSE_DETAIL_TTL)


# ─── Invalidation ───────────────────────────────
def invalidate_course_detail(course_id: int):
    """Hapus cache detail satu course."""
    cache.delete(_course_detail_key(course_id))


def invalidate_all_course_lists():
    """
    Hapus seluruh list-cache menggunakan delete_pattern (fitur django-redis).
    KEY_PREFIX 'lms' ditambahkan otomatis oleh django-redis → pattern: lms:course_list:*
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        # Pola dengan prefix yang ditambahkan django-redis
        pattern = "*course_list:*"
        keys = conn.keys(pattern)
        if keys:
            conn.delete(*keys)
    except Exception:
        # Fallback: tidak ada yang dilakukan jika Redis tidak tersedia
        pass


def invalidate_course(course_id: int):
    """Shortcut: hapus detail + semua list cache untuk satu course."""
    invalidate_course_detail(course_id)
    invalidate_all_course_lists()
