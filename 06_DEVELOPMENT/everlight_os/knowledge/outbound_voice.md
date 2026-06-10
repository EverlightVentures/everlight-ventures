# Everlight Ventures -- Outbound Voice Doctrine

**Locked 2026-05-15.** Single source of truth for every outbound email across
every pipeline: wholesale (seller + buyer), AI Consulting, Onyx POS, Hive Mind
SaaS, Publishing (Everlight Literature), Alley Kingz, and all vendor /
counterparty / regulator / press communication.

> Sibling doc: `brand_voice.md` covers social-media brand voice per product
> (Last Light Protocol, BCARDI, Everlight Kids, etc.). This doc covers
> outbound EMAIL register selection by recipient. Different concern, no overlap.

When in doubt about an outbound, this doc wins. Persona spec files (e.g.,
`WHOLESALE_PERSONA_TEMPLATES.md`) add persona-specific texture ON TOP OF the
rules here, never in conflict with them.

---

## 0. North Star

**Voice scales to the READER, not the sender.** The same persona speaks
differently to a sophisticated investor than to a first-time seller. The
register picker (`content_tools/recipient_register.py`) decides which voice
register each recipient gets. The persona keeps its identity; the texture
changes.

> Reference: memory `feedback_voice_register_by_recipient` (HARD LAW).

---

## 1. The Five Registers

| Register | Recipient profile | Tone | Typical pipeline |
|---|---|---|---|
| **operator** | Multi-deed investor, fellow wholesaler, institutional capital, experienced founder | Peer respect, no flourishes, one signal of homework, tight prose | Wholesale cold-open to investor sellers; cash-buyer relationships at GP scale; B2B founders |
| **warm** | Distressed homeowner, first-time seller, inheritance case, residential consumer | Empathetic, patient, catchphrases and personality reveals (warmth escalates over the chain) | Wholesale cold-open to non-investor sellers; consumer-facing flows |
| **peer** | Fellow wholesaler, cash buyer (Chris @ Mid-South Homebuyers), small-shop investor | Investor-to-investor, net-to-you numbers, no over-explanation | Wholesale buyer-side outreach; partnership conversations |
| **consultative** | AI Consulting prospect, SaaS founder, SMB owner evaluating services | Discovery, question-led, no offer pressure in email #1 | AI Consulting top-of-funnel; Hive Mind SaaS demos; Onyx POS founder outreach |
| **professional_direct** | Vendor, title firm, attorney, accountant, regulator, opposing counsel | Procedural, formal, citation-friendly, no flourishes | Mid-South Title coordination; counsel correspondence; state agency replies |

---

## 2. Cold-Open Rules (apply to email #1, EVERY register)

These are non-negotiable for first-touch emails to people who have never heard
from us. After the recipient engages (touch 2+), register-specific warmth can
escalate.

1. **One verified signal in the first two lines.** Prove we did the homework
   on THEM. Examples: deed history, parcel ID, company funding round, podcast
   appearance, court filing year. Never "I noticed your property." Never
   "Looking at your portfolio, you appear to be."

2. **No catchphrases, no pets, no aphorisms in email #1.** "Hey y'all,"
   "Numbers don't lie," "Biscuit approves," and the like land naturally by
   touch 3, never in a cold-open to a stranger.

3. **No statutory language in the body.** RESPA, SB 909, FCRA, TCPA, OCGA --
   exact statute initialisms live in attached PSA / Schedule A / disclosure
   docs, never in email body. Plain-English substitute in body.

4. **No em-dashes, no non-whitelist hyphens.** Use commas, semicolons,
   parentheses. Whitelist hyphens: proper nouns like Mid-South Title only.

5. **One ask, one line.** "Worth ten minutes this week?" is fine.
   "If there's any interest, reply with what time works for a quick call or
   if you'd prefer email only that's fine too" is not. Limp CTAs are AI-tells.

---

## 3. Universal Phrase Blacklist

Never use these in any outbound, any register, any stage:

- `I hope this email finds you well`
- `I'm reaching out because`
- `Just following up`
- `I noticed your [property|company|profile] and wanted to reach out`
- `Looking at your [portfolio|background], you appear to be`
- `If there's any interest, reply with what time works`
- `My name is [X], with [company]` (preferred: `[Name] with Everlight Ventures.`)
- `RESPA`, `SB 909`, `FCRA`, `TCPA`, `OCGA` (statute initialisms in body)
- Em-dashes of any kind
- `as-is`, `e-signature`, `investor-to-investor`, `RESPA-clean` (hyphen variants)

