import time


class RequestTimingMiddleware:
    """Add X-Request-Duration header and make timing available in templates."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        response['X-Request-Duration'] = f"{duration_ms:.1f}ms"
        return response
