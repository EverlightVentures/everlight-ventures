#!/usr/bin/env python3
"""
Build the Alley Kingz economy SEED migration from the canonical cards.json.

Author: Amara Osei (Iron Stack). Reads cards.json (48 cards + 5 spells) and emits
an idempotent INSERT ... ON CONFLICT DO UPDATE seed for:
  * ak_card_catalog   (48 cards + 5 spells, with descriptions)
  * ak_level_costs    (card rarities x9 + tower x9 upgrade bands)
  * ak_shop_products  (gem packs, deterministic + gated chests, consumable/pass stubs)

Output -> supabase/migrations/20260607_alley_kingz_economy_seed.sql

ECONOMY NUMBERS = committed FIRST DRAFT, all TUNABLE via LiveOps (operator/balance).
Regenerate after any cards.json change:  python3 _build_economy_seed.py
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(HERE, "cards.json")
# repo root = .../AA_MY_DRIVE ; walk up from ecosystem/data
OUT = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "..", "..",
    "supabase", "migrations", "20260607_alley_kingz_economy_seed.sql"))

# rarity -> scrap_value (card-value unit) + default card-shop copy price (matching scrap)
SCRAP_VALUE   = {"Common": 1, "Rare": 5, "Epic": 25, "Legendary": 250, "Mythic": 1000}
CARD_SHOP_BUY = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 5, "Mythic": 10}  # TUNABLE

# copies-to-upgrade bands (from_level 1..9). 0 copies = coins-only "blank band".
CARD_COPIES = {
    "Common":    [2, 4, 6, 10, 20, 40, 80, 150, 300],
    "Rare":      [1, 2, 4, 8, 16, 30, 60, 120, 250],
    "Epic":      [1, 1, 2, 4, 8, 16, 30, 60, 120],
    "Legendary": [1, 0, 1, 0, 2, 0, 4, 0, 8],
    "Mythic":    [1, 0, 0, 1, 0, 0, 1, 0, 1],
}
CARD_COINS = {
    "Common":    [5, 20, 50, 100, 250, 500, 1000, 2000, 4000],
    "Rare":      [50, 150, 400, 1000, 2000, 4000, 8000, 15000, 30000],
    "Epic":      [400, 800, 2000, 4000, 8000, 15000, 30000, 60000, 120000],
    # Legendary/Mythic coin bands: plan only says "up to ~150k / ~250k per band" -> TUNABLE draft.
    "Legendary": [2000, 5000, 10000, 20000, 40000, 60000, 90000, 120000, 150000],
    "Mythic":    [5000, 10000, 25000, 50000, 80000, 120000, 170000, 210000, 250000],
}
TOWER_COPIES = [1, 1, 2, 3, 4, 6, 8, 10, 12]                       # TUNABLE
TOWER_COINS  = [200, 500, 1000, 2000, 4000, 8000, 15000, 25000, 40000]  # TUNABLE


def esc(s):
    return ("" if s is None else str(s)).replace("'", "''")


def card_description(c):
    rar, role = c.get("rarity", ""), c.get("role", "")
    fac = (c.get("class") or c.get("factionId") or "").replace("_", " ")
    dom = c.get("domain") or "ground"
    ab = c.get("ability") or {}
    bits = [f"{rar} {role} of the {fac}.".strip()]
    if ab.get("description"):
        bits.append(f"{ab.get('name','Ability')}: {ab['description']}.")
    bits.append(f"Targets {dom}.")
    if c.get("splash"):
        bits.append("Splash damage.")
    if c.get("queen_target"):
        bits.append("Can strike the Queen.")
    return " ".join(bits)


def build():
    data = json.load(open(CARDS))
    cards, spells = data["cards"], data.get("spells", [])
    L = []
    L.append("-- ============================================================================")
    L.append("-- ALLEY KINGZ economy SEED -- GENERATED from cards.json by _build_economy_seed.py")
    L.append(f"-- Generated: {datetime.date.today().isoformat()}  | DO NOT hand-edit; regenerate.")
    L.append("-- Idempotent: INSERT ... ON CONFLICT DO UPDATE. Safe to re-run.")
    L.append("-- Economy numbers are a TUNABLE first draft (LiveOps owns final values).")
    L.append("-- ============================================================================")
    L.append("")

    # ---- ak_card_catalog (cards + spells) ----
    L.append("-- ---- ak_card_catalog : 48 cards + 5 spells ----")
    L.append("insert into public.ak_card_catalog")
    L.append("  (card_id, name, rarity, faction_id, is_spell, cost, role, domain, scrap_value, card_shop_price, description)")
    L.append("values")
    rows = []
    for c in cards:
        rar = c["rarity"]
        rows.append(
            f"  ('{esc(c['cardNumber'])}','{esc(c['name'])}','{rar}',"
            f"'{esc(c.get('factionId'))}',false,{int(c.get('cost') or 0)},"
            f"'{esc(c.get('role'))}','{esc(c.get('domain') or 'ground')}',"
            f"{SCRAP_VALUE[rar]},{CARD_SHOP_BUY[rar]},'{esc(card_description(c))}')")
    for s in spells:
        rar = s.get("rarity", "Epic")
        desc = f"SPELL. {esc(s.get('description',''))} (radius {s.get('radius','?')}, ~{s.get('duration','?')}s, cost {s.get('cost','?')}, cd {s.get('cooldown','?')}s)."
        rows.append(
            f"  ('{esc(s['spellNumber'])}','{esc(s['name'])}','{rar}',"
            f"'{esc(s.get('factionId'))}',true,{int(s.get('cost') or 0)},"
            f"'Spell','{esc(s.get('effect') or 'area')}',"
            f"{SCRAP_VALUE.get(rar,25)},{CARD_SHOP_BUY.get(rar,3)},'{desc}')")
    L.append(",\n".join(rows))
    L.append("on conflict (card_id) do update set")
    L.append("  name=excluded.name, rarity=excluded.rarity, faction_id=excluded.faction_id,")
    L.append("  is_spell=excluded.is_spell, cost=excluded.cost, role=excluded.role,")
    L.append("  domain=excluded.domain, scrap_value=excluded.scrap_value,")
    L.append("  card_shop_price=excluded.card_shop_price, description=excluded.description,")
    L.append("  updated_at=now();")
    L.append("")

    # ---- ak_level_costs : cards ----
    L.append("-- ---- ak_level_costs : card upgrade bands (copies + coins per from_level) ----")
    L.append("insert into public.ak_level_costs (entity_type, rarity, from_level, copies_required, coins_required)")
    L.append("values")
    cost_rows = []
    for rar in ["Common", "Rare", "Epic", "Legendary", "Mythic"]:
        for i in range(9):
            cost_rows.append(f"  ('card','{rar}',{i+1},{CARD_COPIES[rar][i]},{CARD_COINS[rar][i]})")
    for i in range(9):
        cost_rows.append(f"  ('tower',NULL,{i+1},{TOWER_COPIES[i]},{TOWER_COINS[i]})")
    L.append(",\n".join(cost_rows))
    L.append("on conflict (entity_type, rarity, from_level) do update set")
    L.append("  copies_required=excluded.copies_required, coins_required=excluded.coins_required;")
    L.append("")

    # ---- ak_shop_products ----
    L.append("-- ---- ak_shop_products : gems, chests, consumables, passes ----")
    L.append("-- Gem packs: price_usd + checkout_slug (route to create-checkout TEST price IDs).")
    L.append("-- Deterministic chests (is_random=false): SHIP -- fixed disclosed contents, open-able.")
    L.append("-- Random chests (is_random=true): odds disclosed but edge fn GATES open (PACK_RIP + Gate 3).")
    L.append("insert into public.ak_shop_products")
    L.append("  (sku, kind, title, description, price_usd, price_gems, checkout_slug, grants, odds, is_random, sort_order)")
    L.append("values")
    prod = [
        # Gem packs (Lane A hard currency -- NO cash value). checkout_slug -> create-checkout (TEST).
        ("ak-gems-rookie","gems","Rookie Stash","500 Gems. In-game value only, no cash value.",4.99,None,"ak-gems-rookie",'{"gems":500}',"NULL","false",10),
        ("ak-gems-player","gems","Player Pack","1,100 Gems (+10%).",9.99,None,"ak-gems-player",'{"gems":1100}',"NULL","false",11),
        ("ak-gems-baller","gems","Baller Bag","2,500 Gems (+25%).",19.99,None,"ak-gems-baller",'{"gems":2500}',"NULL","false",12),
        ("ak-gems-highroller","gems","High Roller Crate","6,500 Gems (+30%).",49.99,None,"ak-gems-highroller",'{"gems":6500}',"NULL","false",13),
        ("ak-gems-kingpin","gems","Kingpin Vault","14,000 Gems (+40%).",99.99,None,"ak-gems-kingpin",'{"gems":14000}',"NULL","false",14),
        # Deterministic chests -- SHIP. Fixed grants, open-able, legally clean (no RNG).
        ("chest_scrap_crate","chest","Scrap Crate","Fixed contents: 200 Coins + 5 Common Scrap. No random draw.",None,40,"NULL",'{"coins":200,"scrap_Common":5}',"NULL","false",20),
        ("chest_crew","chest","Crew Chest","Fixed contents: 500 Coins + 10 Common Scrap + 3 Rare Scrap. No random draw.",None,150,"NULL",'{"coins":500,"scrap_Common":10,"scrap_Rare":3}',"NULL","false",21),
        # Random chests -- GATED (gacha). Odds disclosed for store policy; edge fn refuses open.
        ("chest_chop_shop","chest","Chop-Shop Chest","Random: epic-guaranteed + rare + scrap. GATED until legal Gate 3.",None,400,"NULL",'{}','{"Epic":1.0,"Rare":2.0,"scrap_Epic":[3,8]}',"true",22),
        ("chest_kingpin","chest","Kingpin Chest","Random: legendary chance + epic + tokens. GATED until legal Gate 3.",None,900,"NULL",'{}','{"Legendary":0.15,"Epic":1.0,"scrap_Legendary":[1,3]}',"true",23),
        ("chest_mythic_vault","chest","Mythic Vault","Event-only random: mythic chance + guaranteed legendary tokens. GATED.",None,2000,"NULL",'{}','{"Mythic":0.02,"scrap_Legendary":[5,5]}',"true",24),
        # Consumables (Garage, PvE-only -- display stubs; buy-consumable not in scope yet).
        ("nitro_can","consumable","Nitro Can","Pre-PvE-match: +1 starting energy. PvE-only (never ranked).",None,50,"NULL",'{"pve_only":true,"effect":"+1_start_energy"}',"NULL","false",30),
        ("spell_emp","consumable","Lane EMP","One-shot PvE lane EMP. PvE-only (never ranked).",None,80,"NULL",'{"pve_only":true,"effect":"lane_emp"}',"NULL","false",31),
        # Passes (display -- route to existing create-checkout slugs; buy-pass not in scope yet).
        ("pass-master","pass","Master Pass","Arcade-wide: 2x earn, seasonal card track, +chest slot. $14.99/mo.",14.99,None,"master-pass",'{"perk":"arcade_master_pass"}',"NULL","false",40),
        ("pass-crew-ak","pass","AK Crew Pass","Alley Kingz only season track. $4.99/season.",4.99,None,"ak-season-pass",'{"perk":"ak_crew_pass"}',"NULL","false",41),
    ]
    prows = []
    for sku,kind,title,desc,usd,gems,slug,grants,odds,rnd,order in prod:
        usd_s = "NULL" if usd is None else str(usd)
        gems_s = "NULL" if gems is None else str(gems)
        slug_s = "NULL" if slug == "NULL" else f"'{slug}'"
        prows.append(
            f"  ('{sku}','{kind}','{esc(title)}','{esc(desc)}',{usd_s},{gems_s},{slug_s},"
            f"'{grants}'::jsonb,{('NULL' if odds=='NULL' else chr(39)+odds+chr(39)+'::jsonb')},{rnd},{order})")
    L.append(",\n".join(prows))
    L.append("on conflict (sku) do update set")
    L.append("  kind=excluded.kind, title=excluded.title, description=excluded.description,")
    L.append("  price_usd=excluded.price_usd, price_gems=excluded.price_gems,")
    L.append("  checkout_slug=excluded.checkout_slug, grants=excluded.grants, odds=excluded.odds,")
    L.append("  is_random=excluded.is_random, sort_order=excluded.sort_order, updated_at=now();")
    L.append("")
    L.append(f"-- {len(cards)} cards + {len(spells)} spells, {len(cost_rows)} cost bands, {len(prod)} shop products.")
    L.append("-- END SEED.")
    open(OUT, "w").write("\n".join(L) + "\n")
    print(f"Wrote {OUT}")
    print(f"  cards={len(cards)} spells={len(spells)} cost_bands={len(cost_rows)} products={len(prod)}")


if __name__ == "__main__":
    build()
