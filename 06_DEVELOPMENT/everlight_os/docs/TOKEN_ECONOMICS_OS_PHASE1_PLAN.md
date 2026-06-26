# Token Economics OS, Phase 1: Key Registry plus Leak Fix, Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a centralized, agent-readable catalog of every API key (metadata only, never secret values) tagged to project and sub-avenue, and close the hardcoded-secret leak in `.mcp.json`.

**Architecture:** A canonical JSON manifest (`registry/key_registry.json`) is the source of truth. A `key_registry.py` module loads, validates (rejects anything that looks like a real secret), queries by project, rolls up monthly cost, and flags expiring keys. A populator seeds entries from current key NAMES in `.env` / `.mcp.json` / vault (never copying values). A renderer emits a branded human-facing `KEY_REGISTRY.html`. Secret values stay in `secrets_vault.py` / Proton; the registry only stores a `value_location` pointer.

**Tech Stack:** Python 3, stdlib only (json, dataclasses, pathlib, datetime, re), pytest for tests. No new dependencies (free-first).

## Global Constraints
- Registry stores METADATA ONLY. A validator must reject any entry whose `value_location` or any field contains a literal secret (matches a token pattern like `sk-`, `sbp_`, `cfat_`, `eyJ`, `xoxb-`, `re_`, 32+ char hex/base64 blobs).
- No em-dash anywhere in any file or output (pre_tool_guard blocks it). Use hyphen or restructure.
- Code under `03_AUTOMATION_CORE/01_Scripts/token_economics/`. After edits here, deploy doctrine applies (`deploy_to_oracle.sh`) but do NOT auto-deploy secrets.
- Crons (the expiry checker) run on e5, never the phone.
- Human-facing output is HTML, branded palette read from `content_tools/report_template.py`, not hardcoded.

---

### Task 1: Registry data model and loader

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/token_economics/__init__.py`
- Create: `03_AUTOMATION_CORE/01_Scripts/token_economics/key_registry.py`
- Create: `03_AUTOMATION_CORE/01_Scripts/token_economics/registry/key_registry.json`
- Test: `03_AUTOMATION_CORE/01_Scripts/token_economics/tests/test_key_registry.py`

**Interfaces:**
- Produces: `KeyEntry` dataclass with fields `key_name:str, project:str, sub_avenue:str, provider:str, owner:str, created:str, expires:str|None, refresh_cadence:str, monthly_cost_usd:float, status:str, value_location:str, notes:str`.
- Produces: `load_registry(path:str=DEFAULT_PATH) -> list[KeyEntry]`
- Produces: `save_registry(entries:list[KeyEntry], path:str=DEFAULT_PATH) -> None`
- Produces: `DEFAULT_PATH` constant pointing at `registry/key_registry.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_key_registry.py
import os, json, tempfile
from token_economics import key_registry as kr

def test_roundtrip_load_save():
    e = kr.KeyEntry(key_name="CF_API_TOKEN", project="infra", sub_avenue="cloudflare-pages",
                    provider="cloudflare", owner="rich", created="2026-06-25", expires=None,
                    refresh_cadence="none", monthly_cost_usd=0.0, status="live",
                    value_location="vault:CF_API_TOKEN", notes="")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "reg.json")
        kr.save_registry([e], p)
        back = kr.load_registry(p)
    assert len(back) == 1
    assert back[0].key_name == "CF_API_TOKEN"
    assert back[0].value_location == "vault:CF_API_TOKEN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && python -m pytest token_economics/tests/test_key_registry.py::test_roundtrip_load_save -v`
Expected: FAIL (module not found / KeyEntry undefined).

- [ ] **Step 3: Write minimal implementation**

