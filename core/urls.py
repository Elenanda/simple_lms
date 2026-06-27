"""
URL Routing untuk Lab Praktikum Optimasi Query Django
App: core (mapped ke prefix /courses/ di config/urls.py)

Endpoint Lab:
  /courses/lab/course-list/baseline/      → N+1 demo (Course + Instructor)
  /courses/lab/course-list/optimized/     → select_related fix
  /courses/lab/course-members/baseline/   → reverse FK N+1 demo
  /courses/lab/course-members/optimized/  → annotate + prefetch fix
  /courses/lab/course-dashboard/baseline/ → loop Python stats demo
  /courses/lab/course-dashboard/optimized/→ aggregate/annotate fix
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # --------------------------------------------------------
    # Endpoint 1: Course List + Instructor
    # --------------------------------------------------------
    path(
        'lab/course-list/baseline/',
        views.course_list_baseline,
        name='course-list-baseline',
    ),
    path(
        'lab/course-list/optimized/',
        views.course_list_optimized,
        name='course-list-optimized',
    ),

    # --------------------------------------------------------
    # Endpoint 2: Course + Members + Lessons + Progress
    # --------------------------------------------------------
    path(
        'lab/course-members/baseline/',
        views.course_members_baseline,
        name='course-members-baseline',
    ),
    path(
        'lab/course-members/optimized/',
        views.course_members_optimized,
        name='course-members-optimized',
    ),

    # --------------------------------------------------------
    # Endpoint 3: Dashboard Statistik Dosen
    # --------------------------------------------------------
    path(
        'lab/course-dashboard/baseline/',
        views.course_dashboard_baseline,
        name='course-dashboard-baseline',
    ),
    path(
        'lab/course-dashboard/optimized/',
        views.course_dashboard_optimized,
        name='course-dashboard-optimized',
    ),
]