If the recipient has SAID `STOP`, the lead is permanent-eradicated per
`feedback_streubel_permanent_eradication` and the hardcoded list in
`eradication_gate.py`. No exceptions.

---

## 4. Register x Stage Matrix (when each persona is FREE to add warmth)

| Stage | operator | warm | peer | consultative | professional_direct |
|---|---|---|---|---|---|
| #1 cold-open | tight, signal-led | tight, empathy-led | tight, peer respect | discovery question | procedural |
| #2 first reply | begin contextual warmth | begin catchphrase warmth | begin shop-talk | proposed deeper question | procedural, slightly humanized |
| #3 offer / proposal | numbers anchor, named handoff | catchphrases land here | net-to-you tables | scoped proposal | procedural with rationale |
| #4 contract / commitment | clean, signed | gratitude welcome | clean | scoped commitment | procedural with citations |
| #5 close / signoff | brief gravity | celebratory | brief peer | warm wrap | procedural close |

---

## 5. Pipeline Defaults

Each pipeline has a default register; the classifier overrides on a per-lead
basis when signals warrant.

| Pipeline | Default register | Override signals |
|---|---|---|
| Wholesale seller (default) | `warm` | `deed_count>=4` or `has_court_filings` or `is_llc_owner` -> `operator` |
| Wholesale seller, investor track | `operator` | `is_first_time_seller` or `is_inheritance` -> `warm` |
| Wholesale buyer | `peer` | always peer for buy-side cash relationships |
| AI Consulting prospect | `consultative` | senior founder / GP -> `operator` |
| Onyx POS | `consultative` | franchise owner / chain operator -> `operator` |
| Hive Mind SaaS | `consultative` | dev-team lead at scale -> `peer` |
| Vendor / counterparty | `professional_direct` | always |
| Regulator / state agency | `professional_direct` | always |
| Press / journalist | `professional_direct` | rotation-aware, never overshare |
| Publishing reader | `warm` | depends on genre |

---

## 6. Personas (by pipeline)

### Wholesale -- 4 senders (locked 2026-05-15)

> Source of truth: `01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/WHOLESALE_PERSONA_TEMPLATES.md`

- **Piper Reeves** -- Outreach (cold-open + first warm-up). Registers: warm | operator.
- **Henry Hammond** -- Negotiation (anchor + counter). Registers: confident-warm | peer-operator.
- **Marvin Cohen** -- Closing (contract + e-sign coordination). Registers: procedural-warm | procedural-direct.
- **Vaughn Sterling** -- Senior Partner (signoff + escalation). Registers: gravity-warm | gravity-direct.

### AI Consulting -- TBD

Pipeline-specific personas to be defined when AI Consulting outbound goes live.
Pattern: 4 named senders, role-bound, each with register variants.

### Onyx POS -- TBD
### Hive Mind SaaS -- TBD

---

## 7. Audit + Drift Detection

Every send through `branded_mailer.send_branded_email()` writes to
`_logs/branded_mailer_audit.jsonl`:

```json
{
  "ts": "2026-05-15T...",
  "to": "...",
  "register": "operator",
  "persona": "piper_reeves",
  "stage": "cold_open",
  "template_id": "operator_cold_open_v1",
  "phrase_blacklist_pass": true,
  "hyphen_check_pass": true,
  "statutory_leak_pass": true,
  "message_id": "..."
}
```

Style Enforcer agent runs nightly drift detection against this log. Any
register mismatch with the recipient's profile gets flagged in the next
morning's CEO Brief.

---

## 8. Update protocol

Changes to this doc require:
1. PR to side branch first (per `feedback_push_side_then_prod_doctrine`)
2. Style Enforcer review
3. Content Director (Vera Lux) signoff
4. Rich's countersign for register definition changes (additions or removals)

Memory keepers: [[feedback-voice-register-by-recipient]],
[[feedback-canonical-team-roster]], [[feedback-no-hyphens-in-outbound]],
[[feedback-statutory-disclosure-in-attachment]],
[[feedback-carmax-of-wholesaling-thesis]].