```python
# key_registry.py
from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict, field
from pathlib import Path

DEFAULT_PATH = str(Path(__file__).parent / "registry" / "key_registry.json")

@dataclass
class KeyEntry:
    key_name: str
    project: str
    sub_avenue: str
    provider: str
    owner: str
    created: str
    expires: str | None
    refresh_cadence: str
    monthly_cost_usd: float
    status: str
    value_location: str
    notes: str = ""

def load_registry(path: str = DEFAULT_PATH) -> list[KeyEntry]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        raw = json.load(f)
    return [KeyEntry(**row) for row in raw]

def save_registry(entries: list[KeyEntry], path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)
```

Also create empty `__init__.py` and seed `registry/key_registry.json` with `[]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 03_AUTOMATION_CORE/01_Scripts && python -m pytest token_economics/tests/test_key_registry.py::test_roundtrip_load_save -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/token_economics/
git commit -m "feat(teo): key registry data model and loader"
```

---

### Task 2: Secret-leak guard (the metadata-only enforcer)

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/token_economics/key_registry.py`
- Test: `03_AUTOMATION_CORE/01_Scripts/token_economics/tests/test_key_registry.py`

**Interfaces:**
- Produces: `SECRET_PATTERNS:list[str]` (regexes for known token shapes).
- Produces: `looks_like_secret(value:str) -> bool`
- Produces: `validate_registry(entries:list[KeyEntry]) -> list[str]` returning a list of human-readable violations (empty list means clean). Validation fails if any field other than allowed pointer prefixes contains a secret-shaped string.

- [ ] **Step 1: Write the failing test**

```python
def test_rejects_embedded_secret():
    bad = kr.KeyEntry(key_name="OPENAI", project="llm", sub_avenue="content",
                      provider="openai", owner="rich", created="2026-06-25", expires=None,
                      refresh_cadence="none", monthly_cost_usd=0.0, status="live",
                      value_location="sk-proj-ABC123definitelyasecretkey0000", notes="")
    violations = kr.validate_registry([bad])
    assert violations, "a literal sk- secret must be flagged"

def test_accepts_pointer():
    ok = kr.KeyEntry(key_name="OPENAI", project="llm", sub_avenue="content",
                     provider="openai", owner="rich", created="2026-06-25", expires=None,
                     refresh_cadence="none", monthly_cost_usd=0.0, status="live",
                     value_location="vault:OPENAI_API_KEY", notes="")
    assert kr.validate_registry([ok]) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest token_economics/tests/test_key_registry.py -k secret -v` (from `01_Scripts`)
Expected: FAIL (validate_registry undefined).

- [ ] **Step 3: Implement**

```python
import re
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{16,}", r"sbp_[A-Za-z0-9]{16,}", r"cfat_[A-Za-z0-9_\-]{16,}",
    r"xox[baprs]-[A-Za-z0-9\-]{10,}", r"re_[A-Za-z0-9]{16,}", r"eyJ[A-Za-z0-9_\-]{20,}",
    r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}", r"\b[0-9a-fA-F]{40,}\b",
]
_ALLOWED_PREFIXES = ("vault:", "proton:", "env:", "file:")

def looks_like_secret(value: str) -> bool:
    return any(re.search(p, value or "") for p in SECRET_PATTERNS)

def validate_registry(entries: list[KeyEntry]) -> list[str]:
    out = []
    for e in entries:
        vl = e.value_location or ""
        if not vl.startswith(_ALLOWED_PREFIXES):
            out.append(f"{e.key_name}: value_location must be a pointer ({', '.join(_ALLOWED_PREFIXES)}), got '{vl[:12]}...'")
        for fname in ("value_location", "notes", "key_name"):
            if looks_like_secret(getattr(e, fname)):
                out.append(f"{e.key_name}: field '{fname}' contains a secret-shaped string; store the value in the vault, keep only a pointer")
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest token_economics/tests/test_key_registry.py -k secret -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/token_economics/
git commit -m "feat(teo): metadata-only secret-leak guard for registry"
```

---

### Task 3: Query and cost-rollup helpers

**Files:**
- Modify: `key_registry.py`; Test: `tests/test_key_registry.py`

**Interfaces:**
- Produces: `by_project(entries) -> dict[str, list[KeyEntry]]`
- Produces: `monthly_cost_by_project(entries) -> dict[str, float]`
- Produces: `expiring_within(entries, days:int, today:str) -> list[KeyEntry]` (today as ISO string for deterministic tests; entries with `expires=None` never match).

- [ ] **Step 1: Failing test**

```python
def _mk(name, proj, cost, expires=None):
    return kr.KeyEntry(name, proj, "x", "p", "rich", "2026-06-01", expires, "none", cost, "live", f"vault:{name}", "")

