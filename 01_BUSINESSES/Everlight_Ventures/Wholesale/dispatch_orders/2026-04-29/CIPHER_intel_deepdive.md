# Dispatch Order -- Cipher Wolfe (Perplexity Intel)

**From:** Marcus Cole, Chief Operator
**Issued:** 2026-04-29 evening, autonomous-pipeline handoff
**Priority:** HIGH (gates phase 7 email send for 6 leads)
**Boundary:** intel + WebSearch + LinkedIn + business-record probe ONLY. No outbound emails. No outbound calls. No payment for paid databases. No outbound-anything to a human.

---

## Mission

Six priority leads have a real first name on record but no MX-verified email. Phil hit the wall on free-tier skip-trace from phone-side -- TruePeopleSearch / FastPeopleSearch / WhitePages all returned 403. Your job is the WebSearch + public-business-record + LinkedIn pass that Phil could not run.

For each of the six, return ONE structured artifact at:

```
/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel/{slug}/skip_trace.json
```

Schema (REQUIRED for the orchestrator to advance the lead to phase 6):

```json
{
  "first_name": "Immanuel",
  "last_name": "Stokes",
  "email": "istokes@example.com",
  "email_mx_verified": true,
  "email_source": "linkedin_public_profile",
  "phone": null,
  "phone_dnc_scrubbed": false,
  "confidence": 0.85,
  "evidence_urls": ["https://linkedin.com/in/...", "https://radaris.com/..."],
  "skip_method": "websearch+linkedin+mx_dig",
  "performed_by": "Cipher Wolfe",
  "performed_at": "2026-04-29T22:00:00Z",
  "notes": "Found via Radaris snippet match (age + relatives + mailing addr exact)."
}
```

If you can't find an email after a thorough pass, write the artifact anyway with `email: null` and `notes` explaining what was tried. The orchestrator will route the lead to "mail-only" path, not the email path. **Honest negatives are useful artifacts.**

---

## The 6 leads

(Slugs match `seller_intel/` directory names.)

1. `024055__00017` -- **Immanuel Stokes** -- 1303 Michigan St -- mailing 2275 Lester Rd, Nesbit MS 38651
   - Confidence on identity already 0.95 (Phil verified via Radaris)
   - Try: LinkedIn "Immanuel Stokes" Nesbit MS / DeSoto County. Pattern-guess `istokes@`, `immanuel@`, `imm.stokes@` against any business email pattern surfaced.

2. `024055__00028` -- **Franklin Kemp** -- 1329 Michigan St -- mailing 5977 Randy Ln, Ellenwood GA 30294
   - Common name. Search LinkedIn + FB business pages around Ellenwood/Atlanta metro. If he's a contractor / driver / small-biz owner, his business email may be public.

3. `026013__00022` -- **Joseph Spilmann Jr** -- 1112 Saxon -- mailing 60 Young Rdg, Carriere MS 39426
   - Uncommon surname (Spilmann/Spillmann). Pearl River County MS. Try: TN/MS Sec of State LLC search for "Spilmann" -- the multi-quitclaim acquisition pattern looks like a portfolio investor. If LLC, the registered agent record will give us an email.

4. `034033__00003` -- **Samantha Green** -- 1539 S Orleans -- mailing Germantown Pkwy STE 101-301 (commercial mailbox, Cordova TN)
   - Common name + commercial mailbox = hard. Try LinkedIn for "Samantha Green Cordova TN" or "Samantha Green Memphis." If the mailbox is a registered-agent service, look at TN Sec of State for any LLC using that exact suite.

5. `048034__00013` -- **Christine Jones** + **Maggie Saunders** -- 1430 Silver -- mailing Oakland CA
   - Co-owner pattern. Two leads in one. WebSearch each separately for Oakland CA. Also check CA Sec of State for any "Jones Saunders" entity. Co-owner cases sometimes mean a deceased parent + two siblings inheriting.

6. `024047__00022` -- **Peter Showers Jr** -- 1382 Florida St -- mailing 465 Bonnell Ave, Memphis TN 38109
   - Local Memphis owner. Try Memphis-area LinkedIn / community business pages. 24-yr ownership = older couple; LinkedIn coverage is thin for that demographic. Try Daily Memphian + community newspaper search.

---

## Free-path-first rule (ALWAYS)

Before recommending any paid database (Whitepages Premium, BeenVerified, BatchSkipTracing, etc.), you MUST run all free paths first. Document each free path you tried (with URLs) in `notes` even if it returned nothing.

Free paths in order:
1. WebSearch (Perplexity) -- "{name} {city}" + LinkedIn site search
2. LinkedIn public profile (no login needed for the snippet)
3. State Sec of State business registry (free for all 50 states)
4. State LLC search if name suggests a company / portfolio
5. Daily Memphian + local-paper site search
6. Find-A-Grave (decedent only)
7. Email pattern guess + `dig MX {domain}` verification (no SMTP probing -- MX-record presence is the bar)

If you exhaust free paths and find nothing, that's a useful negative -- write it as such.

---

## Boundary

You DO NOT:
- Send any outbound email
- Place any phone call
- Friend / DM anyone on LinkedIn
- Buy a paid database subscription
- Speculate / hallucinate / fill in plausible-sounding details

You DO:
- Public WebSearch + Perplexity research
- LinkedIn public profile reads (snippet only)
- Sec of State / business registry searches
- Find-A-Grave / obit searches
- MX-record DNS lookups (`dig` only, never SMTP probe)
- Honest negative writes when nothing surfaces

---

## Done criteria

- 6 `skip_trace.json` files written under their respective slugs
- Each has either a verified email (MX confirmed) OR a documented honest negative
- Provenance: every `evidence_urls` entry is real and reachable
- Slack ping to `#war-room` (1-line ops) when finished: "Cipher: 6 skip-traces complete. {N} emails surfaced. {6-N} mail-only routed."
- Hive logger event: `skip_trace.batch_complete` with parcel list

---

## Why this matters

Phase 6 (compliance gate) blocks on email presence. Phase 7 (Piper's pre-call email) cannot fire without a real email. If you surface even 2 of the 6, that's 2 more leads moving through the funnel tomorrow. If you surface 0, the orchestrator routes them to mail-only and Lob is the channel -- still progress, just slower.

Either way, the next phase unblocks. That's the win.

-- Marcus
