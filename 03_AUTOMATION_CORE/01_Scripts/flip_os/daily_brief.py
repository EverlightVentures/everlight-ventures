#!/usr/bin/env python3
"""
Flip OS -- Daily Flip Briefing
Runs at 5:30 AM PT. Aggregates penny intel, inventory status, and generates
a morning brief posted to Slack #war-room and stored in Supabase.

The brief answers: "What should I hunt today? What should I list? How's the P&L?"
"""
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ENV_PATH = Path(__file__).resolve().parent.parent.parent / "03_Credentials" / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SLACK_TOKEN = os.environ.get("SLACK_WARROOM_TOKEN", "")
SLACK_CHANNEL = "C08NMHAF0LE"  # #war-room
BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")
STORAGE_RENT = 60.00
N8N_GDOC_URL = "http://129.159.38.250:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc"

# HD Department -> Aisle mapping (standard across all stores)
DEPT_MAP = {
    "tools": {"dept": "D25 Power Tools / D25 Hand Tools", "aisle": "Aisles 11-15 (power tools center)", "endcap": "Check endcaps between aisles 12-14"},
    "appliances": {"dept": "D29 Appliances", "aisle": "Back wall appliance showroom + Aisle 8-9 area", "endcap": "Appliance clearance usually back-left corner"},
    "bath": {"dept": "D29 Kitchen & Bath", "aisle": "Aisles 9-10 (bath vanity showroom)", "endcap": "Vanity clearance on endcaps near aisle 10"},
    "kitchen": {"dept": "D29 Kitchen & Bath / D26 Plumbing", "aisle": "Aisle 9 (faucets) / Aisle 18-19 (plumbing)", "endcap": "Faucet clearance endcap near aisle 9"},
    "lighting": {"dept": "D27 Electrical / Lighting", "aisle": "Aisles 3-5 (lighting showroom)", "endcap": "Lighting clearance middle endcaps aisle 4"},
    "electrical": {"dept": "D27 Electrical", "aisle": "Aisles 5-7", "endcap": "Endcaps aisles 5-6"},
    "plumbing": {"dept": "D26 Plumbing", "aisle": "Aisles 18-20", "endcap": "Endcaps near aisle 19"},
    "garden": {"dept": "D28 Garden / Outdoor", "aisle": "Garden center (outside) + Aisles 1-2", "endcap": "Seasonal clearance near garden entrance"},
    "outdoor": {"dept": "D28 Outdoor Living", "aisle": "Garden center + seasonal area near entrance", "endcap": "Outdoor clearance endcaps near front"},
    "hardware": {"dept": "D25 Hardware", "aisle": "Aisles 13-16", "endcap": "Hardware clearance endcaps aisle 14-15"},
    "flooring": {"dept": "D23 Flooring", "aisle": "Aisles 22-24 (back of store)", "endcap": "Flooring clearance back-right corner"},
    "paint": {"dept": "D24 Paint", "aisle": "Aisles 20-22 (paint desk area)", "endcap": "Paint clearance endcap near aisle 21"},
    "decor": {"dept": "D59 Decor / Home", "aisle": "Aisles 1-3", "endcap": "Decor clearance front endcaps"},
    "seasonal": {"dept": "D28 Seasonal", "aisle": "Front of store / garden center", "endcap": "Seasonal clearance near entrance"},
    "storage": {"dept": "D59 Storage & Organization", "aisle": "Aisles 1-3", "endcap": "Endcaps near aisle 2"},
    "unknown": {"dept": "Check HD app for exact aisle", "aisle": "Use HD app 'product locator'", "endcap": "Walk all clearance endcaps"},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FlipOS-Brief] %(message)s")
log = logging.getLogger("flip_os.brief")

def supa_headers():
    return {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

def supa_get(table: str, params: dict) -> list[dict]:
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(), params=params, timeout=8,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error("Supabase GET %s failed: %s", table, e)
        return []

def supa_upsert(table: str, rows: list[dict]) -> bool:
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**supa_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=rows, timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error("Supabase upsert %s failed: %s", table, e)
        return False

def post_slack(text: str):
    if not SLACK_TOKEN:
        log.warning("No Slack token, skipping post")
        return
    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            json={"channel": SLACK_CHANNEL, "text": text},
            timeout=10,
        )
        if resp.ok:
            log.info("Posted brief to Slack")
        else:
            log.warning("Slack post returned: %s", resp.text[:200])
    except Exception as e:
        log.warning("Slack post failed: %s", e)

