# $BCARDD "Day One" Email Intro - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce $BCARDD to an owned email audience using a Brody-style permission email (dog-voiced, fun-only, faceless), built and sent on *our* infrastructure (Resend + custom branded template), with GoHighLevel documented as a future option but NOT executed.

**Architecture:** Two tracks. **Track A (EXECUTE NOW)** builds the email on our side: a pure-Python email builder rendered through the existing `send_branded_email()` path (keeps `resend_guard` + `resend_budget` + phrase-scrub + send-authority gate), plus a lightweight owned-list capture (signup page to Supabase table to double opt-in) so we have someone to send to. **Track B (PLAN ONLY)** is a GoHighLevel operator playbook/answer-sheet for when Rich decides to pay for it. No code, no account action taken now.

**Tech Stack:** Python 3 (email builder + sender), `content_tools.branded_mailer` / `report_template` (Resend send path), static HTML (signup page), Supabase Postgres + Edge Functions (TypeScript/Deno) for capture + double opt-in.

## Global Constraints

*Every task's requirements implicitly include this section. Values are copied verbatim and enforced by tests where noted.*

- **Fun-only, never investment.** Every email must contain the disclaimer: `$BCARDD is a meme coin and a game, for fun and community, not an investment. DYOR. Never bet the rent.` No price talk, no ROI, no "to the moon $", no financial promises. (Enforced by test.)
- **Faceless founder.** The *dog/mascot* speaks in first person. The email must NEVER claim Rich made/created/owns the coin. Banned substrings (case-insensitive): `i made`, `i created`, `i built this coin`, `my coin`, `i'm the founder`, `i am the founder`, `i launched`. (Enforced by test. See [[feedback_bcardd_anonymous_founder]].)
- **Positive vibes only.** No war/tragedy/deaths/politics. Lanes = dog/cards/game/memes/community. (See [[feedback_bcardd_positive_vibes_only]].)
- **CAN-SPAM.** Every email must include a working unsubscribe link and a real physical postal address: the LLC **registered-agent address**, NEVER a PO box. (Enforced by test that the address token is present + non-empty. See [[feedback_wholesale_digital_only_no_postal_box]].)
- **Send path is mandatory.** All sends go through `content_tools.branded_mailer.send_branded_email()`. NO direct `api.resend.com` calls. `budget_category="nurture"` (opt-in list, not cold bulk).
- **No new root dirs.** All new files land under `01_BUSINESSES/BCARDI_Crypto/`, `_state/bcardd_ops/`, or `supabase/`. Never workspace root.

---

## File Structure

**Track A, built now:**
- `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/bcardd_email.py` - email builder (`build_intro_html`) + sender (`send_intro`) + `--preview`/`--test` CLI. One responsibility: produce + send the $BCARDD intro email.
- `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/tests/test_bcardd_email.py` - compliance + render tests.
- `_state/bcardd_ops/join.html` - public "Join the pack" signup page (gold/dog skin, matches `share.html`).
- `supabase/migrations/20260617_bcardd_subscribers.sql` - `bcardd_subscribers` table + RLS.
- `supabase/functions/bcardd-subscribe/index.ts` - capture + send confirm email (double opt-in).
- `supabase/functions/bcardd-confirm/index.ts` - confirm token, mark subscribed, fire the intro email.

**Track B, documented only (no files executed):**
- `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/GHL_PLAYBOOK.md` - the GoHighLevel answer-sheet (written as a doc; nothing is configured in GHL).

---

## TRACK A - Execute Now (our side, custom templates)

### Task 1: $BCARDD intro email builder (pure function)

**Files:**
- Create: `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/bcardd_email.py`
- Test: `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/tests/test_bcardd_email.py`

**Interfaces:**
- Produces: `build_intro_html(*, gift_url: str, unsub_url: str, postal_address: str, heart_url: str = HEART_URL) -> str` returns the INNER body HTML (to be wrapped by `render_report()` later). Raises `ValueError` if `gift_url`, `unsub_url`, or `postal_address` is empty.
- Module constants: `FUN_ONLY_DISCLAIMER: str`, `BANNED_FOUNDER_PHRASES: tuple[str, ...]`, `HEART_URL: str` (the Jupiter verified link from `share.html`).

