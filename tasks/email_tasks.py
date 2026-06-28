"""
tasks/email_tasks.py
Celery Task: send_enrollment_email

Triggered: Saat student berhasil enroll ke sebuah course
Queue    : default
"""

import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='tasks.email_tasks.send_enrollment_email',
    max_retries=3,
    default_retry_delay=60,  # retry setelah 60 detik
)
def send_enrollment_email(self, student_id: int, course_id: int):
    """
    Kirim email konfirmasi enrollment ke student.

    Args:
        student_id: ID user dengan role student
        course_id : ID course yang di-enroll
    """
    import django
    django.setup()

    try:
        from core.models import User, Course
        student = User.objects.get(pk=student_id)
        course  = Course.objects.select_related('instructor').get(pk=course_id)

        subject = f"🎓 Enrollment Confirmed: {course.title}"
        body = f"""Halo {student.first_name or student.username},

Selamat! Kamu berhasil terdaftar di course berikut:

  📚 Course  : {course.title}
  👨‍🏫 Instructor: {course.instructor.get_full_name() or course.instructor.username}
  📅 Terdaftar: {__import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M')} WIB

Segera mulai belajar dan raih sertifikatmu!

Salam,
Tim Simple LMS
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )
        email.send(fail_silently=False)

        logger.info(f"[EMAIL] Enrollment email sent → user={student_id}, course={course_id}")
        return {"status": "sent", "to": student.email, "course": course.title}

    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send enrollment email: {exc}")
        raise self.retry(exc=exc)
