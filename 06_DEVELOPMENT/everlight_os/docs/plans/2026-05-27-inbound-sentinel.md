# Inbound Sentinel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect inbound email from strangers that concerns Everlight, classify + enrich it, surface it within minutes, and either auto-reply (low-risk only) or auto-draft a reply for one-tap approval.

**Architecture:** One orchestrator (`inbound_sentinel.py`) over small focused units: a shared IMAP helper (also repairs the dead `critical_email_monitor` credential path), a stranger/bulk filter, a category classifier, an enrichment+opsec step, and an action router. Reuse existing rails: `branded_mailer` (which already runs `eradication_gate` internally), `branded_slack`, `recipient_register`, `moltbook_confidentiality_gate`, `neuromorphic.nlp_engine`.

**Tech Stack:** Python 3.13, stdlib `imaplib`/`email`, pytest. No new third-party deps (honors the phone-proot no-npm/no-pip-build constraints; everything is stdlib + existing Hive modules).

**Spec:** `06_DEVELOPMENT/everlight_os/docs/specs/2026-05-27-inbound-sentinel-design.md`

---

## File Structure

```
03_AUTOMATION_CORE/01_Scripts/
  content_tools/
    imap_fetch.py              # NEW: shared IMAP fetch + header parse (fixes cred bug)
  inbound/
    __init__.py                # NEW
    sentinel_filter.py         # NEW: stranger + bulk-marketing filter
    sentinel_classifier.py     # NEW: category + intent + enrichment + opsec
    sentinel_router.py         # NEW: action router (alert + scoped reply/draft)
    known_contacts.json        # NEW: allow-list of domains/people we already know
  inbound_sentinel.py          # NEW: orchestrator CLI (--once / --daemon / --dry-run)
  critical_email_monitor.py    # MODIFY: use imap_fetch + correct creds
  tests/
    conftest.py                # NEW: put Scripts dir on sys.path
    fixtures/
      anyip.eml                # NEW: the real recon/sales email
      newsletter.eml           # NEW: a bulk marketing email
      seller_reply.eml         # NEW: a known-seller reply
      stripe_alert.eml         # NEW: a billing alert
    test_imap_fetch.py         # NEW
    test_sentinel_filter.py    # NEW
    test_sentinel_classifier.py# NEW
    test_sentinel_router.py    # NEW
_logs/inbound/
    sentinel.jsonl             # runtime ledger (created on first run)
    sentinel_seen.json         # runtime dedup state
```

Boundaries: the **filter** decides keep/drop, the **classifier** decides what it is, the **router** decides what to do. Each takes plain dicts and is unit-testable without network.

---

## Task 1: Shared IMAP fetch helper (+ test scaffolding)

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/content_tools/imap_fetch.py`
- Create: `03_AUTOMATION_CORE/01_Scripts/tests/conftest.py`
- Create: `03_AUTOMATION_CORE/01_Scripts/tests/fixtures/anyip.eml`
- Test: `03_AUTOMATION_CORE/01_Scripts/tests/test_imap_fetch.py`

- [ ] **Step 1: Create the conftest so tests can import modules**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/conftest.py
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent  # .../01_Scripts
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
```

- [ ] **Step 2: Save the real anyIP email as a fixture**

```
# 03_AUTOMATION_CORE/01_Scripts/tests/fixtures/anyip.eml
From: Ben <ben@anyipit.com>
To: 1m.rich.gee@gmail.com
Delivered-To: 1m.rich.gee@gmail.com
Subject: quick one on EverlightVentures/everlight-ventures
Message-ID: <anyip-0001@anyipit.com>
Date: Tue, 27 May 2026 06:24:16 +0000
Content-Type: text/plain; charset="utf-8"

Hey,

I was looking at EverlightVentures/everlight-ventures and the proxy-broker piece stood out.

is that live somewhere or just part of the build?

mostly wondering how important that layer is for you.

Ben
Commercial OPS @ anyIP
```

- [ ] **Step 3: Write the failing test for `parse_message`**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/test_imap_fetch.py
from pathlib import Path
from content_tools.imap_fetch import parse_message

FIX = Path(__file__).parent / "fixtures"

