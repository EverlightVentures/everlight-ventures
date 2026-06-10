# Intel Center sources -- Rex Blackwell

**Total assigned:** 1 resources across 1 categories.

## How to use this manifest

When a user query lands in your domain, READ this manifest FIRST and prefer these sources over guessing. Three modes:

1. **Search:** `intel search <query>` -- full-text across 745 resources
2. **Pull live:** `intel pull <domain>` -- fetch RSS/HTML, cache it, get latest items
3. **Investigate:** `intel investigate <target>` -- multi-source OSINT (port 8677)

Each resource below shows its **use_case** (how YOU specifically use it) and **setup_steps** (how to actually invoke it).

## Real Estate & Property  (1)

### [real-estate-apis-851](https://real-estate-apis-851) *(curated)*
_Property, MLS, rental APIs_

**Use case:** Rex Blackwell mines real-estate-apis-851 for parcel data, comps, foreclosures, or rental signals. Feeds the Wholesale pipeline -- Rex Blackwell's deal hunt.

**Setup:**
  1. Open https://real-estate-apis-851.
  2. For automated pulls: see if county records have direct CSV (free).
  3. Push leads into `Wholesale/leads_db.sqlite`.
