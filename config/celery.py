"""
config/celery.py
Konfigurasi Celery untuk Simple LMS
- Broker : RabbitMQ  (AMQP)
- Backend: Redis     (task results)
- Beat   : Scheduled tasks (update_course_statistics tiap 30 menit)
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('simple_lms')

# Baca konfigurasi dari django settings dengan prefix CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks di dalam folder tasks/
app.autodiscover_tasks(['tasks'])


# ─────────────────────────────────────────────
# Beat Schedule — Periodic Tasks
# ─────────────────────────────────────────────
app.conf.beat_schedule = {
    # Update statistik enrollment tiap 30 menit
    'update-course-statistics-every-30min': {
        'task': 'tasks.stats_tasks.update_course_statistics',
        'schedule': crontab(minute='*/30'),
        'args': (),
    },
}

app.conf.timezone = 'UTC'
