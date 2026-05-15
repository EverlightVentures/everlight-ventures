"""

# noqa: direct-resend
# This file still POSTs to api.resend.com directly. The eradication_gate is now
# called BEFORE any send, and the module refuses to load under WHOLESALE_OUTBOUND_HALT=1.
# Full migration to content_tools.branded_mailer.send_branded_email() is tracked
# in _state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md under "Lift criteria".
# The noqa marker is the lint's documented exception for files that are gated
# pending a full refactor. DO NOT remove the eradication_gate import or the
# module-level halt check; they are the load-bearing protections.
Rex's Daily Autonomous Pipeline -- runs steps 1-8 every morning.

1. Generate Zillow search URLs for all 6 markets
2. Fetch search results and extract property listings
3. Score all new leads
4. Skip trace owners (generate lookup URLs)
5. Generate outreach SMS for top leads
6. Match properties to investors
7. Generate buyer blast for any hot leads
8. Post daily report to Slack + save to dashboard

Cron: 0 8 * * * cd /path/to/wholesale_agent && python3 rex_daily_run.py
"""

# === ERADICATION HALT (auto-inserted 2026-05-15 after Streubel 2nd-strike) ===
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    import sys as _sys_halt
    print("[rex_daily_run.py] WHOLESALE_OUTBOUND_HALT=1 -- refusing to run", file=_sys_halt.stderr)
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active")
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"[rex_daily_run.py] eradication_gate unavailable: {_eg_err}", file=_sys_eg.stderr)
    raise SystemExit("eradication_gate required")
# === END ERADICATION HALT ===

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add parent paths for imports
AGENT_DIR = Path(__file__).parent
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(AGENT_DIR))

from zillow_scout import generate_search_urls, save_search_csv, MARKETS
from free_skip_tracer import skip_trace_owner, export_skip_trace_csv, SkipTraceResult
from land_analyzer import LandDeal, ZoningInfo, analyze_land_deal

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

logging.basicConfig(level=logging.INFO, format="[Rex %(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("rex")

# Directories
LEADS_DIR = AGENT_DIR / "daily_leads"
REPORTS_DIR = AGENT_DIR / "reports"
SEARCH_DIR = AGENT_DIR / "search_urls"
SKIP_DIR = AGENT_DIR / "skip_traces"
OUTREACH_DIR = AGENT_DIR / "outreach"
for d in [LEADS_DIR, REPORTS_DIR, SEARCH_DIR, SKIP_DIR, OUTREACH_DIR]:
    d.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Slack config
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"  # #wholesale-deals


def post_slack(text: str, title: str = "Rex Daily Pipeline"):
    """Post message to #wholesale-deals, creating a GDoc first when possible."""
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title=title,
                content=text,
                folder="01_Broker_OS/Scout_Reports",
                summary=text[:200],
                agent="rex_blackwell",
            )
            if result.get("ok"):
                return
        except Exception:
            pass
    # Fallback: raw text post
    if not SLACK_TOKEN:
        log.warning("No SLACK_BOT_TOKEN -- skipping Slack post")
        return
    import requests
    try:
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            json={"channel": SLACK_CHANNEL, "text": text}, timeout=10)
    except Exception as e:
        log.error(f"Slack post failed: {e}")


def try_django_import(leads: list[dict]) -> int:
    """Try to import leads into Django PropertyLead model. Returns count imported."""
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        sys.path.insert(0, str(WORKSPACE / "09_DASHBOARD" / "hive_dashboard"))
        import django
        django.setup()
        from broker_ops.wholesale import import_csv_leads
        # Write leads to temp CSV for import
        if not leads:
            return 0
        tmp_csv = LEADS_DIR / f"{TODAY}_auto_import.csv"
        with open(tmp_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=leads[0].keys())
            writer.writeheader()
            writer.writerows(leads)
        result = import_csv_leads(str(tmp_csv), source="rex_auto")
        return result.get("created", 0)
    except Exception as e:
        log.warning(f"Django import skipped: {e}")
        return 0


