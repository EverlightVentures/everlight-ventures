#!/usr/bin/env python3
"""
ak_stripe_seed_products.py -- Alley Kingz gem packs -> Stripe Products + Prices.

TEST MODE ONLY, FAIL-CLOSED:
  * Reads STRIPE_SECRET_KEY from the environment. Nothing is read from disk.
  * REFUSES to run against a live key (sk_live_* / rk_live_*). Live wiring stays
    gated until operator + legal greenlight flips AK_SHOP_TEST_MODE off with a
    reviewed key. Mirrors the liveBlocked() guard in the alley-kingz-shop edge fn.
  * Only sk_test_* / rk_test_* keys are accepted. Anything else is rejected.

IDEMPOTENT:
  * Products are looked up by metadata sku (+ game_id 'alley-kingz') before any
    create. Re-runs reuse existing Products and matching active USD Prices.

OUTPUT:
  * /mnt/sdcard/AA_MY_DRIVE/_state/ak_stripe_products.json
    {sku: {product_id, price_id, unit_amount, gems, title}} plus _meta.
    Feed the price ids into create-checkout's PRICE_MAP (the ak-gems-* slugs)
    and optionally backfill ak_shop_products.stripe_product_id/stripe_price_id.

Pure stdlib (urllib). No pip deps. Usage:
  STRIPE_SECRET_KEY=sk_test_... python3 ak_stripe_seed_products.py [--dry-run]
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

STRIPE_API = "https://api.stripe.com/v1"
STATE_PATH = "/mnt/sdcard/AA_MY_DRIVE/_state/ak_stripe_products.json"
GAME_ID = "alley-kingz"  # canonical AK namespace -- matches the edge function

# Canonical gem-pack SKUs. Source of truth: game/shop/shop.js +
# supabase/migrations/20260610_ak_shop_products.sql. sku == checkout_slug.
GEM_PACKS = [
    {"sku": "ak-gems-rookie",     "title": "AK Rookie Stash",      "gems": 500,   "unit_amount": 499},
    {"sku": "ak-gems-player",     "title": "AK Player Pack",       "gems": 1100,  "unit_amount": 999},
    {"sku": "ak-gems-baller",     "title": "AK Baller Bag",        "gems": 2500,  "unit_amount": 1999},
    {"sku": "ak-gems-highroller", "title": "AK High Roller Crate", "gems": 6500,  "unit_amount": 4999},
    {"sku": "ak-gems-kingpin",    "title": "AK Kingpin Vault",     "gems": 14000, "unit_amount": 9999},
]
DESCRIPTION_TMPL = (
    "{gems:,} Gems for Alley Kingz. In-game value only. No cash value. "
    "Not redeemable, not transferable, not an NFT."
)


def fail_closed_key_check(key: str) -> None:
    """Refuse anything that is not an explicit Stripe TEST secret key,
    unless the operator-greenlight env gate is set.

    AK_STRIPE_ALLOW_LIVE=1 lifts the live refusal. Set ONLY on explicit
    operator decision (Rich greenlit live 2026-06-09: "greenlight stripe,
    this site is live" + "u have all the keys u need" -- only live keys
    exist in the credential store). Default stays fail-closed.
    """
    allow_live = os.environ.get("AK_STRIPE_ALLOW_LIVE", "") == "1"
    if not key:
        print("REFUSED: STRIPE_SECRET_KEY is not set. Export a TEST key (sk_test_...) and re-run.")
        sys.exit(2)
    if key.startswith("sk_live") or key.startswith("rk_live"):
        if allow_live:
            print("LIVE MODE: operator greenlight gate (AK_STRIPE_ALLOW_LIVE=1) is set.")
            print("Creating products in Stripe LIVE mode.")
            return
        print("REFUSED: STRIPE_SECRET_KEY is a LIVE key. This seeder is TEST MODE ONLY.")
        print("Live wiring needs the operator greenlight gate: AK_STRIPE_ALLOW_LIVE=1.")
        print("No API call was made.")
        sys.exit(2)
    if not (key.startswith("sk_test_") or key.startswith("rk_test_")):
        print("REFUSED: STRIPE_SECRET_KEY does not look like a Stripe TEST secret key")
        print("(expected sk_test_... or rk_test_...). No API call was made.")
        sys.exit(2)


def stripe_request(key: str, method: str, path: str, params: dict | None = None) -> dict:
    """Minimal Stripe REST call via urllib. Form-encoded body, Bearer auth."""
    url = f"{STRIPE_API}{path}"
    data = None
    if method == "GET" and params:
        url += "?" + urllib.parse.urlencode(params)
    elif params:
        data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stripe {method} {path} -> HTTP {e.code}: {body}") from e


def list_all(key: str, path: str, base_params: dict) -> list[dict]:
    """Paginate a Stripe list endpoint (limit 100, starting_after cursor)."""
    out: list[dict] = []
    params = dict(base_params, limit=100)
    while True:
        page = stripe_request(key, "GET", path, params)
        out.extend(page.get("data", []))
        if not page.get("has_more"):
            return out
        params["starting_after"] = out[-1]["id"]


def find_product_by_sku(products: list[dict], sku: str) -> dict | None:
    for p in products:
        md = p.get("metadata") or {}
        if md.get("sku") == sku and md.get("game_id") == GAME_ID:
            return p
    return None


def find_price(prices: list[dict], unit_amount: int) -> dict | None:
    for pr in prices:
        if pr.get("currency") == "usd" and pr.get("unit_amount") == unit_amount and pr.get("active"):
            return pr
    return None


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    fail_closed_key_check(key)
    print(f"Stripe TEST key accepted ({key[:11]}...). dry_run={dry_run}")

    existing = list_all(key, "/products", {"active": "true"})
    print(f"Fetched {len(existing)} existing active Stripe products.")

    results: dict[str, dict] = {}
    for pack in GEM_PACKS:
        sku, gems, cents = pack["sku"], pack["gems"], pack["unit_amount"]
        product = find_product_by_sku(existing, sku)

        if product:
            print(f"[{sku}] product exists: {product['id']}")
        elif dry_run:
            print(f"[{sku}] DRY RUN: would create product '{pack['title']}' (${cents/100:.2f}, {gems} gems)")
            results[sku] = {"product_id": "(dry-run)", "price_id": "(dry-run)",
                            "unit_amount": cents, "gems": gems, "title": pack["title"]}
            continue
        else:
            product = stripe_request(key, "POST", "/products", {
                "name": pack["title"],
                "description": DESCRIPTION_TMPL.format(gems=gems),
                "metadata[sku]": sku,
                "metadata[game_id]": GAME_ID,
                "metadata[gems]": str(gems),
                "metadata[lane]": "A",
                "metadata[cashable]": "false",
            })
            print(f"[{sku}] product CREATED: {product['id']}")

        prices = list_all(key, "/prices", {"product": product["id"], "active": "true"})
        price = find_price(prices, cents)
        if price:
            print(f"[{sku}] price exists: {price['id']} (${cents/100:.2f})")
        elif dry_run:
            print(f"[{sku}] DRY RUN: would create price ${cents/100:.2f} usd")
            results[sku] = {"product_id": product["id"], "price_id": "(dry-run)",
                            "unit_amount": cents, "gems": gems, "title": pack["title"]}
            continue
        else:
            price = stripe_request(key, "POST", "/prices", {
                "product": product["id"],
                "currency": "usd",
                "unit_amount": str(cents),
                "metadata[sku]": sku,
                "metadata[game_id]": GAME_ID,
            })
            print(f"[{sku}] price CREATED: {price['id']} (${cents/100:.2f})")

        results[sku] = {
            "product_id": product["id"],
            "price_id": price["id"],
            "unit_amount": cents,
            "gems": gems,
            "title": pack["title"],
        }

    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "test",
            "game_id": GAME_ID,
            "dry_run": dry_run,
            "note": "TEST-mode Stripe ids. Wire into create-checkout PRICE_MAP "
                    "(ak-gems-* slugs) and ak_shop_products.stripe_*_id. "
                    "Live keys are refused by this script and by the edge function.",
        },
        "products": results,
    }
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(results)} SKUs -> {STATE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
