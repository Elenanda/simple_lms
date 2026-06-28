# config/__init__.py
# Expose Celery app agar Django bisa auto-discover tasks
from .celery import app as celery_app

__all__ = ('celery_app',)
