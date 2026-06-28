# Cache Report — Redis Caching Lab

**Nama Lab:** Implementasi Caching Sederhana dengan Redis  
**Tanggal:** 28 Juni 2026  
**Stack:** Python 3.x · Redis 7 (Docker) · redis-py 5.0.8

---

## 1. Screenshot Hasil Test

### Hasil Eksekusi `test_cache.py`

```
=======================================================
  REDIS CACHING DEMO -- Simple LMS Lab
=======================================================
  [OK] Redis terhubung di localhost:6379

-------------------------------------------------------
  TEST 1: First Call -- Jakarta (Cache MISS)
-------------------------------------------------------
  [CACHE MISS] key='weather:jakarta' | Memanggil API (tunggu 2s)...
  [CACHED]     key='weather:jakarta' | TTL: 300s (5 menit)

  Response time: 2.003 detik   <-- LAMBAT (API call)

-------------------------------------------------------
  TEST 2: Second Call -- Jakarta (Cache HIT)
-------------------------------------------------------
  [CACHE HIT] key='weather:jakarta' | TTL tersisa: 300s
     Sumber    : CACHE

  Response time: 0.0020 detik  <-- CEPAT (dari Redis)

-------------------------------------------------------
  RINGKASAN PERFORMA
-------------------------------------------------------
  1. Jakarta - 1st call (API)    2.003s   API (slow)
  2. Jakarta - 2nd call (Redis)  0.0020s  CACHE (fast)
  3. Bali    - 1st call (API)    2.003s   API (slow)
  4. Bali    - 2nd call (Redis)  0.0011s  CACHE (fast)
-------------------------------------------------------
  Speed-up   : ~1003x lebih cepat dengan cache
  Cache TTL  : 300 detik (5 menit)
```

### Visualisasi Performa

```
Response Time Comparison:

API Call    ████████████████████  2.003s
Cache HIT   ░                     0.002s  (~1003x lebih cepat!)
```

---

## 2. Kode yang Dimodifikasi

### Versi ASLI (tanpa cache)

```python
import requests
import time

def get_weather(city):
    """Simulasi API call yang lambat"""
    time.sleep(2)  # Simulate slow API
    response = requests.get(f"https://api.example.com/weather/{city}")
    return response.json()

# Problem: Setiap panggil get_weather() butuh 2 detik
```

### Versi MODIFIKASI (dengan Redis Cache)

```python
import redis
import json
import time

# Konfigurasi Redis
redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
CACHE_TTL = 300  # 5 menit = 300 detik

def get_weather(city: str) -> dict:
    """
    Get weather dengan Redis caching -- Cache-Aside Pattern.

    Flow:
    1. Cek Redis cache (GET)
    2. Cache HIT  -> return dari Redis (cepat ~0.002s)
    3. Cache MISS -> panggil API (lambat ~2s)
                  -> simpan ke Redis (SETEX)
                  -> return data
    """
    cache_key = f"weather:{city.lower()}"

    # LANGKAH 1: CEK CACHE (Redis GET)
    cached_value = redis_client.get(cache_key)
    if cached_value is not None:
        print(f"  [CACHE HIT] '{city}' diambil dari Redis")
        return json.loads(cached_value)

    # LANGKAH 2: CACHE MISS -- panggil API
    print(f"  [CACHE MISS] Memanggil API untuk '{city}'...")
    time.sleep(2)  # Simulasi API lambat
    data = {"city": city, "temp_c": 32, "condition": "Sunny"}

    # LANGKAH 3: SIMPAN KE CACHE (Redis SETEX = SET + EXPIRE)
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
    print(f"  [CACHED] Disimpan selama {CACHE_TTL}s")

    return data
```

---

## 3. Redis Commands yang Digunakan

### Referensi Lengkap

| Command | Syntax | Fungsi | Contoh |
|---|---|---|---|
| **GET** | `GET key` | Ambil nilai dari Redis | `GET weather:jakarta` |
| **SET** | `SET key value` | Simpan nilai (tanpa expiry) | `SET weather:jakarta "{...}"` |
| **SETEX** | `SETEX key seconds value` | Simpan + set TTL sekaligus | `SETEX weather:jakarta 300 "{...}"` |
| **TTL** | `TTL key` | Sisa waktu expire (detik) | `TTL weather:jakarta` -> `298` |
| **EXISTS** | `EXISTS key` | Cek apakah key ada | `EXISTS weather:jakarta` -> `1` |
| **EXPIRE** | `EXPIRE key seconds` | Update TTL key yang ada | `EXPIRE weather:jakarta 300` |
| **DEL** | `DEL key` | Hapus key (cache invalidation) | `DEL weather:jakarta` |
| **KEYS** | `KEYS pattern` | Cari semua key yang cocok | `KEYS weather:*` |

### Bukti Eksekusi Redis Commands