- [ ] **Step 1: Write the failing tests** (compliance-as-tests, this is the spec)

```python
# tests/test_bcardd_email.py
import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bcardd_email import build_intro_html, FUN_ONLY_DISCLAIMER, BANNED_FOUNDER_PHRASES

KW = dict(
    gift_url="https://alleykingz.online/bcardd/gift?code=PACK",
    unsub_url="https://example.com/u/abc",
    postal_address="Everlight Ventures LLC, 123 Registered Agent St, City, ST 00000",
)

def test_includes_fun_only_disclaimer():
    assert FUN_ONLY_DISCLAIMER in build_intro_html(**KW)

def test_includes_unsubscribe_link():
    html = build_intro_html(**KW)
    assert KW["unsub_url"] in html and "unsub" in html.lower()

def test_includes_postal_address():
    assert KW["postal_address"] in build_intro_html(**KW)

def test_includes_gift_link():
    assert KW["gift_url"] in build_intro_html(**KW)

def test_dog_voice_present():
    html = build_intro_html(**KW).lower()
    assert "$bcardd" in html and "dealer" in html

def test_no_founder_claims():
    html = build_intro_html(**KW).lower()
    for phrase in BANNED_FOUNDER_PHRASES:
        assert phrase not in html, f"founder-claim leaked: {phrase!r}"

def test_no_investment_language():
    html = build_intro_html(**KW).lower()
    for bad in ("financial advice is", "guaranteed return", "roi", "to the moon $", "buy now to profit"):
        assert bad not in html

@pytest.mark.parametrize("missing", ["gift_url", "unsub_url", "postal_address"])
def test_required_fields_raise(missing):
    kw = dict(KW); kw[missing] = ""
    with pytest.raises(ValueError):
        build_intro_html(**kw)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter && python3 -m pytest tests/test_bcardd_email.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'bcardd_email'`

- [ ] **Step 3: Write minimal implementation**

```python
# bcardd_email.py
"""$BCARDD "Day One" intro email: dog-voiced, fun-only, faceless.

Produces the INNER body HTML only. The outer luxury wrapper + Resend send +
all guards come from content_tools.branded_mailer.send_branded_email().
"""
from __future__ import annotations

# Jupiter "verified" heart-ask link reused from _state/bcardd_ops/share.html
HEART_URL = "https://verified.jup.ag/dashboard/6mjokwXx7NNzo5ocvLDFGmbsGAs7rYHZdVJhKYkapump"

FUN_ONLY_DISCLAIMER = (
    "$BCARDD is a meme coin and a game, for fun and community, not an "
    "investment. DYOR. Never bet the rent."
)

# Faceless guard: the dog speaks, Rich never claims authorship.
BANNED_FOUNDER_PHRASES = (
    "i made", "i created", "i built this coin", "my coin",
    "i'm the founder", "i am the founder", "i launched",
)


def build_intro_html(*, gift_url: str, unsub_url: str, postal_address: str,
                     heart_url: str = HEART_URL) -> str:
    for name, val in (("gift_url", gift_url), ("unsub_url", unsub_url),
                      ("postal_address", postal_address)):
        if not val or not val.strip():
            raise ValueError(f"{name} is required")

    return f"""
<p style="font-size:18px;">You found me. 🐕🃏</p>

<p>Name's <strong>$BCARDD</strong>, the B-Card Dog. The dealer. If this hit your
inbox, it's 'cause you grabbed the share kit, played a hand, or somebody in the
pack put you on.</p>

<p><em>Recognize the crew? &#8595;</em></p>
<p style="text-align:center;">
  <img src="https://alleykingz.online/bcardd/assets/montage.gif"
       alt="$BCARDD card drops + game clips" style="max-width:100%;border-radius:12px;">
</p>

<p>Here's the deal: I'm dealing you into the pack. Not a pitch, not financial
advice, just the most fun corner of the internet with a dog, a deck, and people
who actually show up.</p>

<p><strong>First one's on the house 🎁</strong> a little something on me:
<a href="{gift_url}">claim it here</a>.</p>

<p>Wanna help the pack grow? Tap a ❤️ on the page (counts real humans, blocks
bots): <a href="{heart_url}">right here</a>.</p>

<h3>What you get</h3>
<p>Card drops, game updates, memes that actually hit, and first dibs when
something new lands.</p>

<p>I only deal to people who wanna play. Not your vibe? No hard feelings,
<a href="{unsub_url}">fold here (unsubscribe)</a>.</p>

<h3>One thing before you go</h3>
<p>Hit reply and tell me your favorite hand, or the meme that put you on. I read
every one, and it tells me what to drop next.</p>

<p>Stay sharp,<br><strong>- $BCARDD 🃏</strong></p>

<hr>
<p style="font-size:12px;color:#8a8578;">{FUN_ONLY_DISCLAIMER}<br>
Everlight Ventures &middot; {postal_address} &middot;
<a href="{unsub_url}">unsubscribe</a></p>
""".strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter && python3 -m pytest tests/test_bcardd_email.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/bcardd_email.py 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/tests/test_bcardd_email.py
git commit -m "feat(bcardd): dog-voiced intro email builder + compliance tests"
```