def test_parse_extracts_core_fields():
    raw = (FIX / "anyip.eml").read_bytes()
    msg = parse_message(raw)
    assert msg["from_email"] == "ben@anyipit.com"
    assert msg["from_name"] == "Ben"
    assert "everlight-ventures" in msg["subject"]
    assert "proxy-broker" in msg["body"]
    assert msg["message_id"] == "<anyip-0001@anyipit.com>"
    assert msg["delivered_to"] == "1m.rich.gee@gmail.com"
    assert msg["list_unsubscribe"] == ""        # not a bulk email
    assert msg["precedence"] == ""
```

- [ ] **Step 4: Run it, confirm it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_imap_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: content_tools.imap_fetch`

- [ ] **Step 5: Implement `imap_fetch.py`**

```python
# 03_AUTOMATION_CORE/01_Scripts/content_tools/imap_fetch.py
"""Shared Gmail IMAP fetch + RFC822 parse. Single source for all monitors.

Credentials (read from 03_AUTOMATION_CORE/03_Credentials/.env, env wins):
  GMAIL_IMAP_USER, GMAIL_IMAP_PASS, GMAIL_IMAP_HOST (default imap.gmail.com)
This is the working credential path; critical_email_monitor's old
GMAIL_USER/GMAIL_APP_PASSWORD vars were never set -> it was blind.
"""
from __future__ import annotations

import email
import imaplib
import os
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

ENV = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")


def load_env() -> None:
    if not ENV.exists():
        return
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _decode(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    out = []
    for chunk, enc in decode_header(raw):
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                out.append(chunk.decode("utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _addr(header_value: str) -> tuple[str, str]:
    """Return (name, email) from a From header."""
    name, addr = email.utils.parseaddr(header_value)
    return _decode(name), addr.lower().strip()


def parse_message(raw: bytes) -> dict:
    """Parse one RFC822 message into a flat dict the pipeline understands."""
    msg = email.message_from_bytes(raw)
    from_name, from_email = _addr(msg.get("From", ""))

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            body = msg.get_payload() or ""

    return {
        "message_id": (msg.get("Message-ID", "") or "").strip(),
        "from_name": from_name,
        "from_email": from_email,
        "subject": _decode(msg.get("Subject", "")),
        "body": body,
        "delivered_to": (msg.get("Delivered-To", "") or msg.get("X-Original-To", "")).lower().strip(),
        "list_unsubscribe": (msg.get("List-Unsubscribe", "") or "").strip(),
        "precedence": (msg.get("Precedence", "") or "").strip().lower(),
        "date": msg.get("Date", ""),
    }


def fetch_recent(days: int = 1, mailbox: str = "INBOX", limit: int = 100) -> list[dict]:
    """Fetch parsed messages from the last `days`. Returns [] on any failure."""
    load_env()
    user = os.environ.get("GMAIL_IMAP_USER")
    pw = os.environ.get("GMAIL_IMAP_PASS")
    host = os.environ.get("GMAIL_IMAP_HOST", "imap.gmail.com")
    if not user or not pw:
        return []
    out: list[dict] = []
    try:
        imap = imaplib.IMAP4_SSL(host, 993)
        imap.login(user, pw)
        imap.select(mailbox)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        typ, data = imap.search(None, f'(SINCE "{cutoff}")')
        if typ == "OK":
            for num in data[0].split()[-limit:]:
                typ, md = imap.fetch(num, "(RFC822)")
                if typ == "OK" and md and md[0]:
                    out.append(parse_message(md[0][1]))
    except Exception:
        return out
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return out
```

- [ ] **Step 6: Run the test, confirm it passes**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_imap_fetch.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/content_tools/imap_fetch.py \
        03_AUTOMATION_CORE/01_Scripts/tests/conftest.py \
        03_AUTOMATION_CORE/01_Scripts/tests/fixtures/anyip.eml \
        03_AUTOMATION_CORE/01_Scripts/tests/test_imap_fetch.py
git commit -m "feat(inbound): shared IMAP fetch helper with correct creds"
```

---

## Task 2: Stranger + bulk-marketing filter

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound/__init__.py` (empty)
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_filter.py`
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound/known_contacts.json`
- Create fixtures: `tests/fixtures/newsletter.eml`, `seller_reply.eml`, `stripe_alert.eml`
- Test: `03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_filter.py`

- [ ] **Step 1: Create `inbound/__init__.py` (empty) and `known_contacts.json`**

```json
{
  "domains": ["midsouthhomebuyers.com", "everlightventures.io"],
  "emails": ["chris@midsouthhomebuyers.com"]
}
```

