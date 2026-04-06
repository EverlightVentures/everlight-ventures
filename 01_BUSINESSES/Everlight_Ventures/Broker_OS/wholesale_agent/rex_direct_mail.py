"""
Rex Direct Mail -- bypass email blockers with physical mail and manual search URLs.

134 real property owners from ATTOM, 0 emails. TruePeopleSearch blocks automated
scraping. This script generates:

1. Personalized physical letters (one per owner) for printing and mailing ($0.73/stamp)
2. Google search URLs per owner for manual email lookup (~30 sec per owner)

Letters are pain-point-aware based on lead_type, use Everlight Ventures letterhead,
and look professional -- not a "we buy houses" mailer.

Cost analysis at 134 leads:
  - Stamps: 134 x $0.73 = $97.82
  - Paper/envelopes: ~$15
  - Total: ~$113 for 134 personalized letters
  - Expected response rate: 1-3% = 1-4 responses
  - One wholesale deal = $5k-$15k profit
  - ROI: 44x-133x on the mail spend

Usage:
  python3 rex_direct_mail.py                   # generate all outputs
  python3 rex_direct_mail.py --letters-only     # just the letters
  python3 rex_direct_mail.py --search-only      # just the CSV with search URLs
"""

import csv
import json
import logging
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="[Rex Mail %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_mail")

AGENT_DIR = Path(__file__).parent
MAIL_DIR = AGENT_DIR / "direct_mail"
MAIL_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TODAY_DISPLAY = datetime.now(timezone.utc).strftime("%B %d, %Y")

# Source files
ATTOM_LEADS = AGENT_DIR / "pipeline" / "attom_real_leads.json"
LEADS_DB = AGENT_DIR / "leads_db.json"


# ---------------------------------------------------------------------------
# LETTERHEAD
# ---------------------------------------------------------------------------

LETTERHEAD = """
================================================================================
                         EVERLIGHT VENTURES
                    Real Estate Acquisitions Division

                    support@everlightventures.io
                    everlightventures.io/wholesale
================================================================================

{date}

{owner_name}
{mailing_address}


"""

CLOSING = """
If you are interested, simply reply to this letter or reach out directly:

    Email:  support@everlightventures.io
    Web:    everlightventures.io/wholesale

We respond within 24 hours. No obligation. No pressure.

Sincerely,

Rich
Acquisitions Manager
Everlight Ventures
"""


# ---------------------------------------------------------------------------
# PAIN-AWARE LETTER BODIES
# ---------------------------------------------------------------------------

