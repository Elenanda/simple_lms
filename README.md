# Simple LMS - Dockerized Django Project

Project ini adalah setup environment development untuk Simple LMS menggunakan Docker, Django, dan PostgreSQL.

## Prasyarat
- Docker Desktop / Docker Engine terinstall
- Git

## Cara Menjalankan Project
1. Clone repository ini.
2. Gandakan file `.env.example` dan ubah namanya menjadi `.env`.
3. Buka terminal di direktori project, lalu jalankan perintah:
   `docker-compose up --build -d`
4. Jalankan migrasi database:
   `docker-compose exec web python manage.py migrate`
5. Buka `http://localhost:8000` di browser.

## Penjelasan Environment Variables
- `SECRET_KEY`: Kunci rahasia untuk keamanan instance Django.
- `DEBUG`: Mode development (True/False).
- `DB_*`: Kredensial untuk melakukan koneksi dari Django (web container) ke PostgreSQL (db container).

## Dokumentasi & Screenshot

### 1. Status Container (Docker PS)
Bukti bahwa ketiga container (web dan db) berjalan dengan baik:
![Screenshot Docker PS](img/docker-ps.png)

### 2. Halaman Welcome Django
Bukti bahwa Django bisa diakses melalui localhost:8000:
![Screenshot Welcome Django](img/django-welcome.png)

### 3. Log Terminal & Koneksi Database
Bukti bahwa server web berjalan tanpa pesan error dari PostgreSQL:
![Screenshot Log Terminal](img/db-logs.png)