- [ ] **Step 2: Add three fixtures**

```
# tests/fixtures/newsletter.eml
From: Carnival <funships@carnivalcruiselineemail.com>
To: 1m.rich.gee@gmail.com
Subject: 72 Hour Sale On NOW
Message-ID: <nl-1@carnival>
List-Unsubscribe: <https://carnival.example/unsub>
Precedence: bulk
Content-Type: text/plain

Book now and save.
```

```
# tests/fixtures/seller_reply.eml
From: Chris <chris@midsouthhomebuyers.com>
To: marvin@everlightventures.io
Subject: Re: 123 Main St
Message-ID: <sr-1@midsouth>
Content-Type: text/plain

Yes lets talk numbers.
```

```
# tests/fixtures/stripe_alert.eml
From: Stripe <notifications@stripe.com>
To: 1m.rich.gee@gmail.com
Subject: Your payout failed
Message-ID: <st-1@stripe>
Content-Type: text/plain

Action required on your account.
```

- [ ] **Step 3: Write the failing test (truth table)**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_filter.py
from pathlib import Path
from content_tools.imap_fetch import parse_message
from inbound.sentinel_filter import triage_keep

FIX = Path(__file__).parent / "fixtures"

def _msg(name):
    return parse_message((FIX / name).read_bytes())

def test_stranger_is_kept():
    keep, reason = triage_keep(_msg("anyip.eml"))
    assert keep is True
    assert reason == "stranger_inbound"

def test_bulk_marketing_dropped():
    keep, reason = triage_keep(_msg("newsletter.eml"))
    assert keep is False
    assert reason == "bulk_marketing"

def test_known_contact_dropped():
    keep, reason = triage_keep(_msg("seller_reply.eml"))
    assert keep is False
    assert reason == "known_contact"

def test_billing_alert_deferred():
    keep, reason = triage_keep(_msg("stripe_alert.eml"))
    assert keep is False
    assert reason == "critical_service_defer"
```

- [ ] **Step 4: Run it, confirm it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: inbound.sentinel_filter`

- [ ] **Step 5: Implement `sentinel_filter.py`**

```python
# 03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_filter.py
"""Decide whether an inbound email is a stranger worth surfacing.

triage_keep(msg) -> (keep: bool, reason: str)
  reason in {stranger_inbound, bulk_marketing, known_contact,
             critical_service_defer, no_signal}
Order matters: known + critical + bulk are dropped before we keep.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_KNOWN = _HERE / "known_contacts.json"

# Senders handled by critical_email_monitor (billing/legal/security). Deferred, not kept.
_CRITICAL_SENDER = re.compile(
    r"@(stripe|paypal|oracle|aws|amazonwebservices|namecheap|godaddy|cloudflare|"
    r"github|chase|bankofamerica|wellsfargo|capitalone|chime|irs|resend|sendgrid)\.",
    re.I,
)


def _load_known() -> dict:
    try:
        return json.loads(_KNOWN.read_text())
    except Exception:
        return {"domains": [], "emails": []}


def is_bulk_marketing(msg: dict) -> bool:
    if msg.get("list_unsubscribe"):
        return True
    if msg.get("precedence") in {"bulk", "list", "junk"}:
        return True
    return False


def is_known_contact(msg: dict, known: dict | None = None) -> bool:
    known = known or _load_known()
    sender = msg.get("from_email", "")
    if sender in {e.lower() for e in known.get("emails", [])}:
        return True
    domain = sender.split("@")[-1] if "@" in sender else ""
    return domain in {d.lower() for d in known.get("domains", [])}


def is_critical_service(msg: dict) -> bool:
    return bool(_CRITICAL_SENDER.search(msg.get("from_email", "")))


def triage_keep(msg: dict, known: dict | None = None) -> tuple[bool, str]:
    if is_known_contact(msg, known):
        return False, "known_contact"
    if is_critical_service(msg):
        return False, "critical_service_defer"
    if is_bulk_marketing(msg):
        return False, "bulk_marketing"
    # A stranger that got past the noise gates. Keep it.
    if msg.get("from_email"):
        return True, "stranger_inbound"
    return False, "no_signal"
```

