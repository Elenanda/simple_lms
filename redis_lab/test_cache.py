# -*- coding: utf-8 -*-
"""
redis_lab/test_cache.py
Testing Script -- Demonstrasi Redis Caching Performance

Jalankan dengan:
    python redis_lab/test_cache.py

Persyaratan Redis:
    Opsi A (Docker):  docker-compose up redis -d
    Opsi B (Lokal):   redis-server
"""

import sys
import os
import time
import io

# Fix encoding untuk Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Tambah parent directory ke path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weather_api import (
    get_weather,
    cache_info,
    invalidate_cache,
    list_all_cache_keys,
    REDIS_AVAILABLE,
    CACHE_TTL,
)

# ─────────────────────────────────────────────
# Utilitas
# ─────────────────────────────────────────────
SEP  = "-" * 55
SEP2 = "=" * 55

def print_result(data: dict):
    print(f"     Kota      : {data.get('city')}")
    print(f"     Kondisi   : {data.get('condition')}")
    print(f"     Suhu      : {data.get('temp_c')}C")
    print(f"     Kelembaban: {data.get('humidity')}%")
    print(f"     Angin     : {data.get('wind_kmh')} km/h")
    print(f"     Sumber    : {data.get('source', 'API')}")
    if data.get("cache_ttl_left"):
        print(f"     TTL Sisa  : {data.get('cache_ttl_left')}")


# ─────────────────────────────────────────────
# MAIN TEST SEQUENCE
# ─────────────────────────────────────────────
def main():
    print(SEP2)
    print("  REDIS CACHING DEMO -- Simple LMS Lab")
    print(SEP2)

    status = "[OK] Redis terhubung di localhost:6379" if REDIS_AVAILABLE else "[WARN] Redis TIDAK tersedia"
    print(f"  {status}")
    print()

    # Bersihkan cache lama
    invalidate_cache("Jakarta")
    invalidate_cache("Bali")
    print()

    # ════════════════════════════════════════════════
    # TEST 1: First Call — Cache MISS
    # ════════════════════════════════════════════════
    print(SEP)
    print("  TEST 1: First Call -- Jakarta (Cache MISS)")
    print(SEP)

    start = time.perf_counter()
    result1 = get_weather("Jakarta")
    time1 = time.perf_counter() - start

    print_result(result1)
    print(f"\n  Response time: {time1:.3f} detik   <-- LAMBAT (API call)")
    cache_info("Jakarta")
    print()

    # ════════════════════════════════════════════════
    # TEST 2: Second Call — Cache HIT
    # ════════════════════════════════════════════════
    print(SEP)
    print("  TEST 2: Second Call -- Jakarta (Cache HIT)")
    print(SEP)

    start = time.perf_counter()
    result2 = get_weather("Jakarta")
    time2 = time.perf_counter() - start

    print_result(result2)
    print(f"\n  Response time: {time2:.4f} detik   <-- CEPAT (dari Redis)")
    print()

    # ════════════════════════════════════════════════
    # TEST 3: Kota Berbeda — Bali (Cache MISS)
    # ════════════════════════════════════════════════
    print(SEP)
    print("  TEST 3: Kota Baru -- Bali (Cache MISS)")
    print(SEP)

    start = time.perf_counter()
    result3 = get_weather("Bali")
    time3 = time.perf_counter() - start
    print_result(result3)
    print(f"\n  Response time: {time3:.3f} detik   <-- LAMBAT (API call)")
    print()

    # TEST 4: Bali Second Call
    print(SEP)
    print("  TEST 4: Bali -- Second Call (Cache HIT)")
    print(SEP)

    start = time.perf_counter()
    result4 = get_weather("Bali")
    time4 = time.perf_counter() - start
    print_result(result4)
    print(f"\n  Response time: {time4:.4f} detik   <-- CEPAT (dari Redis)")
    print()

    # ════════════════════════════════════════════════
    # RINGKASAN PERFORMA
    # ════════════════════════════════════════════════
    print(SEP2)
    print("  RINGKASAN PERFORMA")
    print(SEP2)
    speedup = time1 / time2 if time2 > 0.0001 else 9999

    print(f"  {'Call':<35} {'Time':>10}  Sumber")
    print(SEP)
    print(f"  {'1. Jakarta - 1st call (API)':<35} {time1:>8.3f}s  API (slow)")
    print(f"  {'2. Jakarta - 2nd call (Redis)':<35} {time2:>8.4f}s  CACHE (fast)")
    print(f"  {'3. Bali    - 1st call (API)':<35} {time3:>8.3f}s  API (slow)")
    print(f"  {'4. Bali    - 2nd call (Redis)':<35} {time4:>8.4f}s  CACHE (fast)")
    print(SEP)
    print(f"  Speed-up   : ~{speedup:.0f}x lebih cepat dengan cache")
    print(f"  Cache TTL  : {CACHE_TTL} detik ({CACHE_TTL//60} menit)")

    # ════════════════════════════════════════════════
    # DEMO REDIS CLI COMMANDS
    # ════════════════════════════════════════════════
    print()
    print(SEP2)
    print("  DEMO REDIS COMMANDS")
    print(SEP2)

    if REDIS_AVAILABLE:
        import json
        from weather_api import redis_client

        # KEYS
        keys = list_all_cache_keys()
        print(f"\n  > KEYS weather:*")
        for k in keys:
            print(f"    {k}")

        # GET
        print(f"\n  > GET weather:jakarta")
        raw = redis_client.get("weather:jakarta")
        if raw:
            parsed = json.loads(raw)
            print(f"    {json.dumps(parsed, ensure_ascii=False)}")

        # TTL
        ttl = redis_client.ttl("weather:jakarta")
        print(f"\n  > TTL weather:jakarta")
        print(f"    {ttl} detik ({ttl//60}m {ttl%60}s tersisa)")

        # EXISTS
        exists = redis_client.exists("weather:jakarta")
        print(f"\n  > EXISTS weather:jakarta")
        print(f"    {exists}  (1=ada, 0=tidak ada)")

        # Simulasi expiry
        print(f"\n  [Simulasi Cache Expired]")
        print(f"  > EXPIRE weather:jakarta 1  (set TTL jadi 1 detik)")
        redis_client.expire("weather:jakarta", 1)
        time.sleep(1.5)
        after_expire = redis_client.get("weather:jakarta")
        print(f"  > GET weather:jakarta (1.5 detik kemudian)")
        print(f"    {after_expire}  (None = sudah expired, cache hilang)")

        # Re-fetch setelah expire
        print(f"\n  [Re-fetch setelah expired -- harus lambat lagi]")
        start = time.perf_counter()
        get_weather("Jakarta")
        time_refetch = time.perf_counter() - start
        print(f"  Response time setelah expired: {time_refetch:.3f}s  <-- lambat lagi!")

    print()
    print(SEP2)
    print("  SELESAI! Lihat cache_report.md untuk dokumentasi lengkap.")
    print(SEP2)


if __name__ == "__main__":
    main()
