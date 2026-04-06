#!/usr/bin/env python3
"""
Create Everlight Intelligence Stripe products and prices.

Usage:
    export STRIPE_SECRET_KEY="sk_live_..."
    python setup_stripe_intel_products.py

Outputs the price IDs to paste into the edge function PRICE_MAP.
"""

import os
import sys
import json
import requests

STRIPE_API = "https://api.stripe.com/v1"


def stripe_headers() -> dict[str, str]:
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        print("ERROR: Set STRIPE_SECRET_KEY env var first.")
        sys.exit(1)
    return {"Authorization": f"Bearer {key}"}


def create_product(name: str, description: str) -> str:
    """Create a Stripe product, return its ID."""
    resp = requests.post(
        f"{STRIPE_API}/products",
        headers=stripe_headers(),
        data={
            "name": name,
            "description": description,
            "metadata[vendor]": "everlight_ventures",
            "metadata[category]": "intelligence",
        },
    )
    resp.raise_for_status()
    prod = resp.json()
    print(f"  Product: {prod['id']} -- {name}")
    return prod["id"]


def create_price(product_id: str, amount_cents: int, nickname: str) -> str:
    """Create a recurring monthly price, return its ID."""
    resp = requests.post(
        f"{STRIPE_API}/prices",
        headers=stripe_headers(),
        data={
            "product": product_id,
            "unit_amount": amount_cents,
            "currency": "usd",
            "recurring[interval]": "month",
            "nickname": nickname,
            "metadata[tier]": nickname.split()[-1].lower(),
        },
    )
    resp.raise_for_status()
    price = resp.json()
    print(f"  Price:   {price['id']} -- ${amount_cents // 100}/mo")
    return price["id"]


def main():
    products = [
        {
            "name": "Everlight Intelligence Basic",
            "description": (
                "Weekly distressed property data lists -- address, filing date, "
                "property type, estimated value. 6 markets covered."
            ),
            "slug": "intel-basic",
            "amount_cents": 50000,
        },
        {
            "name": "Everlight Intelligence Pro",
            "description": (
                "Weekly distressed property data + owner info, equity estimates, "
                "motivation scoring, days since filing. 6 markets."
            ),
            "slug": "intel-pro",
            "amount_cents": 100000,
        },
        {
            "name": "Everlight Intelligence Enterprise",
            "description": (
                "Full enrichment -- skip trace, phone, email, full property data, "
                "custom market requests, priority delivery. 6+ markets."
            ),
            "slug": "intel-enterprise",
            "amount_cents": 200000,
        },
    ]

    results = {}
    print("\n=== Creating Everlight Intelligence Stripe Products ===\n")

    for p in products:
        prod_id = create_product(p["name"], p["description"])
        price_id = create_price(prod_id, p["amount_cents"], p["name"])
        results[p["slug"]] = {
            "product_id": prod_id,
            "price_id": price_id,
            "amount": p["amount_cents"] // 100,
        }
        print()

    print("=== PRICE_MAP entries (paste into create-checkout/index.ts) ===\n")
    for slug, info in results.items():
        print(f'  "{slug}": "{info["price_id"]}",')

    # Save to file for reference
    out_path = os.path.join(os.path.dirname(__file__), "stripe_intel_prices.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
