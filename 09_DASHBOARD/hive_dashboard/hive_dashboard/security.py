import os
from functools import wraps

from django.http import HttpResponseForbidden


def internal_api_allowed(request, env_var: str = "HIVE_API_TOKEN", require_staff: bool = False) -> bool:
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if not require_staff or user.is_staff:
            return True

    token = os.environ.get(env_var, "").strip()
    if not token:
        return False

    auth_header = request.headers.get("Authorization", "")
    header_token = request.headers.get("X-Hive-Api-Key", "").strip()
    bearer_token = ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()

    return header_token == token or bearer_token == token


def internal_api_required(view_func=None, *, env_var: str = "HIVE_API_TOKEN"):
    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            if not internal_api_allowed(request, env_var=env_var):
                return HttpResponseForbidden("Forbidden")
            return func(request, *args, **kwargs)

        return _wrapped

    if view_func is None:
        return decorator
    return decorator(view_func)


def staff_or_internal_required(view_func=None, *, env_var: str = "HIVE_API_TOKEN"):
    def decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            if not internal_api_allowed(request, env_var=env_var, require_staff=True):
                return HttpResponseForbidden("Forbidden")
            return func(request, *args, **kwargs)

        return _wrapped

    if view_func is None:
        return decorator
    return decorator(view_func)
