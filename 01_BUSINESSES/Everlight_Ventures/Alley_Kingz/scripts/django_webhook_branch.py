"""django_webhook_branch.py - Alley Kingz fulfillment handler.

Drop this into `09_DASHBOARD/hive_dashboard/alley_kingz/fulfillment.py` and wire
the existing Stripe webhook in `payments/views.py` to call `fulfill_order(session)`
when `session.metadata.brand == "alley_kingz"`.

Handles:
- POD items (Hoodie, Tee) via Printful API
- Manual items (Sticker pack) via Slack drop-card to Lucrex
- Logs every order to Supabase table `alley_kingz_orders`
- Receipt via Resend
- Slack notify to #content-factory channel
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

log = logging.getLogger("alley_kingz_fulfillment")

PRINTFUL_API_KEY = os.environ.get("PRINTFUL_API_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SLACK_TOKEN = os.environ.get("SLACK_WARROOM_TOKEN", "")
SLACK_CONTENT_FACTORY_CHANNEL = "C0ANPRDUP0R"

# Map Stripe product IDs to Printful variant IDs; fill during onboarding
PRINTFUL_VARIANT_MAP = {
    # "prod_xxx": 4012  # hoodie M black variant
}


def _log_to_supabase(order: dict[str, Any]) -> None:
    if not (SUPABASE_URL and SUPABASE_ANON_KEY):
        log.warning("supabase creds missing; skipping log")
        return
    url = f"{SUPABASE_URL}/rest/v1/alley_kingz_orders"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(order), timeout=10)
    except requests.RequestException as e:
        log.error("supabase log failed: %s", e)


def _submit_printful_order(session: dict[str, Any]) -> dict[str, Any]:
    if not PRINTFUL_API_KEY:
        return {"status": "skipped_no_key"}
    # Pull shipping address + line items from Stripe session
    shipping = session.get("shipping_details") or session.get("shipping") or {}
    addr = shipping.get("address") or {}
    items = []
    for li in session.get("line_items", {}).get("data", []):
        price_id = li.get("price", {}).get("id", "")
        variant_id = PRINTFUL_VARIANT_MAP.get(price_id)
        if variant_id:
            items.append({"variant_id": variant_id, "quantity": li.get("quantity", 1)})
    payload = {
        "recipient": {
            "name": shipping.get("name", ""),
            "address1": addr.get("line1", ""),
            "address2": addr.get("line2", ""),
            "city": addr.get("city", ""),
            "state_code": addr.get("state", ""),
            "country_code": addr.get("country", ""),
            "zip": addr.get("postal_code", ""),
        },
        "items": items,
    }
    try:
        resp = requests.post(
            "https://api.printful.com/orders",
            headers={"Authorization": f"Bearer {PRINTFUL_API_KEY}"},
            data=json.dumps(payload),
            timeout=15,
        )
        return {"status": resp.status_code, "body": resp.text[:400]}
    except requests.RequestException as e:
        return {"status": "error", "error": str(e)}


def _slack_drop_card(session: dict[str, Any]) -> None:
    if not SLACK_TOKEN:
        return
    email = session.get("customer_details", {}).get("email", "")
    addr = session.get("shipping_details", {}).get("address", {})
    summary = (
        f"New Alley Kingz order. Pack + ship STICKERS to:\n"
        f"{email}\n{addr.get('line1','')}\n{addr.get('city','')}, {addr.get('state','')} {addr.get('postal_code','')}"
    )
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            data=json.dumps({"channel": SLACK_CONTENT_FACTORY_CHANNEL, "text": summary}),
            timeout=10,
        )
    except requests.RequestException as e:
        log.error("slack drop card failed: %s", e)


def _send_receipt(session: dict[str, Any]) -> None:
    email = session.get("customer_details", {}).get("email", "")
    if not email:
        return
    # Doctrine: every outbound email goes through branded_mailer (gold template,
    # resend_guard, resend_budget). No direct api.resend.com calls.
    try:
        import sys
        for root in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts",
                     "/home/opc/scripts", "/home/ubuntu/scripts"):
            if root not in sys.path:
                sys.path.insert(0, root)
        from content_tools.branded_mailer import send_branded_email
        result = send_branded_email(
            to=email,
            subject="Your Alley Kingz order is in",
            content_html=(
                "<p>Thanks for the support. Your order is locked in. "
                "Expect shipping confirmation within 48 hours. "
                "Crown up.</p>"
            ),
            from_name="Alley Kingz",
            from_email="drop@everlightventures.io",
            agent_name="Alley Kingz",
            agent_title="Order Desk",
            budget_category="system",  # transactional receipt, not outreach
        )
        ok = result.get("ok", False) if isinstance(result, dict) else bool(getattr(result, "ok", False))
        if not ok:
            log.error("branded receipt failed: %s", result)
    except Exception as e:
        log.error("branded receipt failed: %s", e)


def fulfill_order(session: dict[str, Any]) -> dict[str, Any]:
    """Called from payments/views.py when a Stripe checkout.session.completed for alley_kingz hits."""
    meta = session.get("metadata", {}) or {}
    if meta.get("brand") != "alley_kingz":
        return {"ignored": True}

    order_row = {
        "session_id": session.get("id", ""),
        "email": session.get("customer_details", {}).get("email", ""),
        "amount_total": session.get("amount_total", 0),
        "currency": session.get("currency", "usd"),
        "size": meta.get("size", ""),
        "color": meta.get("color", ""),
        "address_json": json.dumps(session.get("shipping_details", {})),
        "status": "received",
        "created_at": session.get("created", None),
    }
    _log_to_supabase(order_row)

    # Decide fulfillment path
    line_items = session.get("line_items", {}).get("data", [])
    has_pod = False
    has_manual = False
    for li in line_items:
        nickname = li.get("price", {}).get("nickname", "").lower()
        if "hoodie" in nickname or "tee" in nickname:
            has_pod = True
        if "sticker" in nickname:
            has_manual = True

    if has_pod:
        printful_result = _submit_printful_order(session)
        order_row["printful"] = printful_result
    if has_manual:
        _slack_drop_card(session)

    _send_receipt(session)
    return {"ok": True, "session_id": session.get("id", ""), "pod": has_pod, "manual": has_manual}