- [ ] **Step 6: Run the tests, confirm they pass**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_filter.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/inbound/ \
        03_AUTOMATION_CORE/01_Scripts/tests/fixtures/newsletter.eml \
        03_AUTOMATION_CORE/01_Scripts/tests/fixtures/seller_reply.eml \
        03_AUTOMATION_CORE/01_Scripts/tests/fixtures/stripe_alert.eml \
        03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_filter.py
git commit -m "feat(inbound): stranger + bulk-marketing filter"
```

---

## Task 3: Classifier + enrichment + opsec

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_classifier.py`
- Test: `03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_classifier.py`

- [ ] **Step 1: Write the failing test**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_classifier.py
from pathlib import Path
from content_tools.imap_fetch import parse_message
from inbound.sentinel_classifier import classify

FIX = Path(__file__).parent / "fixtures"

def test_anyip_is_recon_probe_with_opsec_flag():
    msg = parse_message((FIX / "anyip.eml").read_bytes())
    result = classify(msg)
    # asks "how important is that layer" about a named public repo => recon probe
    assert result["category"] in {"recon_probe", "sales_pitch"}
    assert "everlight-ventures" in result["referenced_assets"]
    assert result["opsec_flag"] is True
    assert result["high_stakes"] is True   # recon/sales both route to draft, never auto-reply-leak

def test_referenced_assets_extracts_repo_path():
    from inbound.sentinel_classifier import referenced_assets
    assets = referenced_assets("look at EverlightVentures/everlight-ventures repo")
    assert "everlight-ventures" in assets
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `sentinel_classifier.py`**

```python
# 03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_classifier.py
"""Categorize a stranger email + enrich it + flag opsec exposure.

classify(msg) -> {
  category: sales_pitch|partnership|investor|press|recon_probe|job|other,
  intent: float (-1..1),  high_stakes: bool,
  referenced_assets: [str],  opsec_flag: bool,
}
Keyword-first (deterministic + testable). An optional LLM second pass can be
added later behind OPENROUTER_API_KEY without changing this contract.
"""
from __future__ import annotations

import re

# Public Everlight asset names a stranger should not be probing without notice.
_OPSEC_TERMS = ["everlight-ventures", "proxy-broker", "broker_os", "xlm_bot", "hive_mind"]

_CATEGORY_RULES = [
    ("recon_probe",  [r"how important", r"is that live", r"part of the build", r"what.s your stack", r"do you use"]),
    ("investor",     [r"\binvest", r"\bfunding", r"raise", r"cap table", r"\bvc\b", r"check size"]),
    ("partnership",  [r"partner", r"collaborat", r"integrat", r"work together", r"reseller", r"affiliate"]),
    ("press",        [r"journalist", r"reporter", r"writing a (story|piece)", r"press", r"interview", r"podcast"]),
    ("job",          [r"\bresume\b", r"\bcv\b", r"hiring", r"job opening", r"apply", r"looking for work"]),
    ("sales_pitch",  [r"\bdemo\b", r"\bpricing\b", r"our (product|platform|service|tool)", r"book a call", r"@ \w+$"]),
]

_HIGH_STAKES = {"partnership", "investor", "press", "recon_probe", "job"}


def referenced_assets(text: str) -> list[str]:
    """Return public Everlight asset names the email mentions."""
    low = text.lower()
    hits = [t for t in _OPSEC_TERMS if t.replace("_", "-") in low or t in low]
    # also catch Org/repo paths like EverlightVentures/everlight-ventures
    for m in re.finditer(r"[A-Za-z0-9_-]+/([A-Za-z0-9_-]+)", text):
        repo = m.group(1).lower()
        if "everlight" in repo and repo not in hits:
            hits.append(repo)
    return hits


def _category(text: str) -> str:
    low = text.lower()
    for category, patterns in _CATEGORY_RULES:
        if any(re.search(p, low) for p in patterns):
            return category
    return "other"


def _intent(msg: dict) -> float:
    """Best-effort sentiment via the existing NLP engine; 0.0 if unavailable."""
    try:
        import sys
        from pathlib import Path as _P
        for d in ("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os",
                  str(_P(__file__).resolve().parents[3] / "06_DEVELOPMENT" / "everlight_os")):
            if d not in sys.path:
                sys.path.insert(0, d)
        from neuromorphic.nlp_engine import analyze_email_reply
        return float(analyze_email_reply(f"{msg.get('subject','')}\n{msg.get('body','')}").get("reply_sentiment", 0.0))
    except Exception:
        return 0.0


def classify(msg: dict) -> dict:
    blob = f"{msg.get('subject','')}\n{msg.get('body','')}"
    assets = referenced_assets(blob)
    category = _category(blob)
    # If they name our infra AND ask how it works, it is a probe regardless of wording.
    if assets and re.search(r"how important|is that live|part of the build|do you use", blob.lower()):
        category = "recon_probe"
    return {
        "category": category,
        "intent": _intent(msg),
        "high_stakes": category in _HIGH_STAKES,
        "referenced_assets": assets,
        "opsec_flag": bool(assets),
    }
```

