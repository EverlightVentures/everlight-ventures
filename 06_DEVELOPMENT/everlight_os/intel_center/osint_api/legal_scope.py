"""
legal_scope -- what Everlight Intel Center WILL and WILL NOT extract.

Public mantra: if Google can serve targeted ads from public signals, an
operator can build a targeted pitch from public signals. The line is at
*public* -- whatever is voluntarily published. Everything below this list
is off-limits regardless of technical access.

This module is the single source of truth that compliance + agent firmware
+ report footer all read from.
"""

# ============== IN-SCOPE (PUBLIC) ==============
IN_SCOPE = {
    "social_public": {
        "label": "Public social posts + bios",
        "sources": ["GitHub bio", "Twitter/X bio", "Instagram bio", "Reddit profile",
                    "LinkedIn public page", "Medium about", "Pinterest boards",
                    "Patreon page", "Behance/Dribbble", "About.me", "Keybase"],
        "what": "Bio text, public posts, hashtags, public follower lists, profile pics",
        "limit": "Public-facing only; never log in to scrape members-only content",
    },
    "consumer_public": {
        "label": "Public consumer behavior",
        "sources": ["Yelp public reviews", "Goodreads shelves", "Letterboxd ratings",
                    "IMDb ratings", "Untappd check-ins", "Strava public activities",
                    "Spotify public playlists", "GoodFood public reviews",
                    "TripAdvisor reviews", "Product Hunt upvotes"],
        "what": "Restaurants visited, books read, films rated, beers tried, running routes",
        "limit": "Only items the user marked public; never private wishlists or DMs",
    },
    "civic_records": {
        "label": "Civic + government records",
        "sources": ["FEC.gov campaign contributions", "OpenSecrets.org",
                    "FollowTheMoney.org (state campaign $)",
                    "USPTO patent filings", "USPTO trademarks",
                    "Voter registration (state-by-state public)",
                    "Public meeting comments (city council minutes)"],
        "what": "Campaign donations, patents/trademarks, voter party (state-dependent), civic engagement",
        "limit": "Only where state law makes the record public; CO/MN restrict voter file",
    },
    "court_records": {
        "label": "Court + legal records",
        "sources": ["CourtListener", "PACER (federal)", "state court systems",
                    "SEC EDGAR", "OpenCorporates", "state SoS business filings",
                    "Justia", "casetext public records"],
        "what": "Court dockets, opinions, judgments, business filings, officer roles",
        "limit": "Public-record only -- never sealed dockets even if technically accessible",
    },
    "philanthropy_public": {
        "label": "Public philanthropy",
        "sources": ["ProPublica Nonprofit Explorer (990s)",
                    "GuideStar/Candid", "GoFundMe (public campaigns)",
                    "ActBlue / WinRed donor listings (where public)",
                    "Cause-specific walk/run public participant lists"],
        "what": "Charity board memberships, public 990-disclosed gifts, public-campaign backings",
        "limit": "Only donors whose names are voluntarily public on the source",
    },
    "media_mentions": {
        "label": "News + obituary archives",
        "sources": ["Google News", "Bing News", "newspaper archives",
                    "Find-A-Grave", "Legacy.com obituaries"],
        "what": "News mentions, life-event announcements (wedding/obit/award), local press",
        "limit": "Indexed public content only",
    },
    "property_public": {
        "label": "Property + assessor records",
        "sources": ["County assessor sites", "Zillow public listings", "Redfin",
                    "Realtor.com", "Trulia", "Homes.com"],
        "what": "Tax records, deed transfers, parcel info, listing history",
        "limit": "Where the county or platform serves it without authentication",
    },
    "professional_credentials": {
        "label": "Professional licenses + credentials",
        "sources": ["State licensing boards (medical/legal/real estate)",
                    "Bar association directories", "FINRA BrokerCheck",
                    "AMA physician finder", "NMLS for mortgage originators",
                    "ProPublica's public-sector data sets"],
        "what": "License number, status, action history, education, professional milestones",
        "limit": "All public by statute -- but check Operator Truth: never imply a license the operator hasn't seen",
    },
}

