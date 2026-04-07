from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from core.models import Course

class Command(BaseCommand):
    help = 'Demonstrates N+1 query problem vs optimized queries'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n--- DEMO 1: N+1 PROBLEM (BAD PRACTICE) ---'))
        reset_queries() # Reset query count
        
        # Mengambil course TANPA optimasi
        unoptimized_courses = Course.objects.all()
        for course in unoptimized_courses:
            instructor = course.instructor.username # Memicu 1 query tambahan
            category = course.category.name if course.category else 'None' # Memicu 1 query tambahan
            self.stdout.write(f"Course: {course.title} | Instructor: {instructor}")
        
        bad_query_count = len(connection.queries)
        self.stdout.write(self.style.ERROR(f"Total Queries executed (Unoptimized): {bad_query_count}"))

        self.stdout.write(self.style.SUCCESS('\n--- DEMO 2: OPTIMIZED QUERIES (BEST PRACTICE) ---'))
        reset_queries()
        
        # Mengambil course DENGAN optimasi (memakai custom manager yang kita buat)
        optimized_courses = Course.objects.for_listing()
        for course in optimized_courses:
            instructor = course.instructor.username # Tidak memicu query baru! Data sudah di-join
            category = course.category.name if course.category else 'None' # Tidak memicu query baru!
            self.stdout.write(f"Course: {course.title} | Instructor: {instructor}")
            
        good_query_count = len(connection.queries)
        self.stdout.write(self.style.SUCCESS(f"Total Queries executed (Optimized): {good_query_count}"))
        self.stdout.write(self.style.SUCCESS(f"BERHASIL MENGHEMAT {bad_query_count - good_query_count} QUERIES!\n"))