```
> KEYS weather:*
  weather:bali
  weather:jakarta

> GET weather:jakarta
  {"city": "Jakarta", "temp_c": 32, "humidity": 85,
   "condition": "Partly Cloudy", "fetched_at": "19:25:26"}

> TTL weather:jakarta
  298 detik (4m 58s tersisa)

> EXISTS weather:jakarta
  1  (1=ada, 0=tidak ada)

> EXPIRE weather:jakarta 1
> GET weather:jakarta  (1.5 detik kemudian)
  None  <-- sudah expired, hilang dari Redis
```

---

## 4. Jawaban Pertanyaan Refleksi

### Q1: Kenapa Response Time Berbeda?

Response time berbeda karena **lokasi pengambilan data** yang berbeda:

| Kondisi | Lokasi Data | Proses | Waktu |
|---|---|---|---|
| **Cache MISS** | External API (via internet) | HTTP request + server processing + transfer | ~2 detik |
| **Cache HIT** | Redis (RAM lokal server) | GET dari memory + JSON parse | ~0.002 detik |

**Analogi:** Cache seperti "catatan di meja belajar". Pertama kali harus buka buku (lambat), tapi setelah dicatat di kertas, berikutnya tinggal lihat catatan (cepat). Redis menyimpan data di **RAM** yang aksesnya ~1000x lebih cepat dari network call.

---

### Q2: Apa Keuntungan Caching?

| Keuntungan | Penjelasan | Dampak Nyata |
|---|---|---|
| **Performa** | Data dari RAM ~1000x lebih cepat dari API call | Halaman load lebih cepat |
| **Mengurangi Beban API** | External API tidak dipanggil setiap request | Hemat kuota/biaya API berbayar |
| **Skalabilitas** | 1 cache entry melayani ribuan user sekaligus | Sistem tahan lonjakan traffic |
| **Reliabilitas** | Jika API eksternal down, cache tetap melayani | Availability meningkat |
| **Efisiensi Biaya** | Kurang API call = kurang biaya infrastruktur | Cost reduction |

**Contoh nyata:**
- **Twitter/X**: Tweet viral di-cache agar tidak query DB jutaan kali
- **Netflix**: Thumbnail dan metadata film di-cache di Redis
- **Tokopedia**: Harga produk di-cache agar halaman load cepat

---

### Q3: Kapan Sebaiknya TIDAK Menggunakan Cache?

| Situasi | Alasan | Solusi |
|---|---|---|
| **Data real-time kritis** | Harga saham, saldo rekening - data stale = kerugian | Query DB langsung |
| **Data personal/privat** | Risiko user A mendapat data user B jika key tidak unik | Gunakan user-specific key atau skip cache |
| **Data yang sering berubah** | TTL 5 menit, data ganti tiap detik = selalu stale | Turunkan TTL atau skip cache |
| **Data sekali pakai** | OTP, CSRF token - tidak ada manfaat cache | Simpan di session/DB langsung |
| **Query DB sudah cepat** | Jika DB sudah <5ms (dengan index), overhead cache tidak worthit | Optimasi DB index saja |
| **RAM terbatas** | Cache terlalu banyak item = Redis makan RAM besar | Pilih data yang benar-benar sering diakses |

**Prinsip:**
```
Cocok untuk cache : Data SERING dibaca + JARANG berubah + BUKAN sensitif
Hindari cache     : Data REAL-TIME + PERSONAL + SERING berubah
```

---

## 5. Arsitektur Cache-Aside Pattern

```
Request get_weather("Jakarta")
         |
         v
   [Cek Redis GET]
         |
    Ada di cache? --- YES ---> Return data (0.002s) [CACHE HIT]
         |
        NO [CACHE MISS]
         |
         v
   [Panggil API Eksternal]
   time.sleep(2) -- simulasi network latency
         |
         v
   [SETEX key 300 data]  -- simpan ke Redis + set TTL
         |
         v
   Return data (2.003s)
```

---

## 6. Cara Menjalankan

```bash
# 1. Start Redis via Docker
docker-compose up redis -d

# 2. Verifikasi Redis berjalan
docker exec simple-lms-redis-1 redis-cli ping
# Output: PONG

# 3. Jalankan test
python redis_lab/test_cache.py

# 4. Monitor Redis secara real-time (terminal terpisah)
docker exec -it simple-lms-redis-1 redis-cli MONITOR
```

---

## 7. Kesimpulan

Implementasi Redis caching berhasil mengurangi response time dari **~2.003 detik** menjadi **~0.002 detik** - peningkatan **~1003x** untuk repeated calls.

Key takeaways:
- `SETEX` adalah command paling penting: simpan data + set TTL dalam satu operasi
- Cache-Aside (check -> miss -> fetch -> store) adalah pola caching paling umum
- TTL (Time-To-Live) kritis agar data cache tidak menjadi stale selamanya
- Graceful degradation penting: jika Redis mati, sistem harus tetap berjalan (hanya lebih lambat)
