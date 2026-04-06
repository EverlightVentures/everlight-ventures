"""
Rex's Zillow Keyword Scout -- generates Google search URLs for distressed properties
and optionally scrapes results to feed into the wholesale pipeline.

Usage:
    python zillow_scout.py                  # Generate search URLs CSV
    python zillow_scout.py --fetch          # Generate + fetch results
    python zillow_scout.py --market atlanta # Single market only
    python zillow_scout.py --post           # Auto-import to Django pipeline
"""

import csv
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# -- Configuration --

KEYWORDS = [
    # Distressed property keywords
    "fixer upper", "handyman special", "needs TLC", "as-is", "as is",
    "investor special", "distressed", "cash only", "motivated seller",
    "estate sale", "probate", "bank owned", "foreclosure", "REO",
    "needs work", "needs repair", "damaged", "fire damage", "water damage",
    "mold", "code violation", "tax lien", "vacant", "abandoned",
    "below market", "must sell", "price reduced", "bring all offers",
    "fixer", "rehab",
    # Land-specific keywords (from the $45k Dallas playbook)
    "vacant lot", "lot for sale", "buildable lot", "infill lot",
    "tear down", "lot value", "land value", "build your dream",
    "zoned duplex", "zoned multi-family", "land only",
]

MARKETS = {
    "st_louis": {
        "name": "St. Louis, MO",
        "avg_fee": 25000,
        "zips": ["63101", "63103", "63106", "63107", "63111", "63112",
                 "63113", "63115", "63116", "63118"],
    },
    "charlotte": {
        "name": "Charlotte / Raleigh, NC",
        "avg_fee": 22000,
        "zips": ["28205", "28206", "28208", "28212", "28213", "28215",
                 "28216", "28217", "27601", "27610"],
    },
    "atlanta": {
        "name": "Atlanta, GA",
        "avg_fee": 22000,
        "zips": ["30310", "30311", "30314", "30315", "30318", "30344",
                 "30349", "30354", "30316", "30317"],
    },
    "dallas": {
        "name": "Dallas-Fort Worth, TX",
        "avg_fee": 20000,
        "zips": ["75203", "75210", "75215", "75216", "75217", "75227",
                 "76104", "76105", "76106", "76110"],
    },
    "cleveland": {
        "name": "Cleveland, OH",
        "avg_fee": 12500,
        "zips": ["44102", "44103", "44104", "44105", "44106", "44108",
                 "44109", "44110", "44111", "44113"],
    },
    "jacksonville": {
        "name": "Jacksonville / Tampa, FL",
        "avg_fee": 15000,
        "zips": ["32202", "32204", "32205", "32206", "32208", "32209",
                 "32210", "32254", "33602", "33605"],
    },
}

AGENT_DIR = Path(__file__).parent
SEARCH_DIR = AGENT_DIR / "search_urls"
LEADS_DIR = AGENT_DIR / "daily_leads"
REPORTS_DIR = AGENT_DIR / "reports"

for d in [SEARCH_DIR, LEADS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def build_google_url(zip_code: str, keyword: str) -> str:
    """Build a Google search URL targeting Zillow listings."""
    query = f'site:zillow.com/homedetails/ {zip_code} "{keyword}"'
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"


def build_zillow_url(zip_code: str, keyword: str) -> str:
    """Build a direct Zillow search URL with keyword filter."""
    return f"https://www.zillow.com/homes/{zip_code}_rb/?searchQueryState=%7B%22keyword%22%3A%22{urllib.parse.quote(keyword)}%22%7D"


def generate_search_urls(market_key: str = None) -> list[dict]:
    """Generate all search URLs for target markets and keywords."""
    rows = []
    markets = {market_key: MARKETS[market_key]} if market_key and market_key in MARKETS else MARKETS

    for mkey, market in markets.items():
        for zip_code in market["zips"]:
            for keyword in KEYWORDS:
                rows.append({
                    "market": market["name"],
                    "market_key": mkey,
                    "zip_code": zip_code,
                    "keyword": keyword,
                    "google_url": build_google_url(zip_code, keyword),
                    "zillow_url": build_zillow_url(zip_code, keyword),
                    "avg_assignment_fee": market["avg_fee"],
                })
    return rows


def save_search_csv(rows: list[dict], label: str = "") -> Path:
    """Save search URLs to a dated CSV."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    suffix = f"_{label}" if label else ""
    path = SEARCH_DIR / f"{today}_search_urls{suffix}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def generate_daily_report(rows: list[dict]) -> str:
    """Generate Rex's daily scout report."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    market_counts = {}
    for r in rows:
        mkey = r["market_key"]
        market_counts[mkey] = market_counts.get(mkey, 0) + 1

    report = f"# Rex's Daily Scout Report -- {today}\n\n"
    report += f"## Search URLs Generated: {len(rows)}\n\n"
    report += "| Market | Zip Codes | Keywords | URLs | Avg Fee |\n"
    report += "|--------|-----------|----------|------|---------|\n"

    for mkey, market in MARKETS.items():
        count = market_counts.get(mkey, 0)
        report += f"| {market['name']} | {len(market['zips'])} | {len(KEYWORDS)} | {count} | ${market['avg_fee']:,} |\n"

    report += f"\n**Total search combinations: {len(rows)}**\n"
    report += f"\nCSV saved to: `search_urls/{today}_search_urls.csv`\n"
    report += "\n## Next Steps\n"
    report += "1. Open the CSV and click through the top Google/Zillow URLs\n"
    report += "2. Flag any properties with distress signals\n"
    report += "3. Import flagged leads to `/broker/wholesale/` via CSV upload\n"
    report += "4. Run scoring + buyer matching from the dashboard\n"

    return report


def post_to_slack(message: str) -> bool:
    """Post to #wholesale-deals Slack channel."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_WHOLESALE", "")
    if not webhook_url:
        # Fall back to general alerts webhook
        webhook_url = os.environ.get("SLACK_WEBHOOK_ALERTS", "")
    if not webhook_url:
        print("[Rex] No Slack webhook configured, skipping post")
        return False

    import requests
    try:
        r = requests.post(webhook_url, json={"text": message}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[Rex] Slack post failed: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Rex's Zillow Keyword Scout")
    parser.add_argument("--market", type=str, help="Single market key (e.g. atlanta, dallas)")
    parser.add_argument("--fetch", action="store_true", help="Fetch and parse results (requires network)")
    parser.add_argument("--post", action="store_true", help="Auto-import to Django pipeline")
    parser.add_argument("--slack", action="store_true", help="Post report to Slack")
    args = parser.parse_args()

    print("[Rex] Generating search URLs...")
    rows = generate_search_urls(args.market)
    csv_path = save_search_csv(rows, args.market or "all")
    print(f"[Rex] Saved {len(rows)} search URLs to {csv_path}")

    report = generate_daily_report(rows)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"{today}_daily.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[Rex] Daily report saved to {report_path}")

    if args.slack:
        slack_msg = (
            f"*Rex's Daily Scout -- {today}*\n"
            f"Generated {len(rows)} search URLs across {len(MARKETS)} markets.\n"
            f"Top markets: St. Louis ($25k avg), Charlotte ($22k), Atlanta ($22k)\n"
            f"CSV ready for review. Import leads at /broker/wholesale/"
        )
        post_to_slack(slack_msg)

    print("[Rex] Done. Go find some ugly houses.")


if __name__ == "__main__":
    main()