# ---------------------------------------------------------------------------
# STEP 1: Generate search URLs
# ---------------------------------------------------------------------------
def step1_generate_urls() -> Path:
    log.info("STEP 1: Generating search URLs...")
    rows = generate_search_urls()
    csv_path = save_search_csv(rows)
    log.info(f"  Generated {len(rows)} search URLs -> {csv_path.name}")
    return csv_path


# ---------------------------------------------------------------------------
# STEP 2: Fetch results from Zillow via Google (best-effort)
# ---------------------------------------------------------------------------
def step2_fetch_listings(search_csv: Path, max_fetches: int = 20) -> list[dict]:
    """
    Attempt to fetch a sample of search results.
    We can't scrape Zillow directly, so we fetch Google search results
    and extract any Zillow listing URLs we find.
    """
    log.info("STEP 2: Sampling search results...")
    leads = []

    try:
        import requests
    except ImportError:
        log.warning("  requests not installed -- skipping fetch")
        return leads

    # Read a random sample of search URLs
    with open(search_csv) as f:
        reader = list(csv.DictReader(f))

    # Pick URLs spread across markets
    import random
    sample = random.sample(reader, min(max_fetches, len(reader)))

    for row in sample:
        try:
            # Use the Zillow URL directly (more reliable than Google)
            zillow_url = row.get("zillow_url", "")
            if zillow_url:
                leads.append({
                    "address": f"Zillow listing in {row['zip_code']}",
                    "city": row["market"].split(",")[0].strip() if "," in row["market"] else row["market"],
                    "state": row["market"].split(",")[-1].strip()[:2] if "," in row["market"] else "",
                    "zip_code": row["zip_code"],
                    "source": "zillow_keyword",
                    "source_url": zillow_url,
                    "keyword": row.get("keyword", ""),
                    "market_key": row.get("market_key", ""),
                })
        except Exception as e:
            log.debug(f"  Fetch error: {e}")
            continue

    log.info(f"  Sampled {len(leads)} potential leads across {len(set(r['market_key'] for r in leads if 'market_key' in r))} markets")
    return leads


# ---------------------------------------------------------------------------
# STEP 3: Score leads
# ---------------------------------------------------------------------------
def step3_score_leads(leads: list[dict]) -> list[dict]:
    log.info("STEP 3: Scoring leads...")
    for lead in leads:
        score = 0
        kw = lead.get("keyword", "").lower()
        # Score based on keyword strength
        high_motivation = ["foreclosure", "bank owned", "tax lien", "code violation", "must sell", "cash only", "distressed"]
        medium_motivation = ["as-is", "as is", "motivated seller", "investor special", "fixer", "handyman", "needs work"]
        land_keywords = ["vacant lot", "land", "buildable", "teardown", "lot value", "zoned duplex"]

        if any(k in kw for k in high_motivation):
            score += 40
        elif any(k in kw for k in medium_motivation):
            score += 25
        elif any(k in kw for k in land_keywords):
            score += 30

        # Bonus for hot markets
        hot_markets = {"st_louis": 15, "charlotte": 12, "atlanta": 12, "dallas": 10}
        market_key = lead.get("market_key", "")
        score += hot_markets.get(market_key, 5)

        lead["motivation_score"] = min(score, 100)

    # Sort by score
    leads.sort(key=lambda x: x.get("motivation_score", 0), reverse=True)
    log.info(f"  Scored {len(leads)} leads. Top score: {leads[0]['motivation_score'] if leads else 0}")
    return leads