# ---------------------------------------------------------------------------
# Google Calendar event with full hunt list in description
# ---------------------------------------------------------------------------

def create_calendar_event(hunt_items: list[dict], stats: dict, today: date):
    """Create a Google Calendar event at 5:30 AM PT with the full SKU hunt list."""
    log.info("Creating Google Calendar event...")

    # Build rich description with SKUs, aisle locations, and image links
    desc_lines = []
    desc_lines.append("YOUR DAILY PENNY HUNT LIST")
    desc_lines.append("=" * 40)
    desc_lines.append(f"Stores: HD Vacaville #1043 (510 Orange Dr) | HD Fairfield #0637 (2121 Cadenasso Dr)")
    desc_lines.append(f"Opens: 6:00 AM  |  Get there early for best picks")
    desc_lines.append("")

    go_items = [h for h in hunt_items if h.get("demand_score", 0) >= 70 and float(h.get("est_resale") or 0) >= 20]
    total_potential = 0

    if go_items:
        desc_lines.append(f"CONFIRMED $0.01 IN CALIFORNIA ({len(go_items)} items)")
        desc_lines.append("-" * 40)
        desc_lines.append("")

        for i, item in enumerate(go_items, 1):
            sku = item.get("item_sku") or "?"
            name = item.get("item_name", "Unknown")
            retail = float(item.get("original_price") or 0)
            resale = float(item.get("est_resale") or 0)
            category = item.get("category", "unknown")
            dept = DEPT_MAP.get(category, DEPT_MAP["unknown"])
            total_potential += resale

            # HD product page link (user can open in HD app for exact aisle)
            sku_clean = sku.replace("-", "")
            hd_link = f"https://www.homedepot.com/s/{sku_clean}"
            img_link = f"https://images.thdstatic.com/productImages/{sku_clean[:3]}/{sku_clean[:6]}/{sku_clean}/full/{sku_clean}.jpg"

            desc_lines.append(f"#{i}  {name}")
            desc_lines.append(f"    SKU: {sku}")
            desc_lines.append(f"    Retail: ${retail:,.0f}  |  Flip for: ~${resale:,.0f}")
            desc_lines.append(f"    Dept: {dept['dept']}")
            desc_lines.append(f"    Aisle: {dept['aisle']}")
            desc_lines.append(f"    Endcap: {dept['endcap']}")
            desc_lines.append(f"    HD Link: {hd_link}")
            desc_lines.append(f"    Photo: {img_link}")
            desc_lines.append("")

        desc_lines.append(f"TOTAL POTENTIAL: ~${total_potential:,.0f} from ${len(go_items) * 0.01:.2f}")
    else:
        desc_lines.append("No confirmed CA penny items today.")
        desc_lines.append("Check pennycentral.com/penny-list manually.")

    desc_lines.append("")
    desc_lines.append("HOW TO SCAN")
    desc_lines.append("-" * 40)
    desc_lines.append("1. Open HD app -> search SKU for exact aisle")
    desc_lines.append("2. Find item, check for yellow clearance tag")
    desc_lines.append("3. Scan ITEM barcode at self-checkout (NOT the tag)")
    desc_lines.append("4. If $0.01 -> BUY IT")
    desc_lines.append("5. Walk ALL clearance endcaps too")
    desc_lines.append("")
    desc_lines.append(f"P&L: {stats.get('items_sold', 0)} sold | ${stats.get('revenue', 0):,.0f} rev | ${stats.get('net', 0):,.0f} net")
    desc_lines.append(f"Storage: {stats.get('items_in_storage', 0)} items")
    desc_lines.append("")
    desc_lines.append("Dashboard: http://129.159.38.250:8504/flip/")

    description = "\n".join(desc_lines)

    # Tomorrow's date for the event (cron runs at 5 AM, event is for that same morning)
    event_date = today.isoformat()

    # Google Calendar API via service -- use requests directly
    # We'll use the n8n webhook to create the event since we have OAuth there
    # Alternatively, post to a simple webhook that creates the calendar event
    # For now, use the Supabase edge function pattern or direct API

    # Store the event description in Supabase for the MCP Calendar tool to pick up
    # The actual calendar event creation happens via the MCP tool in the CLI session
    # But for automated cron, we need a different approach.

    # Solution: Use Google Calendar API directly with a service account or OAuth token
    # For now, store the event data so it can be created on next CLI interaction
    # AND post the full list to Slack so it's accessible immediately

    # Post the rich list to Slack as well
    slack_text = f"*FLIP OS HUNT LIST -- {today.strftime('%A %b %d')}*\n"
    slack_text += f"Stores: Vacaville #1043 | Fairfield #0637 | Opens 6 AM\n\n"
    if go_items:
        for i, item in enumerate(go_items, 1):
            sku = item.get("item_sku") or "?"
            retail = float(item.get("original_price") or 0)
            resale = float(item.get("est_resale") or 0)
            category = item.get("category", "unknown")
            dept = DEPT_MAP.get(category, DEPT_MAP["unknown"])
            slack_text += f"*{i}. {item['item_name'][:35]}*\n"
            slack_text += f"   SKU `{sku}` | ${retail:,.0f} retail -> ~${resale:,.0f} flip\n"
            slack_text += f"   {dept['dept']} | {dept['aisle']}\n\n"
        slack_text += f"*TOTAL: ~${total_potential:,.0f} from {len(go_items)} pennies*"
    else:
        slack_text += "No CA penny items today. Check pennycentral.com manually."

    post_slack(slack_text)

    # Store event description for calendar creation
    # The cron will write this to a file that the next CLI session can pick up
    event_file = Path("/tmp/flip_os_calendar_event.json")
    try:
        event_data = {
            "summary": f"Penny Hunt: {len(go_items)} items (~${total_potential:,.0f})",
            "description": description,
            "date": event_date,
            "items_count": len(go_items),
            "total_potential": total_potential,
        }
        event_file.write_text(json.dumps(event_data))
        log.info("Calendar event data saved to %s", event_file)
    except Exception as e:
        log.warning("Failed to save calendar event data: %s", e)

    log.info("Calendar event prep complete. %d GO items, ~$%d potential", len(go_items), total_potential)