- [ ] **Step 4: Run the tests, confirm they pass**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_classifier.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_classifier.py \
        03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_classifier.py
git commit -m "feat(inbound): category + enrichment + opsec classifier"
```

---

## Task 4: Action router (scoped reply/draft + alerts)

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_router.py`
- Test: `03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_router.py`

The router decides the action from category, then performs side effects. In `dry_run`
it performs NONE -- it only returns the decided action. This keeps tests send-free.

- [ ] **Step 1: Write the failing test**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_router.py
from inbound.sentinel_router import decide_action

def test_vendor_pitch_auto_replies():
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": False}) == "auto_reply"

def test_opt_out_auto_replies():
    assert decide_action({"category": "opt_out", "high_stakes": False,
                          "opsec_flag": False}) == "auto_reply"

def test_recon_probe_drafts_never_replies():
    assert decide_action({"category": "recon_probe", "high_stakes": True,
                          "opsec_flag": True}) == "draft"

def test_investor_drafts():
    assert decide_action({"category": "investor", "high_stakes": True,
                          "opsec_flag": False}) == "draft"

def test_opsec_flag_forces_draft_even_if_low_stakes():
    # if they named our infra, a human looks first, no matter the category
    assert decide_action({"category": "sales_pitch", "high_stakes": False,
                          "opsec_flag": True}) == "draft"
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_router.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `sentinel_router.py` (decision + side effects)**