---

### Task 2: Sender + preview CLI (wires builder to branded_mailer)

**Files:**
- Modify: `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/bcardd_email.py`
- Test: `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/tests/test_bcardd_email.py`

**Interfaces:**
- Consumes: `build_intro_html(...)` from Task 1; `send_branded_email(...)` from `content_tools.branded_mailer`.
- Produces: `send_intro(recipients: list[str], *, gift_url, unsub_url, postal_address, dry_run: bool=False) -> dict` builds HTML, calls `send_branded_email(subject="You found me 🃏", content_html=..., from_name="$BCARDD 🃏", from_email=BCARDD_FROM_EMAIL, budget_category="nurture", reply_to=BCARDD_REPLY_TO)`. When `dry_run`, returns `{"dry_run": True, "html_bytes": int}` and does NOT send.
- Constants: `BCARDD_FROM_EMAIL` / `BCARDD_REPLY_TO` read from env (`BCARDD_FROM_EMAIL`, default `dealer@everlightventures.io`, must be a verified Resend sender; flagged for a dedicated bcardd domain in Track B).

- [ ] **Step 1: Write the failing test** (dry-run path, no network)

```python
def test_send_intro_dry_run():
    from bcardd_email import send_intro
    out = send_intro(["someone@example.com"], gift_url="https://x/y",
                     unsub_url="https://x/u", postal_address="LLC, addr",
                     dry_run=True)
    assert out["dry_run"] is True and out["html_bytes"] > 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_bcardd_email.py::test_send_intro_dry_run -v`
Expected: FAIL, `ImportError: cannot import name 'send_intro'`

- [ ] **Step 3: Write minimal implementation** (append to `bcardd_email.py`)

```python
import os, sys, pathlib

BCARDD_FROM_EMAIL = os.environ.get("BCARDD_FROM_EMAIL", "dealer@everlightventures.io")
BCARDD_REPLY_TO = os.environ.get("BCARDD_REPLY_TO", BCARDD_FROM_EMAIL)
_SUBJECT = "You found me 🃏"

def _load_mailer():
    # content_tools lives under 03_AUTOMATION_CORE/01_Scripts
    root = pathlib.Path(__file__).resolve()
    for p in root.parents:
        ct = p / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
        if ct.exists():
            sys.path.insert(0, str(ct.parent)); sys.path.insert(0, str(ct))
            break
    from content_tools.branded_mailer import send_branded_email  # type: ignore
    return send_branded_email

def send_intro(recipients, *, gift_url, unsub_url, postal_address, dry_run=False):
    html = build_intro_html(gift_url=gift_url, unsub_url=unsub_url,
                            postal_address=postal_address)
    if dry_run:
        return {"dry_run": True, "html_bytes": len(html)}
    send = _load_mailer()
    return send(
        recipients=recipients, subject=_SUBJECT, content_html=html,
        from_name="$BCARDD 🃏", from_email=BCARDD_FROM_EMAIL,
        reply_to=BCARDD_REPLY_TO, budget_category="nurture",
    )

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="write preview HTML to ./preview.html")
    ap.add_argument("--test", metavar="EMAIL", help="send one live test to this address")
    a = ap.parse_args()
    demo = dict(gift_url="https://alleykingz.online/bcardd/gift?code=PACK",
                unsub_url="https://alleykingz.online/bcardd/u/PREVIEW",
                postal_address=os.environ.get("BCARDD_POSTAL_ADDRESS", "Everlight Ventures LLC, [registered-agent addr]"))
    if a.preview:
        pathlib.Path("preview.html").write_text(build_intro_html(**demo)); print("wrote preview.html")
    elif a.test:
        print(send_intro([a.test], **demo))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_bcardd_email.py -v`
