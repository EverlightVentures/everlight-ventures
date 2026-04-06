from __future__ import annotations

from typing import Any

from hive_dashboard.supabase_client import is_configured as bridge_enabled  # noqa: F401
from hive_dashboard.supabase_client import supabase_function

from .catalog import resolve_gem_package_config

PACKAGE_SLUG_MAP = {
    "Starter Pack": "gems-100",
    "Player Pack": "gems-600",
    "High Roller": "gems-1500",
    "VIP Bundle": "gems-4000",
}

TOTAL_GEMS_SLUG_MAP = {
    100: "gems-100",
    600: "gems-600",
    1500: "gems-1500",
    4000: "gems-4000",
}


def resolve_gem_package_slug(package_or_config: Any) -> str:
    config = (
        package_or_config
        if isinstance(package_or_config, dict)
        else resolve_gem_package_config(package_or_config)
    )
    name = str(config.get("name") or "")
    total_gems = int(config.get("total_gems") or 0)
    slug = PACKAGE_SLUG_MAP.get(name) or TOTAL_GEMS_SLUG_MAP.get(total_gems) or ""
    return slug


def package_checkout_ready(package_or_config: Any) -> bool:
    config = (
        package_or_config
        if isinstance(package_or_config, dict)
        else resolve_gem_package_config(package_or_config)
    )
    return bool(config.get("checkout_ready") and resolve_gem_package_slug(config))


def create_gem_checkout(
    *,
    slug: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    return supabase_function(
        "create-checkout",
        {
            "slug": slug,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata or {},
        },
        timeout=timeout,
    )


def verify_checkout_session(
    *,
    session_id: str,
    expected_slug: str = "",
    timeout: float = 20.0,
) -> dict[str, Any]:
    return supabase_function(
        "verify-checkout-session",
        {
            "session_id": session_id,
            "expected_slug": expected_slug or None,
        },
        timeout=timeout,
    )