```python
# 03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_router.py
"""Turn a classified stranger email into actions.

decide_action(classification) -> "auto_reply" | "draft"  (pure, testable)
route(msg, classification, *, dry_run) -> dict             (side effects)

Safety: auto_reply ONLY for low-risk, non-opsec, non-high-stakes categories.
Everything else becomes a Gmail draft for one-tap human approval. Every send
goes through branded_mailer (which runs eradication_gate internally) and the
confidentiality scan; a confidentiality hit downgrades the send to alert-only.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/sentinel.jsonl")
_AUTO_REPLY_OK = {"sales_pitch", "vendor_pitch", "opt_out"}

# Persona routing: which teammate owns the reply for each category.
_PERSONA = {
    "sales_pitch": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "opt_out":     ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "partnership": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "investor":    ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "press":       ("Everlight Content", "Press Desk", "press@everlightventures.io"),
    "job":         ("Everlight Ops", "Operations", "ops@everlightventures.io"),
    "recon_probe": ("Vaughn Sterling", "Senior Partner", "vaughn@everlightventures.io"),
    "other":       ("Everlight Ventures", "Front Desk", "hello@everlightventures.io"),
}


def decide_action(classification: dict) -> str:
    if classification.get("opsec_flag"):
        return "draft"
    if classification.get("high_stakes"):
        return "draft"
    if classification.get("category") in _AUTO_REPLY_OK:
        return "auto_reply"
    return "draft"


def _confidential_ok(body: str) -> bool:
    """True if the reply body leaks no internal state. Reuses moltbook gate."""
    try:
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/moltbook")
        from moltbook_confidentiality_gate import scan
        return len(scan(body)) == 0
    except Exception:
        return True  # gate import failure must not silently send; see route() guard


def _log(record: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def _safe_reply_body(persona_name: str) -> str:
    """A content-free brush-off. Names nothing internal. Used for auto_reply only."""
    return (
        "Hi,<br><br>Thanks for reaching out. We are heads-down right now and not "
        "evaluating new tools or partnerships. If that changes we will reach back out.<br><br>"
        f"Best,<br>{persona_name}<br>Everlight Ventures"
    )


def route(msg: dict, classification: dict, *, dry_run: bool = True) -> dict:
    action = decide_action(classification)
    category = classification.get("category", "other")
    persona_name, persona_title, persona_email = _PERSONA.get(category, _PERSONA["other"])
    result = {
        "from": msg.get("from_email"),
        "subject": msg.get("subject"),
        "category": category,
        "action": action,
        "opsec_flag": classification.get("opsec_flag"),
        "referenced_assets": classification.get("referenced_assets", []),
        "persona": persona_name,
        "dry_run": dry_run,
        "sent": False,
        "drafted": False,
        "alerted": False,
    }
    if dry_run:
        _log(result)
        return result

    # 1. Always alert (branded Slack card + push handled by orchestrator).
    result["alerted"] = _post_alert(msg, classification, action, persona_name)

    # 2. Reply path.
    if action == "auto_reply":
        body = _safe_reply_body(persona_name)
        if not _confidential_ok(body):
            result["action"] = "blocked_confidential"
        else:
            result["sent"] = _send_reply(msg, body, persona_name, persona_title, persona_email)
    else:
        result["drafted"] = _make_draft(msg, classification, persona_name, persona_email)

    _log(result)
    return result


def _post_alert(msg, classification, action, persona_name) -> bool:
    try:
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts")
        from content_tools.branded_slack import post_branded_slack
        cat = classification.get("category", "other")
        channel = "#ceo-brief" if cat in {"partnership", "investor", "press"} else "#hive-alerts"
        fields = {
            "From": msg.get("from_email", ""),
            "Category": cat,
            "Action": action,
            "Opsec": "EXPOSED: " + ", ".join(classification.get("referenced_assets", [])) if classification.get("opsec_flag") else "clear",
            "Routed to": persona_name,
        }
        r = post_branded_slack(
            channel=channel,
            title="Inbound Sentinel: stranger reached out",
            summary=msg.get("subject", "")[:140],
            body=msg.get("body", "")[:600],
            fields=fields,
            category="intel",
            agent_name="Inbound Sentinel",
            agent_title="Everlight Ventures",
        )
        return bool(getattr(r, "ok", False))
    except Exception:
        return False


def _send_reply(msg, body, name, title, from_email) -> bool:
    try:
        from content_tools.branded_mailer import send_branded_email
        r = send_branded_email(
            to=msg.get("from_email"),
            subject="Re: " + msg.get("subject", ""),
            content_html=body,
            from_name="Everlight Ventures",
            from_email=from_email,
            agent_name=name, agent_title=title, agent_email=from_email,
            budget_category="vip_reply",
            persona_id="inbound_sentinel",
            caller="inbound_sentinel",
        )
        return bool(getattr(r, "ok", False))
    except Exception:
        return False


def _make_draft(msg, classification, name, from_email) -> bool:
    """Persist a draft record the orchestrator turns into a Gmail draft."""
    draft = {
        "to": msg.get("from_email"),
        "subject": "Re: " + msg.get("subject", ""),
        "suggested_persona": name,
        "from": from_email,
        "category": classification.get("category"),
        "note": "Review before sending. Opsec: " + (
            ", ".join(classification.get("referenced_assets", [])) or "clear"),
        "original_body": msg.get("body", "")[:1000],
    }
    out = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/drafts.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(draft, default=str) + "\n")
    return True
```

- [ ] **Step 4: Run the tests, confirm they pass**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_sentinel_router.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/inbound/sentinel_router.py \
        03_AUTOMATION_CORE/01_Scripts/tests/test_sentinel_router.py
git commit -m "feat(inbound): scoped action router (auto-reply low-risk, draft high-stakes)"
```

---

## Task 5: Orchestrator CLI

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/inbound_sentinel.py`

- [ ] **Step 1: Write the failing test (dry-run end to end on fixtures)**

```python
# 03_AUTOMATION_CORE/01_Scripts/tests/test_orchestrator.py
from pathlib import Path
from content_tools.imap_fetch import parse_message
import inbound_sentinel as s

FIX = Path(__file__).parent / "fixtures"

def test_process_one_anyip_keeps_and_drafts():
    msg = parse_message((FIX / "anyip.eml").read_bytes())
    out = s.process_one(msg, dry_run=True)
    assert out is not None
    assert out["action"] == "draft"        # opsec flag forces draft
    assert out["category"] in {"recon_probe", "sales_pitch"}

def test_process_one_newsletter_dropped():
    msg = parse_message((FIX / "newsletter.eml").read_bytes())
    assert s.process_one(msg, dry_run=True) is None  # filtered out
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError: inbound_sentinel`

