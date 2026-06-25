#!/usr/bin/env python3
"""Backfill the Items.csv `Taxable` column from CA sales-tax rules (Reg 1588 / R&TC
6359): food-producing plants are EXEMPT, ornamentals + hardgoods are TAXABLE.

It classifies by keywords found in the item name / product name / subcategory /
description. It is SAFE:
  - dry-run by default (prints the plan); pass --apply to write.
  - backs up Items.csv first.
  - preserves every column (DictReader/DictWriter on the on-disk header).
  - only changes rows whose current Taxable is blank or 'Y' (the create default), so
    an owner's explicit Exempt/Review choices are never overwritten -> safe to re-run.

NOTE on the current MGN data: the real product names were lost in an earlier import
(every plant is literally named "Plant ..."), so there is NO species signal to key on
-- this script will report 0 food matches until a proper catalog (with real names) is
re-imported. That is honest, not a bug: nothing gets wrongly exempted. Until then, the
owner marks food items Exempt on each item's edit page (the Taxable dropdown), or runs
this again after importing named products.

Usage:
  python3 tools/backfill_item_tax.py            # dry-run, show the plan
  python3 tools/backfill_item_tax.py --apply    # write changes (after a backup)
  python3 tools/backfill_item_tax.py --plants-to-review --apply
        # also flag every still-'Y' plant as REVIEW so the owner has a worklist
"""
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
ITEMS = APP / "Inventory" / "Items.csv"

FOOD_HINTS = (
    "veget", "tomato", "pepper", "lettuce", "squash", "zucchini", "bean", "pea",
    "herb", "basil", "cilantro", "parsley", "rosemary", "thyme", "mint", "sage food",
    "oregano", "chive", "dill", "fruit", "berry", "strawberr", "blueberr", "raspberr",
    "blackberr", "citrus", "lemon", "lime", "orange", "mandarin", "apple", "pear",
    "peach", "nectarine", "apricot", "plum", "cherry", "fig", "avocado", "grape",
    "olive", "almond", "walnut", "pecan", "pistachio", "edible", "kale", "spinach",
    "broccoli", "cabbage", "cucumber", "melon", "watermelon", "onion", "garlic",
    "carrot", "corn", "chard", "artichoke", "asparagus", "pomegranate", "persimmon",
    "kiwi", "guava", "starts", "vegetable start", "seed potato",
)
ORNAMENTAL_HINTS = (
    "ornamental", "rose", "succulent", "cactus", "fern", "flower", "annual color",
    "perennial", "shrub", "maple", "juniper", "boxwood", "azalea", "camellia",
    "hydrangea", "petunia", "marigold", "geranium", "begonia", "pansy", "topiary",
    "bonsai", "houseplant", "palm ornamental", "decor", "bamboo lucky",
)


def classify(row):
    """Return ('N'|'Y'|'REVIEW'|None, reason). None = leave unchanged."""
    cat = (row.get("Category") or "").strip().lower()
    blob = " ".join([
        row.get("Item_Name", ""), row.get("Product_Name", ""),
        row.get("Subcategory", ""), row.get("Item_Description", ""),
    ]).lower()

    # Non-plant hardgoods (pots, soil, tools, supplies, decor) are taxable.
    if cat and not cat.startswith("plant"):
        return "Y", "hardgood/supply -> taxable"

    if any(h in blob for h in FOOD_HINTS):
        return "N", "food-producing plant -> exempt (Reg 1588)"
    if any(h in blob for h in ORNAMENTAL_HINTS):
        return "Y", "ornamental plant -> taxable"
    return None, "no signal (name lacks species)"


def main():
    apply = "--apply" in sys.argv
    plants_to_review = "--plants-to-review" in sys.argv

    if not ITEMS.exists():
        print(f"No Items.csv at {ITEMS}")
        return 1

    with open(ITEMS, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    changes = []
    for r in rows:
        cur = (r.get("Taxable") or "").strip().upper()
        if cur not in ("", "Y"):          # never override Exempt/REVIEW the owner set
            continue
        new, reason = classify(r)
        if new is None and plants_to_review and (r.get("Category") or "").lower().startswith("plant"):
            new, reason = "REVIEW", "plant needs owner tax review"
        if new and new != cur:
            changes.append((r.get("SKU", ""), cur or "(blank)", new, reason))
            if apply:
                r["Taxable"] = new

    from collections import Counter
    summary = Counter(c[2] for c in changes)
    print(f"Items: {len(rows)} | would change: {len(changes)} -> {dict(summary)}")
    for sku, old, new, reason in changes[:25]:
        print(f"  {sku}: {old} -> {new}  ({reason})")
    if len(changes) > 25:
        print(f"  ... and {len(changes) - 25} more")

    if not apply:
        print("\nDRY-RUN. Re-run with --apply to write (a backup is made first).")
        return 0

    if changes:
        backup = ITEMS.with_name(f"Items.csv.bak-tax-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(ITEMS, backup)
        with open(ITEMS, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote {len(changes)} changes. Backup: {backup.name}")
    else:
        print("\nNothing to change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