Expected: PASS (9 tests). Then eyeball it: `python3 bcardd_email.py --preview && echo open preview.html`

- [ ] **Step 5: Commit**

```bash
git add 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/bcardd_email.py 01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/tests/test_bcardd_email.py
git commit -m "feat(bcardd): send_intro via branded_mailer + preview/test CLI"
```

> **STOP-AND-SHOW checkpoint:** After Task 2, send a live `--test` to `1m.rich.gee@gmail.com` and let Rich eyeball it in his own inbox before building capture. This is the "see it like Brody's" moment.

---

### Task 3: "Join the pack" signup page

**Files:**
- Create: `_state/bcardd_ops/join.html`

Build a single-screen, gold/dog-skinned page matching `share.html` styling (reuse the `:root` palette + card styles). Content: hero (dog), one email field + "Deal me in 🃏" button, the fun-only disclaimer in the footer. The form POSTs `{email}` to the `bcardd-subscribe` edge function (Task 5). On submit, swap to a "Check your inbox to confirm 📩" state (double opt-in).

- [ ] **Step 1:** Copy the `<style>` `:root` + base rules from `_state/bcardd_ops/share.html` so the skin matches.
- [ ] **Step 2:** Add the form + a `fetch(SUBSCRIBE_URL, {method:'POST', body: JSON.stringify({email})})` handler with success/error states. Include the `FUN_ONLY_DISCLAIMER` text in the footer verbatim.
- [ ] **Step 3:** Manual test, open in a browser, submit a fake email, confirm the success state renders (point `SUBSCRIBE_URL` at a placeholder until Task 5 deploys).
- [ ] **Step 4: Commit**

```bash
git add _state/bcardd_ops/join.html
git commit -m "feat(bcardd): Join the pack email signup page (double opt-in UX)"
```

---

### Task 4: `bcardd_subscribers` table + RLS migration

**Files:**
- Create: `supabase/migrations/20260617_bcardd_subscribers.sql`

**Interfaces:**
- Produces table `public.bcardd_subscribers(id uuid pk default gen_random_uuid(), email text unique not null, status text not null default 'pending' check (status in ('pending','subscribed','unsubscribed')), confirm_token uuid default gen_random_uuid(), source text default 'join_page', created_at timestamptz default now(), confirmed_at timestamptz, unsubscribed_at timestamptz)`.
- RLS: **forced on**, anon has NO direct table access; all writes happen via edge functions using the service-role key (mirrors the AK social-layer pattern in [[project_ak_social_layer]]).

- [ ] **Step 1:** Write the SQL (table + `alter table ... enable row level security;` + `... force row level security;` + a unique index on `lower(email)`).
- [ ] **Step 2:** Apply to the BCARDD/AK Supabase project (default `jdqqmsmwmbsnlnstyavl`, confirm with Rich which project owns BCARDD before applying) via the Supabase MCP `apply_migration`.
- [ ] **Step 3:** Verify with `list_tables` that `bcardd_subscribers` exists with RLS forced.
- [ ] **Step 4: Commit** the migration file.

---

### Task 5: `bcardd-subscribe` edge function (capture + confirm email)

**Files:**
- Create: `supabase/functions/bcardd-subscribe/index.ts`

Mirror `06_DEVELOPMENT/vantaris/supabase/functions/notify-lead/index.ts`. Flow: validate email, upsert row `status='pending'`, build a confirm URL (`.../bcardd-confirm?token=<confirm_token>`), send a short "confirm you're in" email via Resend (reuse the branded send or a minimal confirm template). CORS headers for the `join.html` origin. Never echo the service-role key.