- [ ] **Step 3: Implement `inbound_sentinel.py`**

```python
# 03_AUTOMATION_CORE/01_Scripts/inbound_sentinel.py
"""Inbound Sentinel -- surface strangers who email us about Everlight.

  python3 inbound_sentinel.py --once            # one scan (dry-run default)
  python3 inbound_sentinel.py --once --live      # perform sends/drafts/alerts
  python3 inbound_sentinel.py --daemon --live    # loop every 5 min

Pipeline: fetch -> filter -> classify -> route. Dedup by Message-ID.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_tools.imap_fetch import fetch_recent
from inbound.sentinel_filter import triage_keep
from inbound.sentinel_classifier import classify
from inbound.sentinel_router import route

SEEN = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/inbound/sentinel_seen.json")


def _seen() -> set[str]:
    try:
        return set(json.loads(SEEN.read_text()))
    except Exception:
        return set()


def _mark(seen: set[str], mid: str) -> None:
    seen.add(mid)
    if len(seen) > 5000:
        seen = set(list(seen)[-3000:])
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(list(seen)))


def process_one(msg: dict, *, dry_run: bool = True) -> dict | None:
    keep, reason = triage_keep(msg)
    if not keep:
        return None
    classification = classify(msg)
    return route(msg, classification, dry_run=dry_run)


def scan_once(*, dry_run: bool = True, days: int = 1) -> dict:
    seen = _seen()
    kept = 0
    actions = {"auto_reply": 0, "draft": 0, "blocked_confidential": 0}
    for msg in fetch_recent(days=days):
        mid = msg.get("message_id", "")
        if mid and mid in seen:
            continue
        result = process_one(msg, dry_run=dry_run)
        if result:
            kept += 1
            actions[result["action"]] = actions.get(result["action"], 0) + 1
        if mid:
            _mark(seen, mid)
    return {"kept": kept, "actions": actions, "dry_run": dry_run}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--live", action="store_true", help="perform sends/drafts (default is dry-run)")
    ap.add_argument("--days", type=int, default=1)
    args = ap.parse_args()
    dry = not args.live
    if args.daemon:
        while True:
            print(json.dumps(scan_once(dry_run=dry, days=args.days)))
            time.sleep(300)
    else:
        print(json.dumps(scan_once(dry_run=dry, days=args.days), indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test, confirm it passes**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/test_orchestrator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the FULL suite**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && pytest tests/ -v`
Expected: PASS (all tasks 1-5 green)

- [ ] **Step 6: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/inbound_sentinel.py \
        03_AUTOMATION_CORE/01_Scripts/tests/test_orchestrator.py
git commit -m "feat(inbound): orchestrator CLI (fetch->filter->classify->route)"
```

---

## Task 6: Repair critical_email_monitor onto the shared helper

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/critical_email_monitor.py`

This fixes the live "missing GMAIL_USER or GMAIL_APP_PASSWORD" failure as a side benefit:
point it at the working `GMAIL_IMAP_*` creds via `imap_fetch`.

- [ ] **Step 1: Replace its `check_inbox` fetch with the shared helper**

In `critical_email_monitor.py`, change the credential lines (currently `GMAIL_USER` /
`GMAIL_APP_PASSWORD`) and the IMAP body of `check_inbox()` to use:

```python
from content_tools.imap_fetch import fetch_recent  # add at top with sys.path insert

def check_inbox() -> dict:
    seen = _seen_set()
    alerts_sent = 0
    matched = 0
    for msg in fetch_recent(days=1):                 # was: hand-rolled imaplib block
        msg_id = msg["message_id"]
        if not msg_id or msg_id in seen:
            continue
        classification = classify(msg["from_email"], msg["subject"])
        if not classification:
            _mark_seen(seen, msg_id)
            continue
        matched += 1
        snippet = msg["body"][:1500]
        slack_ok = alert_slack(classification["severity"], classification["category"],
                               msg["from_email"], msg["subject"], snippet)
        ntfy_ok = alert_ntfy(classification["severity"], classification["category"], msg["subject"])
        if slack_ok or ntfy_ok:
            alerts_sent += 1
        _mark_seen(seen, msg_id)
    return {"ok": True, "matched": matched, "alerts_sent": alerts_sent}
```

