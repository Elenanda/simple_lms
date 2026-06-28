"""
tasks/report_tasks.py
Celery Task: export_course_report (Async CSV Export)

Triggered: POST /api/reports/courses/{course_id}
Output   : CSV file disimpan ke reports/exports/
"""

import csv
import logging
import os
from datetime import datetime, timezone
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='tasks.report_tasks.export_course_report',
    max_retries=2,
    default_retry_delay=30,
)
def export_course_report(self, course_id: int, requested_by_id: int):
    """
    Generate CSV report untuk satu course secara asynchronous.
    Berisi: daftar students, progress per lesson, tanggal enroll.

    Args:
        course_id       : ID course yang akan di-export
        requested_by_id : ID user yang request (untuk logging)
    Returns:
        dict berisi path file CSV dan jumlah rows
    """
    try:
        from core.models import Course, Enrollment, Progress

        course = Course.objects.prefetch_related(
            'lessons', 'enrollments__student', 'enrollments'
        ).get(pk=course_id)

        lessons    = list(course.lessons.order_by('order'))
        enrollments = list(
            course.enrollments
            .select_related('student')
            .prefetch_related('student__progress')
            .order_by('enrolled_at')
        )

        # Buat direktori exports
        export_dir = os.path.join(settings.REPORTS_DIR, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename  = f"course_{course_id}_report_{timestamp}.csv"
        filepath  = os.path.join(export_dir, filename)

        # Header CSV: student info + kolom per lesson
        headers = [
            'Student ID', 'Username', 'Email',
            'Enrolled At', 'Lessons Completed', 'Total Lessons', 'Progress %',
        ] + [f'Lesson: {l.title[:30]}' for l in lessons]

        rows_written = 0
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for enrollment in enrollments:
                student = enrollment.student
                progress_qs = Progress.objects.filter(
                    student=student,
                    lesson__course=course,
                    is_completed=True,
                ).values_list('lesson_id', flat=True)
                completed_ids = set(progress_qs)

                completed_count = len(completed_ids)
                total_count     = len(lessons)
                pct             = round(completed_count / total_count * 100, 1) if total_count else 0

                row = [
                    student.pk,
                    student.username,
                    student.email,
                    enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M'),
                    completed_count,
                    total_count,
                    f"{pct}%",
                ] + ['✓' if l.pk in completed_ids else '✗' for l in lessons]

                writer.writerow(row)
                rows_written += 1

        # Log activity
        from services.mongodb import log_activity
        log_activity(
            user_id=requested_by_id,
            action="EXPORT_REPORT",
            resource_type="course",
            resource_id=course_id,
            metadata={"file": filename, "rows": rows_written},
        )

        logger.info(f"[REPORT] CSV generated → {filename} ({rows_written} rows)")
        return {
            "status":   "completed",
            "file":     filename,
            "rows":     rows_written,
            "course":   course.title,
        }

    except Exception as exc:
        logger.error(f"[REPORT] Failed to export course {course_id}: {exc}")
        raise self.retry(exc=exc)