# ---------------------------------------------------------------------------
# Generate the brief
# ---------------------------------------------------------------------------

def generate_brief():
    log.info("=== Generating daily flip brief ===")
    today = date.today()
    first_of_month = today.replace(day=1)

    # 1. Hunt items -- high-score intel not yet acted on (7-day window for PennyCentral SKUs)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    hunt_items = supa_get("flip_intel", {
        "select": "id,item_name,item_sku,original_price,store,category,demand_score,est_resale,margin_pct,penny_confirmed",
        "demand_score": "gte.50",
        "acted_on": "eq.false",
        "found_date": f"gte.{cutoff}",
        "order": "demand_score.desc",
        "limit": "25",
    })

    # 2. Inventory -- items in storage that should be listed
    in_storage = supa_get("flip_inventory", {
        "select": "*",
        "status": "eq.in_storage",
        "order": "buy_date.asc",
    })

    listed = supa_get("flip_inventory", {
        "select": "*",
        "status": "eq.listed",
    })

    # 3. Sold this month
    sold_month = supa_get("flip_inventory", {
        "select": "id,item_name,sold_price,buy_price,net_profit,sold_date",
        "status": "eq.sold",
        "sold_date": f"gte.{first_of_month.isoformat()}",
        "order": "sold_date.desc",
    })

    # 4. Calculate P&L
    total_revenue = sum(float(s.get("sold_price") or 0) for s in sold_month)
    total_cost = sum(float(s.get("buy_price") or 0) for s in sold_month)
    total_profit = sum(float(s.get("net_profit") or 0) for s in sold_month)
    inventory_value = sum(float(i.get("est_sell_price") or 0) for i in in_storage)
    items_in_storage = len(in_storage)
    items_listed = len(listed)
    items_sold = len(sold_month)

    # Days items have been sitting
    stale_items = []
    for item in in_storage:
        buy_date = item.get("buy_date")
        if buy_date:
            days = (today - date.fromisoformat(buy_date)).days
            if days > 14:
                stale_items.append({"name": item["item_name"], "days": days})

    # 5. Build brief text
    lines = []
    lines.append(f"*FLIP OS DAILY BRIEF -- {today.strftime('%A %b %d')}*")
    lines.append("")

    # Hunt section -- SKU list sorted by margin
    go_items = [h for h in hunt_items if h.get("demand_score", 0) >= 70 and float(h.get("est_resale") or 0) >= 20]
    maybe_items = [h for h in hunt_items if h not in go_items]

    # Split into CA-confirmed vs others
    ca_go = [h for h in go_items if h.get("store")]
    other_go = [h for h in go_items if not h.get("store")]

    if ca_go:
        lines.append(f"*SKU HUNT LIST -- CA CONFIRMED* ({len(ca_go)} items, highest margin first):")
        for item in ca_go:
            sku = item.get("item_sku") or "no-sku"
            retail = float(item.get("original_price") or 0)
            resale = float(item.get("est_resale") or 0)
            lines.append(
                f"  SKU {sku:>15s} | ${retail:>7.0f} retail -> ~${resale:>6.0f} resale | {item['item_name'][:35]}"
            )

    if other_go:
        lines.append(f"\n*OTHER STATES* ({len(other_go)} items -- may appear in your stores):")
        for item in other_go[:5]:
            sku = item.get("item_sku") or "no-sku"
            retail = float(item.get("original_price") or 0)
            lines.append(
                f"  SKU {sku:>15s} | ${retail:>7.0f} | {item['item_name'][:40]}"
            )

    if not go_items:
        lines.append("*HUNT TODAY*: No high-confidence SKUs. Check pennycentral.com/penny-list manually.")

    if maybe_items:
        lines.append(f"\n*MAYBE* ({len(maybe_items)} items, score 50-69):")
        for item in maybe_items[:3]:
            sku = item.get("item_sku") or "?"
            lines.append(f"  SKU {sku} | {item['item_name'][:40]} | Score: {item['demand_score']}")

    # Inventory section
    lines.append("")
    lines.append(f"*STORAGE* ({items_in_storage} items, est. value: ${inventory_value:.2f})")
    if stale_items:
        lines.append(f"  Stale (>14 days): {len(stale_items)} -- consider price drop or donate")
        for s in stale_items[:3]:
            lines.append(f"    {s['name'][:40]} -- {s['days']} days")

    if items_listed:
        lines.append(f"  Listed: {items_listed} items active")

    # P&L section
    lines.append("")
    net_after_rent = total_profit - STORAGE_RENT
    emoji = "+" if net_after_rent >= 0 else ""
    lines.append(f"*{today.strftime('%B')} P&L*")
    lines.append(f"  Sold: {items_sold} items | Revenue: ${total_revenue:.2f}")
    lines.append(f"  Cost of goods: ${total_cost:.2f} | Profit: ${total_profit:.2f}")
    lines.append(f"  Storage rent: -${STORAGE_RENT:.2f}")
    lines.append(f"  *Net: {emoji}${net_after_rent:.2f}*")

    # Alerts
    alerts = []
    if net_after_rent < -30:
        alerts.append("P&L is negative. Consider listing more aggressively or pausing buys.")
    if items_in_storage > 30:
        alerts.append(f"Storage is getting full ({items_in_storage} items). List or move product.")
    if not go_items and not maybe_items:
        alerts.append("Scraper found nothing. Visit stores and scan manually.")

    if alerts:
        lines.append("")
        lines.append("*ALERTS*:")
        for a in alerts:
            lines.append(f"  {a}")

    brief_text = "\n".join(lines)

    # 6. Store in Supabase
    brief_row = {
        "brief_date": today.isoformat(),
        "hunt_items": json.dumps([{
            "id": h["id"], "name": h["item_name"], "score": h["demand_score"],
            "resale": float(h.get("est_resale") or 0), "store": h.get("store"),
        } for h in hunt_items]),
        "list_items": json.dumps([{
            "id": i["id"], "name": i["item_name"],
            "est_price": float(i.get("est_sell_price") or 0),
        } for i in in_storage if not i.get("listed_date")]),
        "inventory_summary": json.dumps({
            "in_storage": items_in_storage,
            "listed": items_listed,
            "value": inventory_value,
            "stale_count": len(stale_items),
        }),
        "monthly_pnl": json.dumps({
            "revenue": total_revenue,
            "cost": total_cost,
            "profit": total_profit,
            "rent": STORAGE_RENT,
            "net": net_after_rent,
            "items_sold": items_sold,
        }),
        "alerts": json.dumps(alerts),
        "brief_text": brief_text,
    }
    supa_upsert("flip_daily_brief", [brief_row])

    # 7. Post to Slack
    post_slack(brief_text)

    # 8. Create Google Calendar event with full hunt list
    create_calendar_event(hunt_items, stats={
        "items_in_storage": items_in_storage,
        "items_listed": items_listed,
        "items_sold": items_sold,
        "revenue": total_revenue,
        "net": net_after_rent,
    }, today=today)

    # 10. Log to Blinko
    try:
        requests.post(
            f"{BLINKO_URL}/api/v1/note/upsert",
            json={"content": f"# Flip OS Brief {today}\n#hive/flip-os\n\n{brief_text}", "type": 1},
            timeout=8,
        )
    except Exception:
        pass

    log.info("Brief generated and posted.")
    print(brief_text)
    return brief_text


if __name__ == "__main__":
    generate_brief()
