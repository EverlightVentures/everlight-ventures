import time
import logging

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """Log request duration for performance monitoring."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        if duration_ms > 500:
            logger.warning("Slow request: %s %s took %.0fms", request.method, request.path, duration_ms)
        return response
