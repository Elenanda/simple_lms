"""
services/rate_limiter.py
Middleware Django untuk Rate Limiting berbasis Redis

Strategi: Sliding Window Counter
  - 60 requests per menit per IP address
  - Key: rl:{ip}:{window_timestamp}
  - Exempt: /api/docs, /admin/, /silk/
"""

import time
from django.conf import settings
from django.http import JsonResponse


class RateLimitMiddleware:
    """
    Django WSGI middleware untuk rate limiting via Redis.

    Config (via settings.py):
      RATE_LIMIT_REQUESTS = 60   # max request per window
      RATE_LIMIT_WINDOW   = 60   # window size dalam detik
    """

    EXEMPT_PATHS = ('/api/docs', '/api/openapi.json', '/admin/', '/silk/')

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit  = getattr(settings, 'RATE_LIMIT_REQUESTS', 60)
        self.window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)

    def __call__(self, request):
        # Hanya terapkan ke /api/ dan bukan path yang dikecualikan
        if request.path.startswith('/api/'):
            if not any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
                response = self._check_rate_limit(request)
                if response:
                    return response

        return self.get_response(request)

    def _check_rate_limit(self, request):
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")

            ip     = self._get_client_ip(request)
            bucket = int(time.time() // self.window)
            key    = f"rl:{ip}:{bucket}"

            count = redis.incr(key)
            if count == 1:
                # Set TTL hanya pada request pertama
                redis.expire(key, self.window + 5)

            # Set header informatif
            request._rl_count = count
            request._rl_limit = self.limit

            if count > self.limit:
                return JsonResponse(
                    {
                        "detail": "Rate limit exceeded.",
                        "limit":  self.limit,
                        "window": f"{self.window}s",
                        "retry_after": self.window - (int(time.time()) % self.window),
                    },
                    status=429,
                )
        except Exception:
            # Jika Redis tidak tersedia → biarkan request lewat
            pass
        return None

    def _get_client_ip(self, request) -> str:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
