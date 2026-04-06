from __future__ import annotations

from decimal import Decimal
from typing import Any


DEFAULT_GEM_PACKAGE_CATALOG: dict[str, dict[str, Any]] = {
    "Starter Pack": {
        "gems": 100,
        "bonus_gems": 0,
        "price_usd": Decimal("0.99"),
        "stripe_price_id": "price_1T86XiGd8n4Fz3nAsJk2s93y",
        "is_featured": False,
        "is_active": True,
    },
    "Player Pack": {
        "gems": 500,
        "bonus_gems": 100,
        "price_usd": Decimal("4.99"),
        "stripe_price_id": "price_1T86XjGd8n4Fz3nASyIVCA70",
        "is_featured": False,
        "is_active": True,
    },
    "High Roller": {
        "gems": 1200,
        "bonus_gems": 300,
        "price_usd": Decimal("9.99"),
        "stripe_price_id": "price_1T86XkGd8n4Fz3nAjXXz9pcI",
        "is_featured": True,
        "is_active": True,
    },
    "VIP Bundle": {
        "gems": 3000,
        "bonus_gems": 1000,
        "price_usd": Decimal("24.99"),
        "stripe_price_id": "price_1T86XlGd8n4Fz3nAHfTgPqih",
        "is_featured": False,
        "is_active": True,
    },
    "Casino Boss": {
        "gems": 7000,
        "bonus_gems": 3000,
        "price_usd": Decimal("49.99"),
        "stripe_price_id": "",
        "is_featured": False,
        "is_active": False,
    },
}


def resolve_gem_package_config(package_or_name: Any) -> dict[str, Any]:
    if hasattr(package_or_name, "name"):
        package = package_or_name
        name = str(package.name)
        config: dict[str, Any] = {
            "id": getattr(package, "id", None),
            "name": name,
            "gems": int(getattr(package, "gems", 0) or 0),
            "bonus_gems": int(getattr(package, "bonus_gems", 0) or 0),
            "price_usd": getattr(package, "price_usd", Decimal("0.00")),
            "stripe_price_id": str(getattr(package, "stripe_price_id", "") or ""),
            "is_featured": bool(getattr(package, "is_featured", False)),
            "is_active": bool(getattr(package, "is_active", True)),
        }
    else:
        name = str(package_or_name)
        config = {
            "id": None,
            "name": name,
            "gems": 0,
            "bonus_gems": 0,
            "price_usd": Decimal("0.00"),
            "stripe_price_id": "",
            "is_featured": False,
            "is_active": True,
        }

    override = DEFAULT_GEM_PACKAGE_CATALOG.get(name, {})
    config.update(override)
    config["total_gems"] = int(config.get("gems", 0)) + int(config.get("bonus_gems", 0))
    config["checkout_ready"] = bool(config.get("stripe_price_id"))
    return config
