# render/pricing.py
"""Single source of truth for image-model tiers + the margin gate.
Encodes the 'price must clear COGS and grow' law so the build enforces it,
not the operator's memory. Mirrored as Deno constants in coverforge-create-job."""

MAX_VARIATIONS = 4  # per credit; regenerations cost another credit

TIER_MODELS = {
    "economy":  {"model": "fal-ai/flux/schnell",          "img_cost": 0.025},
    "standard": {"model": "fal-ai/flux/dev",              "img_cost": 0.04},
    "premium":  {"model": "google/nano-banana-pro-batch", "img_cost": 0.067},
}
HAIKU_BUNDLE_COST = 0.002
STRIPE_FEE_PER_COVER = 0.25  # amortized over a 3-batch $15 pack


def cost_per_cover(tier: str, variations: int = 1) -> float:
    if tier not in TIER_MODELS:
        raise ValueError(f"unknown tier {tier!r}; expected {list(TIER_MODELS)}")
    v = min(max(variations, 1), MAX_VARIATIONS)
    return TIER_MODELS[tier]["img_cost"] * v + HAIKU_BUNDLE_COST + STRIPE_FEE_PER_COVER


def clears_costs(price: float, tier: str, variations: int = 1, target_margin: float = 0.90) -> bool:
    """True iff price >= cogs / (1 - target_margin)."""
    return price >= cost_per_cover(tier, variations) / (1 - target_margin)