LETTER_BODIES = {
    "high_equity": """Dear {first_name},

I am writing to you about your property at {property_address}.

I work with a small team of investors at Everlight Ventures, and we buy properties
in {city} for cash. We have been actively acquiring properties in your area and
yours stood out as one we would like to make an offer on.

Here is what we offer:
  -- Cash payment, no financing delays
  -- Close in as little as 7 days (or on your timeline)
  -- We buy as-is -- no repairs, no cleaning, no showings
  -- No realtor commissions or closing costs on your end

If you have been thinking about selling, or if you are curious what a cash offer
would look like, I would welcome a conversation. There is no obligation and no
pressure. I am happy to walk you through the process.
""",

    "pre_foreclosure": """Dear {first_name},

I am reaching out about your property at {property_address}.

I understand that financial situations can change unexpectedly, and I want you
to know there is an option that could help. At Everlight Ventures, we specialize
in helping homeowners who need to sell quickly.

Here is what we can do:
  -- Close before any auction date
  -- Cash payment in as little as 5 business days
  -- We handle all paperwork and closing costs
  -- Your credit stays protected with a clean sale
  -- No repairs, no showings, no commissions

I have helped many homeowners in {city} resolve difficult situations with dignity
and speed. If you would like to explore this option, please reach out. Everything
is confidential.
""",

    "tax_lien": """Dear {first_name},

I am writing regarding your property at {property_address}.

I work with property owners in {city} who have outstanding tax balances and want
a clean resolution. At Everlight Ventures, we buy properties for cash and handle
the back taxes at closing -- so you walk away free and clear.

Here is how it works:
  -- We pay cash for the property as-is
  -- We cover the outstanding taxes at closing
  -- You receive a check with zero out-of-pocket costs
  -- Close in 7-14 days (or on your schedule)
  -- No repairs, no agents, no commissions

Back taxes accrue interest and penalties every month. A quick cash sale stops the
bleeding and puts money in your pocket instead. If this sounds helpful, I would
be glad to discuss the details.
""",

    "code_violation": """Dear {first_name},

I am reaching out about your property at {property_address}.

I noticed there may be some open code issues on the property, and I know from
experience that city fines add up fast. At Everlight Ventures, we buy properties
in {city} as-is -- code violations and all.

What we offer:
  -- Cash purchase, close in 7 days
  -- We buy with all code violations in place
  -- No repairs or remediation required on your end
  -- City fines stop accruing the day we close
  -- No commissions or closing costs for you

If those fines are weighing on you, I can make them go away this month. Just
reach out and I will walk you through a no-obligation offer.
""",

    "probate": """Dear {first_name},

I am sorry for your loss, and I am writing with respect about the property at
{property_address}.

I work with families in {city} who have inherited a property and want a simple
resolution. At Everlight Ventures, we buy inherited properties for cash, as-is,
with no hassle on your end.

Here is what that looks like:
  -- No cleaning out the property -- we handle it
  -- No repairs or updates needed
  -- No showings, no agents, no commissions
  -- Cash payment, close on your timeline
  -- We work with the probate process if needed

Dealing with an inherited property on top of everything else can be overwhelming.
I can take it off your plate quickly and simply. Whenever you are ready --
whether that is now or months from now -- please feel free to reach out.
""",

    "vacant": """Dear {first_name},

I am writing about your property at {property_address}.

I understand you may not be using this property currently, and I know that
an empty property still costs money every month -- taxes, insurance, upkeep,
liability. At Everlight Ventures, we buy vacant properties for cash.

What we offer:
  -- Cash payment, fast close (7-14 days)
  -- We buy in any condition -- no cleanup required
  -- No agent commissions or closing costs on your end
  -- Stop paying carrying costs on a property you are not using

Every month that property sits empty is money going out with nothing coming in.
I can turn it into a check for you. If you are interested, or just want to
hear a number, please reach out.
""",

    "absentee": """Dear {first_name},

I am reaching out about your property at {property_address}.

Managing a property from a distance is not easy -- finding reliable tenants,
handling repairs from afar, dealing with contractors you cannot supervise in
person. At Everlight Ventures, we buy rental and investment properties for cash.

Here is what we offer:
  -- Cash, no financing contingencies
  -- Close in 7-14 days or on your timeline
  -- Buy as-is -- no repairs, no cleanup
  -- No agent commissions or closing costs
  -- One clean transaction, then no more headaches

If managing this property remotely has become more trouble than it is worth, I
can take it off your hands quickly. Just reach out and I will make you a fair
offer.
""",

    "expired_listing": """Dear {first_name},

I am writing about your property at {property_address}.

I saw that this property was recently on the market but did not sell. I know
how frustrating that can be -- months of showings, open houses, and waiting,
only to end up back at square one.

I am a different kind of buyer:
  -- I pay cash -- no financing that falls through
  -- Close in 7-14 days, not 60-90
  -- Buy as-is -- no inspection contingencies
  -- No agent commissions on your end
  -- No more showings or strangers in your home

The traditional market did not deliver. Let me show you what a direct cash
sale looks like instead. Reply to this letter or email me anytime.
""",

    "divorce": """Dear {first_name},

I am writing about your property at {property_address}.

I understand you may need to resolve the property situation quickly, and I
want you to know there is a clean, fast option. At Everlight Ventures, we
buy properties for cash with no complications.

What we offer:
  -- Cash sale, close in 7-14 days
  -- Clean split -- check goes where you direct it
  -- No repairs, no showings, no drawn-out process
  -- No agent commissions or closing costs

A fast sale can simplify everything. If you would like to hear a no-obligation
offer, please reach out at your convenience. Everything is handled
professionally and confidentially.
""",
}

# Default for any lead type not in the dict above
DEFAULT_LETTER_BODY = LETTER_BODIES["high_equity"]


