"""
tasks/certificate_tasks.py
Celery Task: generate_certificate

Triggered: Saat student menyelesaikan SEMUA lesson dalam sebuah course
Output   : HTML certificate disimpan ke reports/certificates/
"""

import logging
import os
from datetime import datetime, timezone
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='tasks.certificate_tasks.generate_certificate',
    max_retries=2,
    default_retry_delay=30,
)
def generate_certificate(self, student_id: int, course_id: int):
    """
    Generate HTML certificate saat student menyelesaikan semua lesson.

    Args:
        student_id: ID student
        course_id : ID course yang diselesaikan
    Returns:
        dict berisi path file sertifikat
    """
    try:
        from core.models import User, Course

        student = User.objects.get(pk=student_id)
        course  = Course.objects.select_related('instructor').get(pk=course_id)

        issued_at = datetime.now(timezone.utc)
        cert_id   = f"LMS-{course_id:04d}-{student_id:04d}-{issued_at.strftime('%Y%m%d')}"

        html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Certificate — {cert_id}</title>
  <style>
    body {{ font-family: 'Georgia', serif; background: #f5f0e8; display: flex;
           justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
    .cert {{ background: white; border: 8px double #b8960c; padding: 60px;
             max-width: 800px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }}
    h1 {{ color: #b8960c; font-size: 2.5rem; margin-bottom: 0.5rem; }}
    .subtitle {{ color: #666; font-size: 1.1rem; margin-bottom: 2rem; }}
    .student-name {{ font-size: 2rem; color: #1a1a2e; font-weight: bold;
                     border-bottom: 2px solid #b8960c; padding-bottom: 0.5rem; }}
    .course-title {{ font-size: 1.4rem; color: #2d6a4f; margin: 1.5rem 0; }}
    .meta {{ color: #888; font-size: 0.9rem; margin-top: 2rem; }}
    .cert-id {{ font-family: monospace; color: #aaa; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <div class="cert">
    <h1>🎓 Certificate of Completion</h1>
    <p class="subtitle">Simple Learning Management System</p>
    <p>This certifies that</p>
    <p class="student-name">{student.get_full_name() or student.username}</p>
    <p>has successfully completed the course</p>
    <p class="course-title">"{course.title}"</p>
    <p>taught by <strong>{course.instructor.get_full_name() or course.instructor.username}</strong></p>
    <div class="meta">
      <p>Issued on: {issued_at.strftime('%d %B %Y')}</p>
      <p class="cert-id">Certificate ID: {cert_id}</p>
    </div>
  </div>
</body>
</html>"""

        # Pastikan direktori ada
        cert_dir = os.path.join(settings.REPORTS_DIR, 'certificates')
        os.makedirs(cert_dir, exist_ok=True)

        filename = f"{cert_id}.html"
        filepath = os.path.join(cert_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Log ke MongoDB
        from services.mongodb import log_analytics
        log_analytics(
            event_type="COURSE_COMPLETE",
            course_id=course_id,
            student_id=student_id,
            data={"certificate_id": cert_id, "file": filename},
        )

        logger.info(f"[CERT] Generated → {cert_id}")
        return {"status": "generated", "certificate_id": cert_id, "file": filepath}

    except Exception as exc:
        logger.error(f"[CERT] Failed to generate certificate: {exc}")
        raise self.retry(exc=exc)