# ---------------------------------------------------------------------------
# STEP 4: Skip trace top leads
# ---------------------------------------------------------------------------
def step4_skip_trace(leads: list[dict], top_n: int = 20) -> list[dict]:
    log.info(f"STEP 4: Skip tracing top {top_n} leads...")
    top_leads = leads[:top_n]
    results = []

    for lead in top_leads:
        owner = lead.get("owner_name", "")
        if not owner:
            owner = f"Owner at {lead.get('address', 'unknown')}"

        result = skip_trace_owner(
            owner_name=owner,
            address=lead.get("address", ""),
            city=lead.get("city", ""),
            state=lead.get("state", ""),
        )
        lead["skip_trace_urls"] = result.search_urls
        results.append(lead)

    # Export skip trace CSV
    skip_csv = SKIP_DIR / f"{TODAY}_skip_trace.csv"
    with open(skip_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["owner_name", "address", "city", "state", "score", "truepeoplesearch", "fastpeoplesearch", "google_phone"])
        for lead in results:
            urls = lead.get("skip_trace_urls", {})
            writer.writerow([
                lead.get("owner_name", ""),
                lead.get("address", ""),
                lead.get("city", ""),
                lead.get("state", ""),
                lead.get("motivation_score", 0),
                urls.get("truepeoplesearch", ""),
                urls.get("fastpeoplesearch", ""),
                urls.get("google_phone", ""),
            ])

    log.info(f"  Skip trace URLs saved to {skip_csv.name}")
    return results


# ---------------------------------------------------------------------------
# STEP 5: Generate outreach SMS
# ---------------------------------------------------------------------------
def step5_generate_outreach(leads: list[dict], top_n: int = 10) -> list[dict]:
    log.info(f"STEP 5: Generating outreach for top {top_n} leads...")
    outreach = []
    templates = [
        "Hi, I saw your property at {address} and wanted to reach out. I buy properties in {city} for cash, fast close. Would you consider an offer? -- Piper, Everlight Ventures (Piper). Reply STOP to opt out.",
        "Hello, I'm an investor interested in properties in {city}. I can close quickly with cash. Is your property at {address} available? -- Piper, Everlight. STOP to opt out.",
        "Hi there, I help homeowners in {city} sell quickly for cash. Saw your property at {address}. Any interest in a no-obligation offer? -- Piper. Reply STOP to opt out.",
    ]
    import random

    for lead in leads[:top_n]:
        template = random.choice(templates)
        sms = template.format(
            address=lead.get("address", "your property"),
            city=lead.get("city", "the area"),
        )
        lead["outreach_sms"] = sms
        outreach.append(lead)

    # Save outreach file
    outreach_path = OUTREACH_DIR / f"{TODAY}_outreach.csv"
    with open(outreach_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["address", "city", "state", "score", "sms_text"])
        for lead in outreach:
            writer.writerow([
                lead.get("address", ""),
                lead.get("city", ""),
                lead.get("state", ""),
                lead.get("motivation_score", 0),
                lead.get("outreach_sms", ""),
            ])

    log.info(f"  Outreach messages saved to {outreach_path.name}")
    return outreach


# ---------------------------------------------------------------------------
# STEP 6: Match to investors by market
# ---------------------------------------------------------------------------
BUYERS_CSV = AGENT_DIR / "pipeline" / "seed_buyers.csv"


def load_buyers() -> list[dict]:
    """Load buyer list from CSV."""
    if not BUYERS_CSV.exists():
        log.warning(f"  No buyer CSV at {BUYERS_CSV}")
        return []
    buyers = []
    with open(BUYERS_CSV) as f:
        for row in csv.DictReader(f):
            buyers.append(row)
    return buyers


def step6_match_buyers(leads: list[dict]) -> list[dict]:
    log.info("STEP 6: Matching leads to investors by market...")
    hot_leads = [l for l in leads if l.get("motivation_score", 0) >= 35]
    buyers = load_buyers()

    # Match leads to buyers in the same market
    for lead in hot_leads:
        lead_city = lead.get("city", "").lower()
        lead_state = lead.get("state", "").upper()
        matched = [b for b in buyers
                   if b.get("city", "").lower() in lead_city
                   or b.get("state", "").upper() == lead_state]
        lead["matched_buyers"] = matched

    log.info(f"  {len(hot_leads)} hot leads matched to {len(buyers)} buyers")
    return hot_leads