# ---------------------------------------------------------------------------
# LETTER GENERATION
# ---------------------------------------------------------------------------

def load_leads() -> list[dict]:
    """Load leads from ATTOM file first, fall back to leads_db.json."""
    if ATTOM_LEADS.exists():
        data = json.loads(ATTOM_LEADS.read_text())
        log.info(f"Loaded {len(data)} leads from {ATTOM_LEADS.name}")
        return data

    if LEADS_DB.exists():
        data = json.loads(LEADS_DB.read_text())
        log.info(f"Loaded {len(data)} leads from {LEADS_DB.name}")
        return data

    log.error("No leads file found")
    return []


def get_mailing_address(lead: dict) -> str:
    """
    Build mailing address from lead data.

    ATTOM leads have the property address. For owner-occupied properties,
    that IS the mailing address. For absentee owners, ATTOM expanded profile
    would have a separate mailing address -- but our current data uses property
    address as the best available.
    """
    # Check if lead has a separate mailing address field
    if lead.get("owner_mailing"):
        return lead["owner_mailing"]

    # Use property address
    parts = [lead.get("address", "")]
    city = lead.get("city", "")
    state = lead.get("state", "")
    zip_code = lead.get("zip_code", "")

    if city or state or zip_code:
        city_line = ", ".join(filter(None, [city, state]))
        if zip_code:
            city_line = f"{city_line} {zip_code}" if city_line else zip_code
        parts.append(city_line)

    return "\n".join(parts)


def generate_letter(lead: dict) -> str:
    """Generate a single personalized letter for a lead."""
    owner_name = lead.get("owner_name", "Property Owner")
    first_name = owner_name.split()[0].title() if owner_name else "there"

    # Skip LLC/corporate owners for mail -- they need a different approach
    # Use word-boundary matching to avoid false positives (e.g. PRINCE matching INC)
    corp_signals = ["LLC", "INC", "CORP", "TRUST", "LP", "PARTNERS", "HOLDINGS",
                    "PROPERTIES", "SERVICES", "INVESTMENTS", "CAPITAL", "GROUP",
                    "MANAGEMENT", "REALTY", "ENTERPRISES"]
    upper_name = owner_name.upper()
    is_corporate = any(re.search(r'\b' + sig + r'\b', upper_name) for sig in corp_signals)
    if is_corporate:
        first_name = "Property Owner"

    mailing_address = get_mailing_address(lead)
    property_address = lead.get("address", "your property")
    city = lead.get("city", "the area")
    lead_type = lead.get("lead_type", "high_equity")

    # Get the right letter body
    body_template = LETTER_BODIES.get(lead_type, DEFAULT_LETTER_BODY)
    body = body_template.format(
        first_name=first_name,
        property_address=property_address,
        city=city,
    )

    closing = CLOSING

    letter = LETTERHEAD.format(
        date=TODAY_DISPLAY,
        owner_name=owner_name.title(),
        mailing_address=mailing_address,
    )
    letter += body + closing

    return letter


def generate_all_letters(leads: list[dict]) -> Path:
    """
    Generate all letters as a single text file, one per page.
    Page breaks are marked with form-feed characters for printing.
    """
    letters = []
    skipped_no_address = 0
    skipped_corporate = 0
    generated = 0

    for lead in leads:
        if not lead.get("address"):
            skipped_no_address += 1
            continue

        letter = generate_letter(lead)
        letters.append(letter)
        generated += 1

    # Join with page breaks
    output = "\f\n".join(letters)

    out_path = MAIL_DIR / f"{TODAY}_letters.txt"
    out_path.write_text(output)

    log.info(
        f"Generated {generated} letters -> {out_path.name} "
        f"(skipped: {skipped_no_address} no address)"
    )
    return out_path


# ---------------------------------------------------------------------------
# GOOGLE SEARCH URL GENERATION (for manual email lookup)
# ---------------------------------------------------------------------------

