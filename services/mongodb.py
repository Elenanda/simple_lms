"""
services/mongodb.py
MongoDB Connection Pool + Activity Logging Helpers

Collections:
  activity_logs      → setiap aksi user (register, login, enroll, dll)
  learning_analytics → event belajar (progress, course complete, dll)
"""

from datetime import datetime, timezone
from typing import Optional

from django.conf import settings

# ─── Singleton Connection Pool ───────────────────
_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from pymongo import MongoClient
            _client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000,  # Timeout 3 detik
                connectTimeoutMS=3000,
            )
        except Exception:
            return None
    return _client


def get_db():
    """Return MongoDB database instance atau None jika koneksi gagal."""
    client = _get_client()
    if client is None:
        return None
    return client[settings.MONGODB_DB]


# ─── Activity Log ────────────────────────────────
def log_activity(
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """
    Catat aktivitas user ke collection activity_logs.

    Contoh penggunaan:
        log_activity(user_id=1, action="LOGIN", resource_type="auth")
        log_activity(user_id=2, action="ENROLL", resource_type="course", resource_id=5)
    """
    db = get_db()
    if db is None:
        return  # Graceful degrade jika MongoDB tidak tersedia

    db.activity_logs.insert_one({
        "user_id":       user_id,
        "action":        action,           # "LOGIN", "REGISTER", "ENROLL", "CREATE_COURSE", dll
        "resource_type": resource_type,    # "auth", "course", "enrollment", "progress"
        "resource_id":   resource_id,
        "metadata":      metadata or {},
        "ip_address":    ip_address,
        "timestamp":     datetime.now(timezone.utc),
    })


# ─── Learning Analytics ──────────────────────────
def log_analytics(
    event_type: str,
    course_id: int,
    student_id: int,
    data: Optional[dict] = None,
):
    """
    Catat event analytics ke collection learning_analytics.

    event_type: "LESSON_COMPLETE", "COURSE_COMPLETE", "PROGRESS_UPDATE"
    """
    db = get_db()
    if db is None:
        return

    db.learning_analytics.insert_one({
        "event_type":  event_type,
        "course_id":   course_id,
        "student_id":  student_id,
        "data":        data or {},
        "timestamp":   datetime.now(timezone.utc),
    })


# ─── Aggregation Reports ─────────────────────────
def get_course_activity_summary(course_id: int) -> dict:
    """
    Aggregasi: hitung total enroll, lesson complete, dan unique students per course.
    Return dict kosong jika MongoDB tidak tersedia.
    """
    db = get_db()
    if db is None:
        return {}

    pipeline = [
        {"$match": {"course_id": course_id}},
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1},
            "unique_students": {"$addToSet": "$student_id"},
        }},
        {"$project": {
            "event_type": "$_id",
            "count": 1,
            "unique_student_count": {"$size": "$unique_students"},
        }},
    ]
    results = list(db.learning_analytics.aggregate(pipeline))
    return {r["event_type"]: {"count": r["count"], "students": r["unique_student_count"]}
            for r in results}


def get_recent_activities(limit: int = 50) -> list:
    """Ambil N activity log terbaru (untuk admin dashboard)."""
    db = get_db()
    if db is None:
        return []
    return list(
        db.activity_logs
        .find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
