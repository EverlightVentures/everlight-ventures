#!/usr/bin/env python3
"""
gen_metadata.py -- Alley Kingz Metaplex Core metadata generator (PURE PYTHON).

Runs on the phone proot (no node/npm needed -- that is a HARD constraint; the
phone proot SIGSEGVs on npm install and cannot sign transactions). This script
ONLY emits the off-chain JSON + the on-chain Attribute-Plugin subset. The actual
mint (Sugar / umi / mpl-core) runs on e5-mother and is signed by the operator's
Phantom wallet. See RUNBOOK.md.

Reads:
  ../data/cards.json     -- the 48-card canon (rarity, faction, stats, ability, rig)
  ./asset_config.json    -- swappable CID base / gateway / naming patterns

Emits, per card:
  ./metadata/<cardNumber>_<slug>.json
      Metaplex Core standard off-chain metadata:
      name, symbol, description, image, animation_url, external_url,
      properties{category:"video", files[]}, attributes[]
      PLUS an "onchain_attributes" block = the Attribute-Plugin key-value subset
      that the mint step writes ON-CHAIN (per CHAIN_DECISION_MEMO section 4b).

Asset URIs are TEMPLATED placeholders until Seedance art + the upload land.
Swap the CID base in asset_config.json and re-run -- nothing else changes.

Tooling target (confirmed live 2026-06-03):
  mpl-core 1.10.0, umi 1.5.1, mpl-core-candy-machine (TokenPayment guard).

NO em-dash / en-dash anywhere in output (repo hook blocks them).
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARDS_PATH = HERE.parent / "data" / "cards.json"
CONFIG_PATH = HERE / "asset_config.json"
OUT_DIR = HERE / "metadata"

# Rig name -> hero-clip animation token, from SEEDANCE_BATTLE_KIT.md section 6.
# Where a card has a named hero rig + clip, the animation_url uses that token so
# it lines up with the real Seedance filename when the clip lands. Everything
# else falls back to <Name>_<RigOneWord>.
HERO_ANIM_TOKENS = {
    "0001": "$BCARDD_Crownbreaker",   # 2.1 hero clip
    "0013": "Jagged_ShadowFang",      # 2.3
    "0025": "Rosco_Leashbreaker",     # 2.4
    "0037": "CrownFoxhound_RoyalHunt",  # 2.5
    "0002": "Stonejaw_Stonewall",     # 2.6 (rig "Stonewall")
}


def slugify(value):
    """lowercase, spaces+punct -> underscore, collapse repeats, trim."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def camel_token(value):
    """'Crown Foxhound' -> 'CrownFoxhound' for the Seedance filename token."""
    parts = re.split(r"[^A-Za-z0-9]+", value.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def anim_token(card):
    cn = card["cardNumber"]
    if cn in HERO_ANIM_TOKENS:
        return HERO_ANIM_TOKENS[cn]
    # generic fallback: <Name>_<RigFirstWord>
    rig_name = card.get("rig", {}).get("name", "Rig")
    rig_word = camel_token(rig_name.split()[0]) if rig_name else "Rig"
    return f"{camel_token(card['name'])}_{rig_word}"


def build_description(card):
    """Brand-voice description: the dog + rig + faction. NO promised returns."""
    name = card["name"]
    breed = card["breed"]
    faction = card["class"]
    rarity = card["rarity"]
    role = card["role"]
    rig = card.get("rig", {})
    rig_name = rig.get("name", "")
    rig_lang = rig.get("rigLanguage", "")
    ability = card.get("ability", {}).get("name", "")

    if card.get("isMythic"):
        lead = f"{name} is a {rarity} {role} of the {faction}."
    elif rarity == "Legendary":
        lead = f"{name} is the {rarity} {role} of the {faction}."
    else:
        lead = f"{name}, a {rarity} {role} in the {faction}."

    rig_line = ""
    if rig_name:
        rig_line = f" The {breed} pilots the {rig_name}"
        if rig_lang:
            rig_line += f" -- {rig_lang.lower()}."
        else:
            rig_line += "."

    ability_line = f' Signature move: "{ability}".' if ability else ""

    # Card #0001 $BCARDD carries the coin/dealer through-line.
    if card["cardNumber"] == "0001":
        tie = (" Card #0001. The $BCARDD coin mascot, the blackjack dealer, and the"
               " Mythic Vanguard who anchors the whole pack. One dog, one currency,"
               " one aesthetic, one arcade.")
    else:
        tie = (" A playable Alley Kingz battle card on Solana -- the NFT is the card,"
               " with gameplay stats written on-chain.")

    closing = (" Cosmetic art plus gameplay stats; in-game items are for entertainment"
               " and utility, not investments. No promised returns.")

    return (lead + rig_line + ability_line + tie + closing).strip()


def card_slug(card):
    return slugify(card["name"])


def build_image_uri(card, cfg):
    pattern = cfg["image_filename_pattern"]
    fname = pattern.format(cardNumber=card["cardNumber"], slug=card_slug(card))
    return f'{cfg["image_cid_base"]}/{fname}'


def build_animation_uri(card, cfg):
    pattern = cfg["animation_filename_pattern"]
    fname = pattern.format(
        animation_date_prefix=cfg["animation_date_prefix"],
        anim_token=anim_token(card),
    )
    return f'{cfg["animation_cid_base"]}/{fname}'


def build_external_url(card, cfg):
    if card["cardNumber"] == "0001":
        # $BCARDD: brand / coin landing per task spec.
        return cfg["external_url_brand"]
    return f'{cfg["external_url_base"]}/{card["cardNumber"]}'


def build_attributes(card):
    """Off-chain (full) attribute list -- the marketplace/explorer display set."""
    rig = card.get("rig", {})
    ability = card.get("ability", {})
    attrs = [
        {"trait_type": "Card Number", "value": card["cardNumber"]},
        {"trait_type": "Faction", "value": card["class"]},
        {"trait_type": "Faction Id", "value": card["factionId"]},
        {"trait_type": "Breed", "value": card["breed"]},
        {"trait_type": "Name", "value": card["name"]},
        {"trait_type": "Rarity", "value": card["rarity"]},
        {"trait_type": "Role", "value": card["role"]},
        {"trait_type": "Cost", "value": card["cost"]},
    ]
    for tag in card.get("tags", []):
        attrs.append({"trait_type": "Tag", "value": tag})
    attrs.extend([
        {"trait_type": "HP", "value": card["hp"]},
        {"trait_type": "Damage", "value": card["damage"]},
        {"trait_type": "Attack Speed", "value": card["attack_speed"]},
        {"trait_type": "Move Speed", "value": card["move_speed"]},
        {"trait_type": "Range", "value": card["range"]},
        {"trait_type": "Ability", "value": ability.get("name", "")},
        {"trait_type": "Ability Cooldown", "value": ability.get("cooldown", 0)},
        {"trait_type": "Queen Target", "value": bool(card.get("queen_target", False))},
        {"trait_type": "Rig", "value": rig.get("name", "")},
        {"trait_type": "Rig Class", "value": rig.get("rigClass", "")},
        {"trait_type": "Weapon Mod", "value": rig.get("weaponMod", "")},
    ])
    return attrs


def build_onchain_attributes(card, cfg):
    """
    The Attribute-Plugin subset that the mint step writes ON-CHAIN.
    Per CHAIN_DECISION_MEMO section 4b: gameplay-load-bearing, anti-cheat stats
    only. Values are STRINGS (Core Attribute Plugin stores key->value strings;
    the game/program parses to int). Mutable by the update authority only.

    Keys are driven by asset_config.json:onchain_attribute_keys so the split is
    declared in one place.
    """
    ability = card.get("ability", {})
    source = {
        "hp": card["hp"],
        "damage": card["damage"],
        "attack_speed": card["attack_speed"],
        "move_speed": card["move_speed"],
        "range": card["range"],
        "cost": card["cost"],
        "rarity": card["rarity"],
        "ability_id": slugify(ability.get("name", "")),
        "queen_target": "1" if card.get("queen_target", False) else "0",
    }
    keys = cfg.get("onchain_attribute_keys", list(source.keys()))
    # Core Attribute Plugin shape: a list of {key, value} string pairs.
    attribute_list = []
    for k in keys:
        if k in source:
            attribute_list.append({"key": k, "value": str(source[k])})
    return attribute_list


def build_metadata(card, cfg):
    image_uri = build_image_uri(card, cfg)
    animation_uri = build_animation_uri(card, cfg)
    return {
        "name": f'{cfg["collection_name"]} #{card["cardNumber"]} {card["name"]}',
        "symbol": cfg["symbol"],
        "description": build_description(card),
        "image": image_uri,
        "animation_url": animation_uri,
        "external_url": build_external_url(card, cfg),
        "attributes": build_attributes(card),
        "properties": {
            "category": "video",
            "chain": "solana",
            "standard": "metaplex-core",
            "ticker": cfg["ticker"],
            "files": [
                {"uri": image_uri, "type": "image/png"},
                {"uri": animation_uri, "type": "video/mp4"},
            ],
        },
        # NOT part of the off-chain display spec; consumed by the e5-mother mint
        # step to populate the Core Attribute Plugin on-chain. Kept in the same
        # file so one artifact per card carries both halves of the hybrid split.
        "onchain_attributes": build_onchain_attributes(card, cfg),
    }


def main():
    if not CARDS_PATH.exists():
        sys.exit(f"cards.json not found at {CARDS_PATH}")
    if not CONFIG_PATH.exists():
        sys.exit(f"asset_config.json not found at {CONFIG_PATH}")

    cfg = json.loads(CONFIG_PATH.read_text())
    cards_doc = json.loads(CARDS_PATH.read_text())
    cards = cards_doc["cards"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = []
    seen_numbers = set()
    for card in cards:
        cn = card["cardNumber"]
        if cn in seen_numbers:
            sys.exit(f"duplicate cardNumber {cn} -- canon roster must be unique")
        seen_numbers.add(cn)

        meta = build_metadata(card, cfg)
        out_name = f"{cn}_{card_slug(card)}.json"
        (OUT_DIR / out_name).write_text(json.dumps(meta, indent=2) + "\n")
        written.append(out_name)

    expected = cards_doc.get("meta", {}).get("cardCount", len(cards))
    print(f"Wrote {len(written)} metadata files to {OUT_DIR}")
    print(f"Roster meta cardCount = {expected}")
    if len(written) != expected:
        print(f"WARNING: wrote {len(written)} but roster cardCount says {expected}")
    else:
        print("OK: file count matches roster cardCount.")


if __name__ == "__main__":
    main()