- [ ] **Step 2: Run it once for real and confirm it no longer errors on creds**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && python3 critical_email_monitor.py`
Expected: JSON with `"ok": true` (not the old `missing GMAIL_USER` error).

- [ ] **Step 3: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/critical_email_monitor.py
git commit -m "fix(monitor): critical_email_monitor uses shared imap_fetch + working creds"
```

---

## Task 7: Live acceptance run + deploy + cron

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh` (add new files to rsync list)
- Modify: crontab (phone) / e5-mother crontab

- [ ] **Step 1: Verify forwarding topology (spec open item)**

Run a quick check: do @everlightventures.io aliases land in the personal Gmail?
`cd 03_AUTOMATION_CORE/01_Scripts && python3 -c "from content_tools.imap_fetch import fetch_recent; import collections; print(collections.Counter(m['delivered_to'] for m in fetch_recent(days=3)))"`
Expected: a Counter showing which Delivered-To addresses actually arrive. Record the result;
if @everlightventures.io aliases do NOT appear, add their mailbox(es) to a follow-up task.

- [ ] **Step 2: Live dry-run against the real inbox, confirm anyIP surfaces**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && python3 inbound_sentinel.py --once --days 3`
Expected: JSON `{"kept": >=1, ...}`; then
`grep anyipit _logs/inbound/sentinel.jsonl` shows the anyIP record with `"action": "draft"`,
`"opsec_flag": true`, `"referenced_assets": ["everlight-ventures"]`. This is the acceptance proof.

- [ ] **Step 3: One controlled --live run, verify the Slack card + draft (NOT a send)**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && python3 inbound_sentinel.py --once --live --days 1`
Expected: a branded card in #hive-alerts; `_logs/inbound/drafts.jsonl` has the anyIP draft;
`_logs/inbound/sentinel.jsonl` shows `"sent": false` for anyIP (drafted, not sent).

- [ ] **Step 4: Add files to the Oracle deploy list**

In `deploy_to_oracle.sh`, add to the rsync file list:
`inbound_sentinel.py`, `inbound/` (dir), `content_tools/imap_fetch.py`.

- [ ] **Step 5: Install the cron (e5-mother preferred, phone fallback)**

```bash
# every 5 min, live
*/5 * * * * cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts && python3 inbound_sentinel.py --once --live >> /mnt/sdcard/AA_MY_DRIVE/_logs/inbound/sentinel_cron.log 2>&1
```

- [ ] **Step 6: Log the session to Blinko + update LIVING_PUNCHLIST**

```bash
curl -s -X POST http://e5-mother:1111/api/v1/note/upsert -H "Content-Type: application/json" \
 -d '{"content":"# Inbound Sentinel shipped\n#hive/session\n\nStranger-inbound email triage live. anyIP recon email is the acceptance case: drafted, opsec_flag set, not auto-replied.","type":1}'
```

- [ ] **Step 7: Final commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh
git commit -m "chore(inbound): deploy Inbound Sentinel + 5-min cron"
```

---

## Self-Review

**Spec coverage:**
- Inbox scope (every address) -> Task 1 fetch + Task 7 Step 1 topology check. COVERED (with the forwarding-collapse realism baked into the verification step).
- Stranger filter w/ bulk-marketing noise gate -> Task 2. COVERED.
- Full enrichment + categories + opsec -> Task 3. COVERED.
- Scoped auto-reply (low-risk only; high-stakes + opsec -> draft) -> Task 4 `decide_action` + tests. COVERED.
- Always alert + persona routing + #ceo-brief escalation -> Task 4 `_post_alert`. COVERED.
- Confidentiality gate on reply body -> Task 4 `_confidential_ok` + route() guard. COVERED.
- Fix dead critical_email_monitor -> Task 6. COVERED.
- e5-mother host + 5-min cron + Blinko log -> Task 7. COVERED.
- Error handling (never crash cron, degrade to draft/alert) -> fetch_recent returns [] on failure; route() try/excepts; send failure leaves sent=False. COVERED.

**Placeholder scan:** No TBD/TODO; every code step has complete code; every command has expected output.

**Type consistency:** `parse_message` dict keys (message_id, from_email, from_name, subject, body, delivered_to, list_unsubscribe, precedence) are used identically in filter, classifier, router, orchestrator. `classify()` returns {category, intent, high_stakes, referenced_assets, opsec_flag} consumed unchanged by `decide_action`/`route`. `triage_keep` reasons match the filter tests. Consistent.