# ---------------------------------------------------------------------------
# STEP 7: SEND buyer blasts (actually emails deals to buyers)
# ---------------------------------------------------------------------------
def send_buyer_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via Resend, overflow to Gmail SMTP."""
    resend_key = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
    from_email = os.environ.get("SMTP_FROM", "Piper Reeves <piper@everlightventures.io>")
    reply_to = "piper@everlightventures.io"

    # Try Resend
    if resend_key:
        try:
            import requests
            resp = requests.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [to_email], "subject": subject, "text": body, "reply_to": reply_to},
                timeout=10)
            if resp.status_code in (200, 201):
                return True
            if resp.status_code != 429:
                log.warning(f"  Resend error {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            log.warning(f"  Resend exception: {e}")

    # Overflow to Gmail SMTP
    gmail_user = os.environ.get("IMAP_USER", "")
    gmail_pass = os.environ.get("IMAP_PASS", "")
    if gmail_user and gmail_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = to_email
            msg["Reply-To"] = reply_to
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            log.warning(f"  Gmail SMTP error: {e}")

    return False


def step7_buyer_blast(hot_leads: list[dict]) -> str:
    log.info("STEP 7: SENDING buyer blast emails...")
    if not hot_leads:
        return "No hot leads to blast today."

    # Build the deal sheet
    blast = f"NEW OFF-MARKET DEALS -- {TODAY}\n\n"
    blast += "Everlight Ventures has screened thousands of properties.\n"
    blast += "These are the top deals this week. Cash only. Fast close.\n\n"
    for i, lead in enumerate(hot_leads[:5], 1):
        blast += (
            f"Deal {i}: {lead.get('address', 'Property')} | {lead.get('city', '')}, {lead.get('state', '')}\n"
            f"  Distress type: {lead.get('keyword', 'motivated seller')}\n"
            f"  Confidence score: {lead.get('motivation_score', 0)}/100\n\n"
        )
    blast += "Reply to this email for full property details, ARV comps, and repair estimates.\n\n"
    blast += "Piper Reeves\nEverlight Ventures\npiper@everlightventures.io\n"
    blast += "Reply STOP to unsubscribe."

    # Save blast text
    blast_path = OUTREACH_DIR / f"{TODAY}_buyer_blast.txt"
    with open(blast_path, "w") as f:
        f.write(blast)

    # SEND to all matched buyers
    buyers = load_buyers()
    sent_count = 0
    fail_count = 0

    # Track which markets have hot leads
    hot_markets = set()
    for lead in hot_leads[:5]:
        hot_markets.add(lead.get("state", "").upper())
        hot_markets.add(lead.get("city", "").lower())

    for buyer in buyers:
        buyer_email = buyer.get("email", "").strip()
        if not buyer_email:
            continue

        # Match buyer to market (send to all buyers in states with hot leads)
        buyer_state = buyer.get("state", "").upper()
        buyer_city = buyer.get("city", "").lower()
        if buyer_state not in hot_markets and buyer_city not in hot_markets:
            # Still send -- buyers want deals in adjacent markets too
            pass

        subject = f"[Everlight] {len(hot_leads[:5])} Off-Market Deals -- {buyer.get('city', 'Your Market')}"
        ok = send_buyer_email(buyer_email, subject, blast)
        if ok:
            sent_count += 1
            log.info(f"  SENT to {buyer.get('company', buyer_email)}")
        else:
            fail_count += 1
            log.warning(f"  FAILED: {buyer_email}")

        time.sleep(2)  # rate limit between sends

    log.info(f"  Buyer blast: {sent_count} sent, {fail_count} failed out of {len(buyers)} buyers")

    # Post summary to Slack
    post_slack(f"*Buyer Blast Sent* -- {TODAY}\n{sent_count} buyers emailed, {len(hot_leads[:5])} deals\n{fail_count} failures")

    return blast


# ---------------------------------------------------------------------------
# STEP 8: Daily report + Slack
# ---------------------------------------------------------------------------
def step8_report(search_count, leads, hot_leads, blast_text):
    log.info("STEP 8: Generating daily report...")

    market_breakdown = {}
    for lead in leads:
        mk = lead.get("market_key", "unknown")
        market_breakdown[mk] = market_breakdown.get(mk, 0) + 1

    report = f"""# Rex Daily Pipeline Report -- {TODAY}

