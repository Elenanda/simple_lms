"""
tasks/stats_tasks.py
Celery Task: update_course_statistics (Scheduled / Periodic)

Schedule: Tiap 30 menit via Celery Beat (config/celery.py)
Fungsi  : Hitung enrollment count per course dan simpan ke Redis cache
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name='tasks.stats_tasks.update_course_statistics',
    ignore_result=False,
)
def update_course_statistics():
    """
    Hitung ulang statistik enrollment untuk semua course aktif,
    lalu simpan hasilnya ke Redis.

    Dipanggil tiap 30 menit oleh Celery Beat.
    Returns:
        dict berisi jumlah course yang diupdate
    """
    from django.core.cache import cache
    from django.db.models import Count
    from core.models import Course

    courses = (
        Course.objects
        .annotate(enrollment_count=Count('enrollments'))
        .values('id', 'title', 'enrollment_count')
    )

    updated = 0
    for course in courses:
        key = f"stats:course:{course['id']}:enrollment_count"
        cache.set(key, course['enrollment_count'], timeout=60 * 35)  # TTL 35 menit
        updated += 1

    # Simpan juga summary terakhir
    cache.set('stats:last_updated', __import__('datetime').datetime.utcnow().isoformat(), timeout=60 * 60)

    logger.info(f"[STATS] Updated enrollment stats for {updated} courses")
    return {"updated_courses": updated, "status": "ok"}


def get_course_enrollment_stat(course_id: int):
    """
    Helper: ambil cached enrollment count untuk satu course.
    Return None jika belum di-cache (akan dihitung pada beat berikutnya).
    """
    from django.core.cache import cache
    return cache.get(f"stats:course:{course_id}:enrollment_count")