def test_cost_rollup_and_expiry():
    es = [_mk("A","alley_kingz",5.0), _mk("B","alley_kingz",2.5), _mk("C","bcardi",1.0,"2026-07-01")]
    assert kr.monthly_cost_by_project(es)["alley_kingz"] == 7.5
    soon = kr.expiring_within(es, 30, today="2026-06-25")
    assert [e.key_name for e in soon] == ["C"]
```

- [ ] **Step 2: Run, expect FAIL.** `python -m pytest token_economics/tests/test_key_registry.py -k rollup -v`

- [ ] **Step 3: Implement**

```python
from datetime import date
from collections import defaultdict

def by_project(entries):
    d = defaultdict(list)
    for e in entries:
        d[e.project].append(e)
    return dict(d)

def monthly_cost_by_project(entries):
    d = defaultdict(float)
    for e in entries:
        d[e.project] += float(e.monthly_cost_usd or 0)
    return dict(d)

def expiring_within(entries, days, today):
    t = date.fromisoformat(today)
    out = []
    for e in entries:
        if not e.expires:
            continue
        if 0 <= (date.fromisoformat(e.expires) - t).days <= days:
            out.append(e)
    return out
```

- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(teo): registry query + cost rollup + expiry helpers"`

---

### Task 4: Populate the registry from current key NAMES (no values)

**Files:**
- Create: `token_economics/populate_registry.py`

**What it does:** Reads key NAMES (not values) from `03_AUTOMATION_CORE/03_Credentials/.env` (split on first `=`, keep left side only), scans `.mcp.json` for hardcoded secret-shaped values and records the key NAME plus a `LEAK` flag, lists vault keys via `secrets_vault.py list` (names only). Infers `project`/`sub_avenue` from name prefixes using a `PREFIX_MAP`; anything unmatched gets `project="UNCONFIRMED"` so Rich verifies rather than us guessing silently. Writes entries through `validate_registry` before saving; aborts if any violation.

- [ ] **Step 1:** Write `populate_registry.py` with `PREFIX_MAP = {"CF_":("infra","cloudflare"), "CLOUDFLARE_":("infra","cloudflare"), "SUPABASE_":("infra","supabase"), "ANTHROPIC_":("llm","shared-inference"), "OPENAI_":("llm","shared-inference"), "OPENROUTER_":("llm","fallback-routing"), "RESEND_":("comms","email"), "SLACK_":("comms","slack"), "ELEVENLABS_":("comms","voice"), "TELEGRAM_":("bcardi","telegram"), "BCARDD_":("bcardi","community"), "AK_":("alley_kingz","game"), "STRIPE_":("revenue","checkout"), "GITHUB_":("infra","ci-deploy"), "KALSHI_":("trading","kalshi"), "COINBASE_":("trading","xlm-bot")}`. Each unmatched name -> `("UNCONFIRMED","UNCONFIRMED")`. Default `status="live"`, `monthly_cost_usd=0.0` (filled in Phase 2), `value_location=f"vault:{name}"` if in vault else `f"env:{name}"`.
- [ ] **Step 2:** Run it: `cd 03_AUTOMATION_CORE/01_Scripts && python token_economics/populate_registry.py`. Expected output: a count of entries written and a list of any `UNCONFIRMED` keys + any `LEAK` keys found in `.mcp.json`.
- [ ] **Step 3:** Manually review `registry/key_registry.json`. Confirm NO secret values present (run `python -c "from token_economics import key_registry as kr; print(kr.validate_registry(kr.load_registry()))"` expecting `[]`).
- [ ] **Step 4: Commit** `git commit -m "feat(teo): populate key registry from current key names"`. NOTE: confirm `.env` values are NOT in the committed JSON before pushing.

