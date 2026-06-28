"""
redis_lab/weather_api.py
Implementasi Redis Caching untuk simulasi Weather API

Modul ini mendemonstrasikan:
  - Operasi Redis: SET, GET, SETEX, EXISTS, TTL, DELETE
  - Cache-aside pattern (lazy loading)
  - Cache expiry (TTL 5 menit)
  - Pengurangan response time dari ~2s → <0.01s
"""

import json
import time
import redis

# ─────────────────────────────────────────────
# Konfigurasi Redis
# ─────────────────────────────────────────────
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB   = 1          # Gunakan DB=1 agar tidak bentrok dengan Django
CACHE_TTL  = 300        # 5 menit dalam detik

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,  # Otomatis decode bytes → str
        socket_connect_timeout=3,
    )
    redis_client.ping()  # Test koneksi saat import
    REDIS_AVAILABLE = True
except (redis.ConnectionError, redis.TimeoutError):
    REDIS_AVAILABLE = False
    print("⚠️  Redis tidak tersedia — caching dinonaktifkan (graceful fallback)")


# ─────────────────────────────────────────────
# Simulasi Data Cuaca
# (Menggantikan api.example.com yang tidak nyata)
# ─────────────────────────────────────────────
_MOCK_WEATHER_DB = {
    "jakarta":  {"city": "Jakarta",  "temp_c": 32, "humidity": 85, "condition": "Partly Cloudy", "wind_kmh": 15},
    "surabaya": {"city": "Surabaya", "temp_c": 34, "humidity": 78, "condition": "Sunny",         "wind_kmh": 20},
    "bandung":  {"city": "Bandung",  "temp_c": 22, "humidity": 92, "condition": "Rainy",          "wind_kmh": 8},
    "bali":     {"city": "Bali",     "temp_c": 30, "humidity": 80, "condition": "Clear Sky",      "wind_kmh": 18},
    "medan":    {"city": "Medan",    "temp_c": 29, "humidity": 88, "condition": "Thunderstorm",   "wind_kmh": 25},
    "yogyakarta": {"city": "Yogyakarta", "temp_c": 28, "humidity": 82, "condition": "Cloudy",    "wind_kmh": 12},
}


def _fetch_from_api(city: str) -> dict:
    """
    Simulasi HTTP call ke external API yang lambat.
    Delay 2 detik mensimulasikan latency jaringan + waktu proses server.

    Di dunia nyata ini akan berupa:
        response = requests.get(f"https://api.example.com/weather/{city}")
        return response.json()
    """
    time.sleep(2)  # ← Simulasi slow network / API processing

    city_key = city.lower().strip()
    if city_key in _MOCK_WEATHER_DB:
        data = _MOCK_WEATHER_DB[city_key].copy()
    else:
        data = {
            "city":      city,
            "temp_c":    28,
            "humidity":  75,
            "condition": "Data tidak tersedia",
            "wind_kmh":  10,
        }

    data["fetched_at"] = time.strftime("%H:%M:%S")
    data["source"]     = "API"
    return data


# ─────────────────────────────────────────────
# Fungsi Utama: get_weather() dengan Caching
# ─────────────────────────────────────────────
def get_weather(city: str) -> dict:
    """
    Ambil data cuaca kota dengan strategi cache-aside (lazy caching).

    Alur:
      1. Bangun cache key  → "weather:{city_lowercase}"
      2. GET dari Redis    → jika ada, return (CACHE HIT)
      3. Jika tidak ada   → panggil API (lambat)
      4. SETEX ke Redis   → simpan hasil dengan TTL 300s
      5. Return data

    Args:
        city: Nama kota (contoh: "Jakarta", "Bali")

    Returns:
        dict berisi data cuaca
    """
    cache_key = f"weather:{city.lower().strip()}"

    # ── LANGKAH 1: CEK REDIS (GET) ──────────────────
    if REDIS_AVAILABLE:
        cached_value = redis_client.get(cache_key)      # Operasi: GET

        if cached_value is not None:
            # ✅ CACHE HIT — data ada di Redis
            remaining_ttl = redis_client.ttl(cache_key) # Operasi: TTL
            data = json.loads(cached_value)
            data["source"]        = "CACHE"
            data["cache_ttl_left"] = f"{remaining_ttl}s"
            print(f"  ✅ CACHE HIT  | key='{cache_key}' | TTL tersisa: {remaining_ttl}s")
            return data

    # ── LANGKAH 2: CACHE MISS — panggil API ─────────
    print(f"  ❌ CACHE MISS | key='{cache_key}' | Memanggil API (tunggu 2s)...")
    data = _fetch_from_api(city)

    # ── LANGKAH 3: SIMPAN KE REDIS (SETEX) ──────────
    if REDIS_AVAILABLE:
        redis_client.setex(                              # Operasi: SETEX (SET + EXPIRE)
            name=cache_key,
            time=CACHE_TTL,
            value=json.dumps(data),
        )
        print(f"  💾 CACHED     | key='{cache_key}' | TTL: {CACHE_TTL}s ({CACHE_TTL//60} menit)")

    return data


# ─────────────────────────────────────────────
# Helper Functions (untuk demo Redis commands)
# ─────────────────────────────────────────────
def cache_info(city: str) -> None:
    """Tampilkan info cache untuk sebuah kota."""
    if not REDIS_AVAILABLE:
        print("Redis tidak tersedia.")
        return

    key = f"weather:{city.lower()}"
    exists = redis_client.exists(key)     # Operasi: EXISTS
    ttl    = redis_client.ttl(key)        # Operasi: TTL

    print(f"\n  📊 Cache Info untuk '{city}':")
    print(f"     Key    : {key}")
    print(f"     Exists : {'Ya' if exists else 'Tidak'}")
    print(f"     TTL    : {ttl}s ({ttl//60}m {ttl%60}s tersisa)" if ttl > 0 else f"     TTL    : key tidak ada / expired")


def invalidate_cache(city: str) -> bool:
    """Hapus cache untuk sebuah kota (cache invalidation)."""
    if not REDIS_AVAILABLE:
        return False
    key = f"weather:{city.lower()}"
    deleted = redis_client.delete(key)    # Operasi: DELETE
    print(f"  🗑️  Cache '{key}' {'dihapus' if deleted else 'tidak ditemukan'}")
    return bool(deleted)


def list_all_cache_keys() -> list:
    """Tampilkan semua cache key cuaca yang aktif."""
    if not REDIS_AVAILABLE:
        return []
    keys = redis_client.keys("weather:*")  # Operasi: KEYS pattern
    return keys