# ============== OUT OF SCOPE (HARD STOP) ==============
OUT_OF_SCOPE = {
    "hipaa_health": {
        "label": "Medical records / HIPAA-protected health info",
        "why": "HIPAA Privacy Rule 45 CFR §§164.500-534. Never touch.",
        "examples": "Prescription histories, doctor visits, diagnoses, lab results, hospital records",
        "exception": "PUBLIC self-disclosure (e.g., person posts 'I'm diabetic' on Reddit) is in-scope, but treat sensitive",
    },
    "dppa_dmv": {
        "label": "DMV / Driver Privacy Protection Act data",
        "why": "DPPA 18 USC §2721. Civil + criminal penalties for unauthorized access.",
        "examples": "Driver license #, license plate lookups, vehicle registration, photo",
        "exception": "None applicable to wholesale outreach",
    },
    "fcra_consumer_reports": {
        "label": "Consumer credit reports",
        "why": "FCRA 15 USC §1681. Wholesale outreach is not a 'permissible purpose'.",
        "examples": "Credit score, credit history, FICO, Experian/Equifax/TransUnion reports",
        "exception": "Never. Even if the lead opts in, requires specific FCRA-compliant disclosure",
    },
    "glba_financial": {
        "label": "Nonpublic financial info (GLBA)",
        "why": "GLBA 15 USC §§6801-6809 + §§6821-6827. Pretexting is a federal crime.",
        "examples": "Bank account balances, transaction history, mortgage payoff statements",
        "exception": "Only if obtained directly from the consumer with their consent",
    },
    "ecpa_communications": {
        "label": "Intercepted communications",
        "why": "Electronic Communications Privacy Act 18 USC §§2510-2522.",
        "examples": "Private email contents, SMS contents, voicemails not voluntarily shared",
        "exception": "None",
    },
    "private_membership_data": {
        "label": "Private membership data",
        "why": "First Amendment associational privacy + various state laws",
        "examples": "Private support groups, AA/NA membership lists, private therapist patient lists",
        "exception": "PUBLIC self-disclosure is in-scope; never pierce a private group's roster",
    },
    "minors": {
        "label": "Records about minors",
        "why": "Children's Online Privacy Protection Act + state laws",
        "examples": "Anything about children under 13, school records of minors",
        "exception": "Public family-event mentions (e.g., 'congrats on new baby') are fine; never target minors",
    },
    "license_plate_lookup": {
        "label": "License plate to VIN / owner lookup",
        "why": "DPPA 18 USC 2721 -- statutory damages $2,500 minimum per violation; "
               "wholesale outreach is not among the 14 permissible purposes",
        "examples": "Plate number to vehicle owner, plate-camera databases, VIN-to-owner",
        "exception": "None applicable. Codified 2026-05-15 after 3-agent OSINT audit.",
    },
    "voter_id_brute": {
        "label": "Voter ID brute-force lookup",
        "why": "State election-law violations in most states; not relevant to property pitch",
        "examples": "Iterating voter IDs to discover unpublished records",
        "exception": "Public voter file (where state law makes party affiliation public) "
                     "queried by name+address is in-scope; brute-force ID iteration is not",
    },
    "breach_csv_enrichment": {
        "label": "Breach data / ComboList enrichment (beyond HIBP existence)",
        "why": "CFAA + ECPA exposure for downloading + processing breach CSVs",
        "examples": "Downloading Collection-1, parsing leaked-credentials dumps, ripgrep on Pastebin scrapes",
        "exception": "HIBP existence-check (knowing an email appeared in *some* breach) is in-scope. "
                     "The line is HIBP_GETTING_THE_PASSWORD vs HIBP_KNOWING_AN_EMAIL_EXISTS.",
    },
    "wifi_geolocation": {
        "label": "WiFi BSSID geolocation (Wigle and equivalents)",
        "why": "Surveillance signal with zero pitch value; pure creep-line violation",
        "examples": "Looking up a person's home WiFi BSSID to confirm address",
        "exception": "None. Already have property address via assessor.",
    },
    "form_brute_force": {
        "label": "Burp Suite / form brute-force attacks against any target",
        "why": "CFAA violation -- we are not pentesters and have no written authorization",
        "examples": "Brute-forcing login forms, credential stuffing, automated form submission attacks",
        "exception": "Defensive audit of Everlight's own properties only, never third parties",
    },
    "login_walled_scraping": {
        "label": "Scraping behind any login wall",
        "why": "Platform ToS + ECPA exposure (e.g. Hunchly behind LinkedIn auth)",
        "examples": "Auto-login to LinkedIn/Facebook/Instagram to scrape profile data, "
                    "session-cookie reuse to access members-only content",
        "exception": "Public-by-default profiles accessed without login are in-scope "
                     "(hiQ v. LinkedIn, 9th Cir.); the line is the auth boundary",
    },
    "hexstrike_external": {
        "label": "HexStrike (or equivalent AI pen-test MCP) against any third party",
        "why": "Without written authorization, every shot crosses CFAA",
        "examples": "Running HexStrike against a buyer's company before vetting, against a competitor",
        "exception": "Sandbox VM, against Cipher-owned test targets only. WO2 in TODO_AGENTS.md.",
    },
    "fcra_seller_side": {
        "label": "Consumer-credit-style criminal-background reports on property owners",
        "why": "FCRA 15 USC 1681 -- seller prospecting is not a permissible purpose",
        "examples": "Pulling a TruthFinder / BeenVerified / Spokeo-Pro background report on an owner before pitching",
        "exception": "Direct public-court-record search (CourtListener, county clerk) is in-scope; "
                     "the line is FCRA-covered consumer-report vs raw public records. "
                     "Buyer-side at Stripe Identity tier is a separate flow under 1681b(a)(3)(F)(ii).",
    },
}


def in_scope_list() -> list[dict]:
    return [{"key": k, **v} for k, v in IN_SCOPE.items()]


def out_of_scope_list() -> list[dict]:
    return [{"key": k, **v} for k, v in OUT_OF_SCOPE.items()]


def is_in_scope(source_class: str) -> bool:
    return source_class in IN_SCOPE


def render_short_scope() -> str:
    """One-paragraph human summary for report footer."""
    return (
        "Sources used: public social/bios, public consumer reviews + activity (Yelp/Goodreads/"
        "Strava/etc.), civic + court records, public philanthropy (FEC/990s), news + obit "
        "archives, property assessor records, professional license lookups. EXCLUDED: HIPAA "
        "medical records, DMV (DPPA), consumer credit (FCRA), nonpublic financial (GLBA), "
        "private communications (ECPA), private support-group membership, minors."
    )
