# Intel Center sources -- Brief Calloway

**Total assigned:** 1 resources across 1 categories.

## How to use this manifest

When a user query lands in your domain, READ this manifest FIRST and prefer these sources over guessing. Three modes:

1. **Search:** `intel search <query>` -- full-text across 745 resources
2. **Pull live:** `intel pull <domain>` -- fetch RSS/HTML, cache it, get latest items
3. **Investigate:** `intel investigate <target>` -- multi-source OSINT (port 8677)

Each resource below shows its **use_case** (how YOU specifically use it) and **setup_steps** (how to actually invoke it).

## Legal & Compliance  (1)

### [sec.gov](https://sec.gov)
_SEC Charges 21 Individuals with Alleged Wide-Reaching Insider Trading Scheme_

**Use case:** Brief Calloway pulled sec.gov live via `intel pull`. Latest items cached at cache/articles/. Refresh anytime: `intel pull sec.gov`.

**Setup:**
  1. Open https://sec.gov.
  2. Pull latest items: `intel pull sec.gov`.
  3. View detail at /09_Dashboard/resource.html?d=sec.gov