---

### Task 5: Close the .mcp.json leak

**Files:**
- Modify: `.mcp.json` (root); Create: `token_economics/scrub_mcp_secrets.py`

**What it does:** First verify whether `.mcp.json` is git-tracked (`git ls-files --error-unmatch .mcp.json`). For each hardcoded secret-shaped value found in Task 4: store the value into the vault under its key name (`secrets_vault.py set <NAME> '<val>'`), then replace the literal in `.mcp.json` with an env-var reference (`${NAME}`). Produce a `ROTATE_THESE.md` checklist listing every key that was exposed in git history and therefore must be rotated provider-side by Rich (we do NOT auto-rotate live keys).

- [ ] **Step 1:** Run `git ls-files --error-unmatch .mcp.json` to confirm tracking status; record result.
- [ ] **Step 2:** For each leaked key: `python content_tools/secrets_vault.py set <NAME> '<value>'`, verify with `get`, then edit `.mcp.json` to replace the literal with `${NAME}`.
- [ ] **Step 3:** Write `ROTATE_THESE.md` listing exposed keys + provider rotation URLs. Hand to Rich (he holds rotation authority).
- [ ] **Step 4:** Re-run `validate_registry` and `git diff .mcp.json` to confirm no literals remain.
- [ ] **Step 5: Commit** `git commit -m "fix(teo): move hardcoded mcp secrets to vault, replace with refs"` (verify diff shows refs, not values).

---

### Task 6: Branded human-facing HTML view

**Files:**
- Create: `token_economics/render_registry.py`; Output: `token_economics/KEY_REGISTRY.html`

**What it does:** Reads the JSON, groups by project, renders a gold-branded table (palette + fonts read from `content_tools/report_template.py`, never hardcoded) with columns key/sub-avenue/provider/owner/expires/monthly-cost/status, a per-project cost subtotal, and a highlighted "expiring within 30 days" and "UNCONFIRMED" section up top. Auto-open for Rich on completion (VIEW intent doctrine).

- [ ] **Step 1:** Write `render_registry.py` importing the palette from `report_template.py`; build the HTML string; write `KEY_REGISTRY.html`.
- [ ] **Step 2:** Run `python token_economics/render_registry.py`; confirm the file opens and shows real entries with subtotals.
- [ ] **Step 3: Commit** `git commit -m "feat(teo): branded HTML key registry view"`.

---

## Phases 2 to 5 (outline, each gets its own plan when reached)
- **Phase 2 (COGS ledger):** extend `content_tools/swarm_budget.py` to tag calls with project/sub_avenue from the registry; backfill `monthly_cost_usd` per key; per-project monthly rollup.
- **Phase 3 (Attention sink):** add analytics client shims so Alley Kingz and BCARDI emit into the Vantaris Supabase `analytics_events`/`sessions` tables; add monetization event types.
- **Phase 4 (Payback dashboard + agent):** Supabase view joining COGS to recoup income; one dashboard panel; weekly Analytical Agent on e5 posting a branded 3-format report.
- **Phase 5 (3 distribution plays):** portal-publish Alley Kingz (Playgama Bridge), wire BCARDD creator-fee wallet, monetize + route the Telegram bot.

## Self-Review notes
- Spec coverage: Phase 1 tasks cover the Key Registry pillar + leak fix fully. COGS/attention/dashboard/plays are Phases 2 to 5 (separate plans), per the spec's phasing.
- Metadata-only guard (Task 2) is the load-bearing safety control; every populate/scrub path routes through `validate_registry`.
- No auto-rotation of live keys (Task 5 hands rotation to Rich) per ask-before-outward-facing doctrine.
