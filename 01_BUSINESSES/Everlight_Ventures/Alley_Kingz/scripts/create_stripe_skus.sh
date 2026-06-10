#!/usr/bin/env bash
# create_stripe_skus.sh - Create Alley Kingz Phase 1 products + prices in Stripe.
#
# Source: 01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ONLINE_STORE_SPEC.md
# Prereq: STRIPE_SECRET_KEY in env (live key). Stripe CLI installed.
#
# Safe to run repeatedly? NO - creates duplicate products if re-run.
# Check with `stripe products list` first. Remove duplicates via Stripe Dashboard if seen.
#
# Output: prints new product/price IDs. Save them to .env as
#   STRIPE_PRICE_AK_HOODIE=...
#   STRIPE_PRICE_AK_TEE=...
#   STRIPE_PRICE_AK_STICKERS=...
#   STRIPE_SHIPPING_RATE_US=...

set -euo pipefail

if [ -z "${STRIPE_SECRET_KEY:-}" ]; then
  echo "ERROR: STRIPE_SECRET_KEY not set"
  exit 1
fi

export STRIPE_API_KEY="$STRIPE_SECRET_KEY"

echo "[1/4] Creating Hoodie product + price..."
HOODIE_PROD=$(stripe products create \
  --name="Alley Kingz Hoodie - Drop 001" \
  --description="Heavyweight cotton hoodie. Gold foil crown on the back. Numbered interior tag. Limited to 50 per color." \
  --shippable=true \
  --metadata[brand]=alley_kingz \
  --metadata[drop]=001 \
  --metadata[fulfillment]=pod_printful \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  product: $HOODIE_PROD"

HOODIE_PRICE=$(stripe prices create \
  --product="$HOODIE_PROD" \
  --unit-amount=6500 \
  --currency=usd \
  --nickname="Hoodie base price" \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  price: $HOODIE_PRICE"

echo ""
echo "[2/4] Creating Tee product + price..."
TEE_PROD=$(stripe products create \
  --name="Alley Kingz Tee" \
  --description="Heavyweight cotton tee. Embroidered crown. Everyday wear." \
  --shippable=true \
  --metadata[brand]=alley_kingz \
  --metadata[fulfillment]=pod_printful \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  product: $TEE_PROD"

TEE_PRICE=$(stripe prices create \
  --product="$TEE_PROD" \
  --unit-amount=3200 \
  --currency=usd \
  --nickname="Tee base price" \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  price: $TEE_PRICE"

echo ""
echo "[3/4] Creating Sticker Pack product + price..."
STICKERS_PROD=$(stripe products create \
  --name="Alley Kingz Founder Sticker Pack" \
  --description="5-piece vinyl sticker set." \
  --shippable=true \
  --metadata[brand]=alley_kingz \
  --metadata[fulfillment]=manual_fulfilled_everlight \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  product: $STICKERS_PROD"

STICKERS_PRICE=$(stripe prices create \
  --product="$STICKERS_PROD" \
  --unit-amount=800 \
  --currency=usd \
  --nickname="Sticker pack price" \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "  price: $STICKERS_PRICE"

echo ""
echo "[4/4] Creating US Standard shipping rate..."
SHIP_RATE=$(stripe shipping-rates create \
  --display-name="US Standard" \
  --type=fixed_amount \
  --fixed-amount[amount]=600 \
  --fixed-amount[currency]=usd \
  --delivery-estimate[minimum][unit]=business_day \
  --delivery-estimate[minimum][value]=4 \
  --delivery-estimate[maximum][unit]=business_day \
  --delivery-estimate[maximum][value]=7 \
  --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "SKIPPED_MANUAL_IN_DASHBOARD")
echo "  shipping rate: $SHIP_RATE"

echo ""
echo "=== COPY THESE TO .env ==="
echo "STRIPE_PRICE_AK_HOODIE=$HOODIE_PRICE"
echo "STRIPE_PRICE_AK_TEE=$TEE_PRICE"
echo "STRIPE_PRICE_AK_STICKERS=$STICKERS_PRICE"
echo "STRIPE_SHIPPING_RATE_US=$SHIP_RATE"