def generate_search_urls(leads: list[dict]) -> Path:
    """
    Generate a CSV with Google search URLs for each owner.

    Each row has: owner_name, property_address, city, state, google_email_url,
    google_phone_url, linkedin_url, facebook_url

    The user clicks each URL, scans results for ~30 seconds, and pastes any
    email found into the CSV or leads_db.json.
    """
    rows = []

    for lead in leads:
        owner = lead.get("owner_name", "")
        if not owner or len(owner) < 3:
            continue

        city = lead.get("city", "")
        state = lead.get("state", "")
        address = lead.get("address", "")

        # Skip corporate entities -- need different search strategy
        corp_signals = ["LLC", "INC", "CORP", "TRUST", "LP", "PARTNERS",
                        "HOLDINGS", "PROPERTIES", "SERVICES"]
        is_corporate = any(re.search(r'\b' + sig + r'\b', owner.upper()) for sig in corp_signals)

        if is_corporate:
            # For businesses, search for company email
            email_query = f"{owner} {city} {state} email contact"
            phone_query = f"{owner} {city} {state} phone number"
            linkedin_query = f"site:linkedin.com {owner} {city}"
            facebook_query = ""
        else:
            # For individuals, search name + location + email
            email_query = f"{owner} {city} {state} email"
            phone_query = f"{owner} {city} {state} phone"
            linkedin_query = f"site:linkedin.com {owner} {city} {state}"
            facebook_query = f"site:facebook.com {owner} {city} {state}"

        rows.append({
            "owner_name": owner,
            "address": address,
            "city": city,
            "state": state,
            "arv": lead.get("arv", lead.get("estimated_arv", 0)),
            "lead_type": lead.get("lead_type", ""),
            "is_corporate": is_corporate,
            "google_email_url": f"https://www.google.com/search?q={quote(email_query)}",
            "google_phone_url": f"https://www.google.com/search?q={quote(phone_query)}",
            "linkedin_url": f"https://www.google.com/search?q={quote(linkedin_query)}",
            "facebook_url": f"https://www.google.com/search?q={quote(facebook_query)}" if facebook_query else "",
            "found_email": "",  # user fills this in
            "found_phone": "",  # user fills this in
        })

    out_path = MAIL_DIR / f"{TODAY}_owner_search_urls.csv"
    if rows:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    log.info(f"Generated {len(rows)} search URL rows -> {out_path.name}")
    return out_path


# ---------------------------------------------------------------------------
# ENVELOPE LABELS (for printing on Avery 5160 labels)
# ---------------------------------------------------------------------------

def generate_envelope_labels(leads: list[dict]) -> Path:
    """
    Generate a CSV formatted for Avery 5160 label printing.
    3 columns x 10 rows = 30 labels per sheet.
    Each label has: owner_name, address line 1, city/state/zip.
    """
    rows = []
    for lead in leads:
        if not lead.get("address"):
            continue
        owner = lead.get("owner_name", "Property Owner").title()
        # Parse address -- ATTOM format: "123 MAIN ST, CITY, ST ZIP"
        full_addr = lead.get("address", "")
        city = lead.get("city", "")
        state = lead.get("state", "")
        zip_code = lead.get("zip_code", "")

        # Remove city/state from address if they are embedded
        street = full_addr.split(",")[0].strip() if "," in full_addr else full_addr

        rows.append({
            "name": owner,
            "street": street.title(),
            "city_state_zip": f"{city.title()}, {state} {zip_code}",
        })

    out_path = MAIL_DIR / f"{TODAY}_envelope_labels.csv"
    if rows:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "street", "city_state_zip"])
            writer.writeheader()
            writer.writerows(rows)

    log.info(f"Generated {len(rows)} envelope labels -> {out_path.name}")
    return out_path


# ---------------------------------------------------------------------------
# SUMMARY / COST REPORT
# ---------------------------------------------------------------------------