- [ ] **Step 1:** Scaffold from `notify-lead`, swap table + payload.
- [ ] **Step 2:** Deploy via Supabase MCP `deploy_edge_function`.
- [ ] **Step 3:** Manual test, `curl` the function with a test email, confirm a `pending` row appears + a confirm email arrives.
- [ ] **Step 4: Commit.**

---

### Task 6: `bcardd-confirm` edge function (double opt-in, fire intro)

**Files:**
- Create: `supabase/functions/bcardd-confirm/index.ts`

Flow: read `token`, find `pending` row, set `status='subscribed', confirmed_at=now()`, trigger the Task 2 intro email to that address (simplest: the confirm function sends the intro via Resend using the same inner HTML rendered server-side). Show a friendly "You're in the pack 🐕" confirmation page.

- [ ] **Step 1:** Implement confirm + idempotency (already-subscribed, friendly no-op).
- [ ] **Step 2:** Deploy + manual test the full loop: `join.html`, confirm email, click, "You're in", intro email lands.
- [ ] **Step 3: Commit.**

> **List ownership (the "1 AND 3" answer):** `bcardd_subscribers` in our Supabase **is** the source of truth we own. If/when GHL comes online (Track B), GHL becomes the front-door capture and we sync its contacts *into* this table via webhook. We never let the list live only in GHL.

---

## TRACK B - GoHighLevel (PLAN ONLY, do not execute)

Write `01_BUSINESSES/BCARDI_Crypto/02_Community/newsletter/GHL_PLAYBOOK.md` as a complete operator answer-sheet so Rich can stand it up in one sitting *when he decides the $97/mo is worth it*. **No account is created, no GHL action is taken as part of this plan.** The playbook documents, field-by-field (per [[feedback_full_answer_sheets_before_forms]]):

1. **Account + plan** - which GHL tier, the ~$97/mo line item, who owns the login.
2. **Sending domain** - verify a dedicated `bcardd.*` domain (keeps the brand faceless + separate from everlightventures.io, per [[project_brand_entity_separation_roadmap]]); DNS records to add.
3. **Signup funnel page** - headline, sub, single email field, button copy, the dog hero, the fun-only disclaimer block (verbatim).
4. **The intro email** - paste the exact Task 1 copy into GHL's drag-drop editor; where the GIF/images upload; subject `You found me 🃏`.
5. **Double opt-in automation** - confirm step, welcome trigger fires the intro.
6. **List sync back to us** - GHL outbound webhook to a small `bcardd-ghl-sync` edge function, upsert into `bcardd_subscribers`. (We always own the list.)
7. **Compliance footer** - same fun-only disclaimer + registered-agent address + unsubscribe.

This file is prose/checklist only. It is the deliverable for Track B.

---

## Self-Review

- **Spec coverage:** list (Tasks 3-6) done; custom-template email (Tasks 1-2) done; dog voice (Task 1) done; fun-only + faceless + CAN-SPAM (Global Constraints, enforced by Task 1 tests) done; "1 and 3" Resend+GHL split (Task 6 note + Track B item 6) done; GHL plan-only (Track B) done.
- **Placeholders:** `montage.gif`, `gift_url`, `BCARDD_FROM_EMAIL`, `BCARDD_POSTAL_ADDRESS`, and the Supabase project id are **config inputs Rich must supply**, not logic gaps. Each is flagged at its use site. The registered-agent address is intentionally operator-provided (no PO box).
- **Type consistency:** `build_intro_html(**KW)` signature matches across Tasks 1-2; `send_intro` params match its test.

## Open inputs needed from Rich (to fill config, not blockers to start coding)
1. **Registered-agent postal address** for the CAN-SPAM footer (no PO box).
2. **The free gift** behind `gift_url`: free gems / a free card / blackjack seat? (rides `ak_grants`).
3. **Sender address**: OK to send from `dealer@everlightventures.io` for now, or verify a dedicated `bcardd` domain in Resend first (keeps brands separate)?
4. **Which Supabase project** owns BCARDD subscribers (default: the AK/shop project `jdqqmsmwmbsnlnstyavl`).
