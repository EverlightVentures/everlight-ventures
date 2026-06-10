# SKILL: Google Dorking Templates

Source: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/google_dorking_find_everything.txt`

Curated Google dork templates for Everlight's wholesale skip-trace, Broker OS buyer discovery, and AI Consulting prospecting. Use ONLY for public intelligence on existing prospects/leads. NEVER against third parties without a legitimate business reason.

## Prospect discovery

```
# Find SMBs with public phone + website in a city
site:yelp.com OR site:google.com "hvac contractor" "Sacramento" phone

# Find SMBs on Yellow Pages for targeted verticals
site:yellowpages.com "dental practice" "CA" "24 hours"

# Find LinkedIn profiles for SMB owners
site:linkedin.com/in/ "owner" "{vertical}" "{city}"
```

## Wholesale lead signals

```
# Properties with pre-foreclosure indicators
site:zillow.com "foreclosure" "{city}" "{state}"

# Tax delinquency lists (often public)
"{county} county" "delinquent tax" filetype:pdf 2024 OR 2025

# Probate filings
"{county} county" "probate" "docket" filetype:pdf

# Code enforcement violations
site:*.gov "code enforcement" "violation" "{address}" OR "{city}"
```

## Broker OS buyer intent signals

```
# Buyers publicly complaining about a SaaS
"alternative to {competitor}" site:reddit.com

# Companies hiring ops roles that imply pain
"hiring" "operations manager" "{industry}" site:linkedin.com/jobs

# Founders talking about specific tool gaps
site:twitter.com OR site:x.com "need a {tool_category}" -ad
```

## Security hygiene (self-audit)

```
# Check if any Everlight secrets leaked
site:github.com OR site:pastebin.com "everlightventures" password OR token OR key

# Find open S3 buckets associated with domain
site:s3.amazonaws.com "everlight"

# Subdomain discovery
site:*.everlightventures.io -www
```

## Negative dorks (avoid)

- DO NOT dork for personal addresses/SSN/finances of individuals.
- DO NOT use dorks to harvest emails for spam lists.
- DO NOT use dorks to bypass authentication.

Justine (Compliance) gates any large-scale dork campaign before it runs. If you are searching for more than ~20 records in a single session, stop and escalate.

## Usage

Paste any template above into Google, replace `{placeholders}` with real values, and work top-down. Results are sources, not answers. Confirm anything material through a second source before acting on it.