def print_summary(leads: list[dict], letters_path: Path, urls_path: Path, labels_path: Path):
    """Print cost and ROI analysis."""
    total = len(leads)
    with_name = sum(1 for l in leads if l.get("owner_name"))
    corp_check = ["LLC", "INC", "CORP", "TRUST", "LP"]
    corporate = sum(1 for l in leads if any(
        re.search(r'\b' + s + r'\b', l.get("owner_name", "").upper())
        for s in corp_check
    ))
    individual = with_name - corporate
    avg_arv = sum(l.get("arv", l.get("estimated_arv", 0)) for l in leads) / max(total, 1)

    stamp_cost = 0.73
    total_stamp = individual * stamp_cost
    paper_cost = individual * 0.05  # ~$0.05/sheet for paper
    envelope_cost = individual * 0.05
    total_cost = total_stamp + paper_cost + envelope_cost

    log.info("")
    log.info("=" * 60)
    log.info("REX DIRECT MAIL CAMPAIGN SUMMARY")
    log.info("=" * 60)
    log.info(f"Total leads:          {total}")
    log.info(f"Individual owners:    {individual} (mailable)")
    log.info(f"Corporate entities:   {corporate} (need different approach)")
    log.info(f"Average ARV:          ${avg_arv:,.0f}")
    log.info("")
    log.info("COST BREAKDOWN:")
    log.info(f"  Stamps ({individual} x ${stamp_cost}):    ${total_stamp:,.2f}")
    log.info(f"  Paper:                   ${paper_cost:,.2f}")
    log.info(f"  Envelopes:               ${envelope_cost:,.2f}")
    log.info(f"  TOTAL:                   ${total_cost:,.2f}")
    log.info("")
    log.info("EXPECTED ROI:")
    log.info(f"  Response rate 1%:   {max(1, int(individual * 0.01))} responses")
    log.info(f"  Response rate 3%:   {max(1, int(individual * 0.03))} responses")
    log.info(f"  One deal at $10k:   {10000/max(total_cost,1):.0f}x ROI")
    log.info("")
    log.info("FILES GENERATED:")
    log.info(f"  Letters:    {letters_path}")
    log.info(f"  Search URLs:{urls_path}")
    log.info(f"  Labels:     {labels_path}")
    log.info("")
    log.info("NEXT STEPS:")
    log.info("  1. Print letters from the .txt file (one per page)")
    log.info("  2. Print envelope labels from the .csv (Avery 5160)")
    log.info("  3. Open the search URL CSV, click links, fill in emails")
    log.info("  4. Import found emails back into leads_db.json")
    log.info("  5. Rex SDR picks up leads with emails on next cron run")
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# EMAIL IMPORT HELPER
# ---------------------------------------------------------------------------

def import_found_emails(search_csv_path: str) -> int:
    """
    After the user fills in the found_email column in the search URL CSV,
    this imports those emails back into leads_db.json.

    Usage: python3 rex_direct_mail.py --import /path/to/filled_csv.csv
    """
    csv_path = Path(search_csv_path)
    if not csv_path.exists():
        log.error(f"File not found: {csv_path}")
        return 0

    # Load current leads
    if not LEADS_DB.exists():
        log.error("No leads_db.json found")
        return 0

    leads = json.loads(LEADS_DB.read_text())
    leads_by_addr = {l.get("address", "").upper(): l for l in leads}

    updated = 0
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("found_email", "").strip()
            phone = row.get("found_phone", "").strip()
            if not email and not phone:
                continue

            addr = row.get("address", "").upper()
            if addr in leads_by_addr:
                if email and not leads_by_addr[addr].get("owner_email"):
                    leads_by_addr[addr]["owner_email"] = email
                    updated += 1
                if phone and not leads_by_addr[addr].get("owner_phone"):
                    leads_by_addr[addr]["owner_phone"] = phone

    if updated:
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
        log.info(f"Imported {updated} emails into leads_db.json")
    else:
        log.info("No new emails to import")

    return updated


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    # Handle import mode
    if "--import" in args:
        idx = args.index("--import")
        if idx + 1 < len(args):
            import_found_emails(args[idx + 1])
            return
        else:
            log.error("Usage: --import /path/to/filled_csv.csv")
            return

    letters_only = "--letters-only" in args
    search_only = "--search-only" in args

    leads = load_leads()
    if not leads:
        log.error("No leads found. Run ATTOM seeder first.")
        return

    letters_path = Path("/dev/null")
    urls_path = Path("/dev/null")
    labels_path = Path("/dev/null")

    if not search_only:
        letters_path = generate_all_letters(leads)

    if not letters_only:
        urls_path = generate_search_urls(leads)
        labels_path = generate_envelope_labels(leads)

    print_summary(leads, letters_path, urls_path, labels_path)


if __name__ == "__main__":
    main()