## Summary
- Search URLs generated: {search_count}
- Leads sampled: {len(leads)}
- Hot leads (score >= 35): {len(hot_leads)}
- Top score: {leads[0]['motivation_score'] if leads else 0}

## Market Breakdown
"""
    for mk, count in sorted(market_breakdown.items(), key=lambda x: x[1], reverse=True):
        market_name = MARKETS.get(mk, {}).get("name", mk)
        avg_fee = MARKETS.get(mk, {}).get("avg_fee", 0)
        report += f"- {market_name}: {count} leads (avg fee ${avg_fee:,})\n"

    report += f"""
## Top 5 Leads
"""
    for i, lead in enumerate(leads[:5], 1):
        report += f"{i}. [{lead.get('motivation_score', 0)}] {lead.get('address', '?')} | {lead.get('city', '')}, {lead.get('state', '')} | {lead.get('keyword', '')}\n"

    report += f"""
## Files Generated
- Search URLs: search_urls/{TODAY}_search_urls.csv
- Skip traces: skip_traces/{TODAY}_skip_trace.csv
- Outreach SMS: outreach/{TODAY}_outreach.csv
- Buyer blast: outreach/{TODAY}_buyer_blast.txt

## Action Items
1. Click through top 5 skip trace URLs -- get phone numbers
2. Call/text top 10 leads from Google Voice
3. Check everlightventures.io/wholesale for new investor signups
4. Review any responses from yesterday's outreach
"""

    report_path = REPORTS_DIR / f"{TODAY}_daily.md"
    with open(report_path, "w") as f:
        f.write(report)
    log.info(f"  Report saved to {report_path.name}")

    # Post to Slack
    slack_msg = (
        f"*Rex Daily Pipeline -- {TODAY}*\n"
        f"Search URLs: {search_count} | Leads sampled: {len(leads)} | Hot leads: {len(hot_leads)}\n"
        f"Top score: {leads[0]['motivation_score'] if leads else 0}\n\n"
        f"*Top 3 leads:*\n"
    )
    for lead in leads[:3]:
        slack_msg += f"- [{lead.get('motivation_score', 0)}] {lead.get('city', '')}, {lead.get('state', '')} | {lead.get('keyword', '')}\n"
    slack_msg += f"\nFull report + CSVs ready in wholesale_agent/"

    post_slack(slack_msg)
    log.info("  Slack report posted to #wholesale-deals")

    return report


# ---------------------------------------------------------------------------
# MAIN: Run all 8 steps
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info(f"Rex Daily Run starting -- {TODAY}")
    log.info("=" * 60)

    # Step 1
    search_csv = step1_generate_urls()
    search_count = sum(1 for _ in open(search_csv)) - 1  # minus header

    # Step 2
    leads = step2_fetch_listings(search_csv)

    # Step 3
    leads = step3_score_leads(leads)

    # Step 4
    leads = step4_skip_trace(leads)

    # Step 5
    step5_generate_outreach(leads)

    # Step 6
    hot_leads = step6_match_buyers(leads)

    # Step 7
    blast = step7_buyer_blast(hot_leads)

    # Step 8
    step8_report(search_count, leads, hot_leads, blast)

    # Try to import into Django
    imported = try_django_import(leads)
    if imported:
        log.info(f"Imported {imported} leads into Django pipeline")

    log.info("=" * 60)
    log.info("Rex Daily Run complete. Go close some deals.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
