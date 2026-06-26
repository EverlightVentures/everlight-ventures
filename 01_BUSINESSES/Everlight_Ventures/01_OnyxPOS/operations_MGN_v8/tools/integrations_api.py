"""Live API sync adapters: QuickBooks Online, Square, Shopify.

CREDENTIAL-GATED and SAFE BY DEFAULT. Each platform reads its keys from environment
variables (set in .env on the Dell -- NEVER stored in git or a committed CSV, same
as SMTP_/STRIPE_ keys). Until the keys are set, every method returns
{"ok": False, "reason": ...} so callers degrade gracefully (the branded_sms pattern).

The real HTTP calls are marked TODO(live): they are wired the day real credentials +
a live account exist to test against. Nothing here makes a live API call without keys,
so this module is inert until you opt in -- which is exactly "CSV-only for now, all
three later".
"""
import os

ADAPTERS = {
    "quickbooks": {
        "label": "QuickBooks Online",
        "env": ["QBO_CLIENT_ID", "QBO_CLIENT_SECRET", "QBO_REFRESH_TOKEN", "QBO_REALM_ID"],
        "guide": "Intuit developer app -> set QBO_CLIENT_ID / QBO_CLIENT_SECRET / "
                 "QBO_REFRESH_TOKEN / QBO_REALM_ID in .env",
    },
    "square": {
        "label": "Square",
        "env": ["SQUARE_ACCESS_TOKEN"],
        "guide": "Square Developer -> access token -> set SQUARE_ACCESS_TOKEN "
                 "(and optionally SQUARE_LOCATION_ID) in .env",
    },
    "shopify": {
        "label": "Shopify",
        "env": ["SHOPIFY_STORE", "SHOPIFY_ADMIN_TOKEN"],
        "guide": "Shopify Admin -> custom app -> set SHOPIFY_STORE (xxx.myshopify.com) "
                 "+ SHOPIFY_ADMIN_TOKEN in .env",
    },
}


def is_configured(platform):
    cfg = ADAPTERS.get(platform)
    if not cfg:
        return False
    return all(os.environ.get(k, "").strip() for k in cfg["env"])


def _missing(platform):
    cfg = ADAPTERS.get(platform, {"env": []})
    return [k for k in cfg["env"] if not os.environ.get(k, "").strip()]


def status():
    """Connection status for each platform (never exposes secret values)."""
    out = []
    for key, cfg in ADAPTERS.items():
        out.append({
            "platform": key, "label": cfg["label"],
            "configured": is_configured(key),
            "missing": _missing(key), "guide": cfg["guide"],
        })
    return out


def _gate(platform):
    if platform not in ADAPTERS:
        return {"ok": False, "reason": f"unknown platform '{platform}'"}
    if not is_configured(platform):
        miss = ", ".join(_missing(platform))
        return {"ok": False,
                "reason": f"{ADAPTERS[platform]['label']} not connected -- set {miss} in .env"}
    return None


def push_catalog(platform, items):
    gate = _gate(platform)
    if gate:
        return gate
    # TODO(live): credentials present -> POST `items` to the platform catalog API here.
    # Left unimplemented on purpose until a live account + keys exist to test against.
    return {"ok": False, "reason": "credentials present -- live catalog push not wired yet"}


def push_sale(platform, sale):
    gate = _gate(platform)
    if gate:
        return gate
    return {"ok": False, "reason": "credentials present -- live sale push not wired yet"}


def test_connection(platform):
    gate = _gate(platform)
    if gate:
        return gate
    return {"ok": True, "reason": f"{ADAPTERS[platform]['label']} credentials present"}
