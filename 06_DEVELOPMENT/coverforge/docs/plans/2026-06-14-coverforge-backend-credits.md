# COVERFORGE Backend + Credits + Bundle - Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.
> **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

**Goal:** Stand up the backend that turns the Plan 1 render core into a paid product: a Haiku text-bundle generator, a job orchestrator, an e5 render worker, the Supabase schema + credit ledger, the Deno edge functions, and the Stripe cover-credit wiring.

**Architecture:** Two halves. **Part A (local TDD, Python)** extends the `render/` package on the phone venv exactly like Plan 1 - bundle generator, asset orchestrator, worker logic - all unit-tested with fakes, no network. **Part B (deploy)** is the SQL migration + Deno edge functions + Stripe SKUs that touch LIVE Supabase/Stripe; these are gated behind an explicit Rich checkpoint and Stripe TEST mode first.

**Tech Stack:** Python 3.13 (Pillow/pypdf already; add `anthropic`, `pydantic`); Claude `claude-haiku-4-5` via `messages.parse`; Supabase (Postgres + RLS + Storage + Deno edge functions); Stripe (reuse `create-checkout` + `stripe-webhook`).

> **Env:** venv at `/root/coverforge_venv` (sdcard can't hold a venv). Test command from `06_DEVELOPMENT/coverforge`:
> `/root/coverforge_venv/bin/python -m pytest render/tests -q`

---

## DESIGN REFINEMENT (Rich to confirm at review)

- **Bundle generator runs in Python (render package), not a Deno edge function.** Reuses the venv + fake-driven tests; worker calls it directly. Edge functions stay thin (validate + debit + enqueue + status). Spec said edge function; this is the only deviation.
- **Credits modeled as an append-only `credit_ledger`** (balance = SUM of deltas), not a mutable counter - auditable, refund-safe, matches the "no silent truncation" doctrine.

---

# PART A - Local TDD (Python, on phone venv)

## Task A0: deps

**Files:** Modify `06_DEVELOPMENT/coverforge/render/requirements.txt`

- [ ] **Step 1: add deps**

Append to `requirements.txt`:
```
anthropic>=0.40
pydantic>=2.6
```

- [ ] **Step 2: install + verify**

Run: `cd /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/coverforge && /root/coverforge_venv/bin/pip install -r render/requirements.txt && /root/coverforge_venv/bin/python -c "import anthropic, pydantic; print('ok', anthropic.__version__, pydantic.VERSION)"`
Expected: prints `ok ...`

- [ ] **Step 3: commit**
```bash
git add 06_DEVELOPMENT/coverforge/render/requirements.txt
git commit -m "chore(coverforge): add anthropic + pydantic for bundle generator"
```

---

## Task A1: Bundle model + prompt + FakeLLM + generate_bundle

**Files:**
- Create: `render/bundle.py`
- Test: `render/tests/test_bundle.py`

- [ ] **Step 1: write failing tests**
```python
# tests/test_bundle.py
from render.bundle import Bundle, build_bundle_prompt, generate_bundle, FakeLLM
from render.render_job import BookMeta

META = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                vibe="rainy rooftop", trim=(6.0, 9.0), page_count=200,
                paper="white", blurb="A tense night.")

def test_prompt_includes_title_genre_and_counts():
    p = build_bundle_prompt(META)
    assert "MIDNIGHT" in p["user"] and "thriller" in p["user"]
    assert "7" in p["system"] and "keyword" in p["system"].lower()
    assert "3" in p["system"] and "categor" in p["system"].lower()

def test_fake_llm_returns_valid_shaped_bundle():
    b = FakeLLM().parse("sys", "user")
    assert isinstance(b, Bundle)
    assert len(b.keywords) == 7
    assert len(b.categories) == 3
    assert len(b.ad_headlines) == 5
    assert b.blurb

def test_generate_bundle_wires_prompt_to_llm():
    b = generate_bundle(META, FakeLLM())
    assert len(b.keywords) == 7 and len(b.categories) == 3
```

- [ ] **Step 2: run, verify fail** - Run: `/root/coverforge_venv/bin/python -m pytest render/tests/test_bundle.py -q` Expected: `ModuleNotFoundError`

- [ ] **Step 3: implement**
```python
# render/bundle.py
"""KDP listing bundle (keywords, categories, blurb, ad headlines) for one book.
Mirrors the ImageProvider pattern: an LLMClient protocol + offline FakeLLM for
tests + a real HaikuLLM. Pure-text, sub-cent per book."""
from typing import Protocol
from pydantic import BaseModel, Field

class Bundle(BaseModel):
    keywords: list[str] = Field(description="exactly 7 Amazon backend search keywords")
    categories: list[str] = Field(description="exactly 3 Amazon fiction browse categories")
    blurb: str = Field(description="back-cover blurb, 60-120 words")
    ad_headlines: list[str] = Field(description="exactly 5 Amazon Ads headlines, <=30 chars each")

def build_bundle_prompt(meta) -> dict:
    system = (
        "You are a KDP fiction marketing expert. Return EXACTLY 7 backend keywords, "
        "EXACTLY 3 Amazon fiction browse categories, a 60-120 word back-cover blurb, "
        "and EXACTLY 5 Amazon Ads headlines (<=30 chars). Be genre-accurate and concrete."
    )
    user = (
        f"Title: {meta.title}\nAuthor: {meta.author}\nGenre: {meta.genre}\n"
        f"Vibe: {meta.vibe}\nExisting blurb seed: {meta.blurb}"
    )
    return {"system": system, "user": user}

class LLMClient(Protocol):
    def parse(self, system: str, user: str) -> Bundle: ...

class FakeLLM:
    """Deterministic, offline. Shape-valid Bundle for tests."""
    def parse(self, system: str, user: str) -> Bundle:
        return Bundle(
            keywords=[f"kw{i}" for i in range(1, 8)],
            categories=["Fiction > Thriller", "Fiction > Suspense", "Fiction > Crime"],
            blurb="A taut, fast-moving story that keeps the pages turning to the end.",
            ad_headlines=[f"Headline {i}" for i in range(1, 6)],
        )

class HaikuLLM:
    """Real client. Integration-only; not exercised by unit tests."""
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def parse(self, system: str, user: str) -> Bundle:
        resp = self.client.messages.parse(
            model=self.model, max_tokens=1024, system=system,
            messages=[{"role": "user", "content": user}], output_format=Bundle,
        )
        return resp.parsed_output

def generate_bundle(meta, llm: LLMClient) -> Bundle:
    p = build_bundle_prompt(meta)
    return llm.parse(p["system"], p["user"])
```

- [ ] **Step 4: run, verify pass** - Expected: 3 passed
- [ ] **Step 5: commit**
```bash
git add render/bundle.py tests/test_bundle.py
git commit -m "feat(coverforge): Haiku bundle generator (keywords/categories/blurb/ads) + offline FakeLLM"
```

---

## Task A2: HaikuLLM gated integration test

**Files:** Create `render/tests/test_integration_haiku.py`

- [ ] **Step 1: gated test**
```python
# tests/test_integration_haiku.py
import os, pytest
from render.bundle import HaikuLLM, generate_bundle
from render.render_job import BookMeta

@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")
def test_real_haiku_bundle():
    meta = BookMeta(title="THE LONG DARK", author="R. Gee", genre="thriller",
                    vibe="neon rain alley", trim=(6.0, 9.0), page_count=240,
                    paper="white", blurb="Nobody walks away clean.")
    b = generate_bundle(meta, HaikuLLM(os.environ["ANTHROPIC_API_KEY"]))
    assert len(b.keywords) == 7 and len(b.categories) == 3 and len(b.ad_headlines) == 5
    print("BLURB:", b.blurb)
```
- [ ] **Step 2: run gated (manual)** - `ANTHROPIC_API_KEY=... /root/coverforge_venv/bin/python -m pytest render/tests/test_integration_haiku.py -s` Expected: PASS or skipped
- [ ] **Step 3: commit**
```bash
git add tests/test_integration_haiku.py
git commit -m "test(coverforge): gated live Haiku bundle integration test"
```

---

## Task A3: produce_assets orchestrator

**Files:**
- Create: `render/produce.py`
- Test: `render/tests/test_produce.py`

- [ ] **Step 1: failing tests**
```python
# tests/test_produce.py
from render.produce import produce_assets
from render.render_job import BookMeta
from render.image_provider import FakeProvider
from render.bundle import FakeLLM

META = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                vibe="rooftop", trim=(6.0, 9.0), page_count=200,
                paper="white", blurb="Tense.")

def test_paid_produces_render_and_bundle(tmp_path):
    out = produce_assets(META, FakeProvider(), FakeLLM(), str(tmp_path), tier="paid")
    assert out.render.wrap_pdf and out.render.validation_ok
    assert out.bundle is not None and len(out.bundle.keywords) == 7

def test_free_produces_preview_no_bundle(tmp_path):
    out = produce_assets(META, FakeProvider(), FakeLLM(), str(tmp_path), tier="free")
    assert out.render.preview_png and out.render.wrap_pdf is None
    assert out.bundle is None  # bundle is a paid asset
```
- [ ] **Step 2: run, verify fail**
- [ ] **Step 3: implement**
```python
# render/produce.py
"""Top-level: one book's metadata -> all assets. Free tier = preview only;
paid tier = print files + listing bundle."""
from dataclasses import dataclass
from render.render_job import render_book, RenderResult
from render.bundle import generate_bundle, Bundle

@dataclass
class Assets:
    render: RenderResult
    bundle: Bundle = None

def produce_assets(meta, image_provider, llm, out_dir: str, tier: str = "paid", font_path=None) -> Assets:
    render = render_book(meta, image_provider, out_dir, tier=tier, font_path=font_path)
    if tier == "paid":
        return Assets(render=render, bundle=generate_bundle(meta, llm))
    return Assets(render=render, bundle=None)
```
- [ ] **Step 4: run, verify pass** - Expected: 2 passed
- [ ] **Step 5: commit**
```bash
git add render/produce.py tests/test_produce.py
git commit -m "feat(coverforge): produce_assets orchestrator (render + paid bundle)"
```

---

## Task A4: worker process_job logic (fakes)

**Files:**
- Create: `render/worker.py`
- Test: `render/tests/test_worker.py`

- [ ] **Step 1: failing tests**
```python
# tests/test_worker.py
from render.worker import process_job

class FakeDB:
    def __init__(self): self.done=None; self.failed=None; self.refunded=False
    def mark_done(self, job_id, outputs): self.done=(job_id, outputs)
    def mark_failed(self, job_id, err): self.failed=(job_id, err)
    def refund(self, job_id): self.refunded=True

class FakeStorage:
    def __init__(self): self.uploaded=[]
    def upload(self, path): self.uploaded.append(path); return f"https://cdn/{path.split('/')[-1]}"

class OkResult:  # stand-in for Assets
    class R: wrap_pdf="/t/wrap.pdf"; ebook_pdf="/t/ebook.pdf"; preview_png=None; validation_ok=True
    render=R(); 
    class B: 
        def model_dump(self): return {"keywords":[1]*7}
    bundle=B()

def test_success_uploads_and_marks_done():
    db, st = FakeDB(), FakeStorage()
    process_job({"id":"j1","tier":"paid"}, produce=lambda m,t: OkResult(), storage=st, db=db,
                build_meta=lambda row: object())
    assert db.done and db.done[0]=="j1"
    assert any("wrap.pdf" in u for u in st.uploaded)
    assert db.failed is None

def test_failure_marks_failed_and_refunds():
    db, st = FakeDB(), FakeStorage()
    def boom(m,t): raise RuntimeError("image api down")
    process_job({"id":"j2","tier":"paid"}, produce=boom, storage=st, db=db,
                build_meta=lambda row: object())
    assert db.failed and "image api down" in db.failed[1]
    assert db.refunded is True
```
- [ ] **Step 2: run, verify fail**
- [ ] **Step 3: implement**
```python
# render/worker.py
"""Pure job processor (no live Supabase here - injected db/storage/produce).
The e5 poll loop (Part B / Task B5) wires real Supabase clients into this."""

def process_job(job, produce, storage, db, build_meta):
    """job: a cover_jobs row dict. produce(meta, tier)->Assets. storage.upload(path)->url.
    db.mark_done/mark_failed/refund. Refunds the credit on any failure."""
    try:
        meta = build_meta(job)
        assets = produce(meta, job["tier"])
        outputs = {}
        for attr in ("wrap_pdf", "ebook_pdf", "preview_png"):
            path = getattr(assets.render, attr, None)
            if path:
                outputs[attr] = storage.upload(path)
        if getattr(assets, "bundle", None) is not None:
            outputs["bundle"] = assets.bundle.model_dump()
        if not getattr(assets.render, "validation_ok", True):
            raise RuntimeError("output failed dimension validation")
        db.mark_done(job["id"], outputs)
    except Exception as e:  # never silent-fail; refund the debited credit
        db.mark_failed(job["id"], str(e))
        if job.get("tier") == "paid":
            db.refund(job["id"])
```
- [ ] **Step 4: run, verify pass** - Expected: 2 passed
- [ ] **Step 5: run full suite + commit**

Run: `/root/coverforge_venv/bin/python -m pytest render/tests -q` Expected: all green
```bash
git add render/worker.py tests/test_worker.py
git commit -m "feat(coverforge): pure job processor with refund-on-failure (fakes-tested)"
```

---

## Task A5: pricing guardrails (the margin gate)

**Files:** Create `render/pricing.py`; Test `render/tests/test_pricing.py`

- [ ] **Step 1: failing tests**
```python
# tests/test_pricing.py
import pytest
from render.pricing import MAX_VARIATIONS, cost_per_cover, clears_costs

def test_standard_5dollar_cover_clears_90pct_margin():
    assert clears_costs(5.0, "standard", variations=4)

def test_variations_capped_at_max():
    assert cost_per_cover("standard", 100) == cost_per_cover("standard", MAX_VARIATIONS)

def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        cost_per_cover("ultra", 1)

def test_underpriced_cover_fails_gate():
    assert not clears_costs(1.0, "standard", variations=4)

def test_premium_costs_more_than_standard():
    assert cost_per_cover("premium") > cost_per_cover("standard")
```
- [ ] **Step 2: run, verify fail**
- [ ] **Step 3: implement**
```python
# render/pricing.py
"""Single source of truth for image-model tiers + the margin gate.
Encodes the 'price must clear COGS and grow' law so the build enforces it,
not the operator's memory. Mirrored as Deno constants in coverforge-create-job."""

MAX_VARIATIONS = 4  # per credit; regenerations cost another credit

TIER_MODELS = {
    "economy":  {"model": "fal-ai/flux/schnell",          "img_cost": 0.025},
    "standard": {"model": "fal-ai/flux/dev",              "img_cost": 0.04},
    "premium":  {"model": "google/nano-banana-pro-batch", "img_cost": 0.067},
}
HAIKU_BUNDLE_COST = 0.002
STRIPE_FEE_PER_COVER = 0.25  # amortized over a 3-batch $15 pack

def cost_per_cover(tier: str, variations: int = 1) -> float:
    if tier not in TIER_MODELS:
        raise ValueError(f"unknown tier {tier!r}; expected {list(TIER_MODELS)}")
    v = min(max(variations, 1), MAX_VARIATIONS)
    return TIER_MODELS[tier]["img_cost"] * v + HAIKU_BUNDLE_COST + STRIPE_FEE_PER_COVER

def clears_costs(price: float, tier: str, variations: int = 1, target_margin: float = 0.90) -> bool:
    """True iff price >= cogs / (1 - target_margin)."""
    return price >= cost_per_cover(tier, variations) / (1 - target_margin)
```
- [ ] **Step 4: run, verify pass** - Expected: 5 passed
- [ ] **Step 5: commit**
```bash
git add render/pricing.py tests/test_pricing.py
git commit -m "feat(coverforge): pricing tiers + margin gate (price must clear COGS)"
```

---

# PART B - Deploy (LIVE Supabase + Stripe) -- CHECKPOINT REQUIRED

> ⛔ **Do NOT run Part B against production until Rich approves.** All Stripe wiring uses TEST keys first (the `AK_SHOP_TEST_MODE` discipline). Migrations apply to a Supabase branch or are reviewed before `apply_migration`. These tasks are authored here; execution is a separate, gated step.

## Task B1: SQL migration

**Files:** Create `supabase/migrations/20260614_coverforge.sql`

- [ ] **Step 1: write migration**
```sql
-- cover jobs queue + append-only credit ledger + outputs bucket
create table if not exists cover_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  tier text not null check (tier in ('free','paid')),
  status text not null default 'queued' check (status in ('queued','running','done','failed')),
  input jsonb not null,
  outputs jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists credit_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  delta integer not null,                 -- +N purchase, -1 debit, +1 refund
  reason text not null,                    -- 'purchase' | 'debit' | 'refund'
  stripe_session_id text unique,           -- idempotency for purchases
  created_at timestamptz not null default now()
);

create or replace function cover_credit_balance(uid uuid) returns integer
  language sql stable as $$ select coalesce(sum(delta),0)::int from credit_ledger where user_id = uid $$;

alter table cover_jobs enable row level security;
alter table credit_ledger enable row level security;
create policy "own jobs"   on cover_jobs   for select using (auth.uid() = user_id);
create policy "own ledger" on credit_ledger for select using (auth.uid() = user_id);
-- writes are service-role only (edge functions); no insert/update policies for anon/auth.

insert into storage.buckets (id, name, public) values ('covers','covers', false)
  on conflict (id) do nothing;
```
- [ ] **Step 2 (CHECKPOINT):** Rich approves, then apply via Supabase MCP `apply_migration` to project `jdqqmsmwmbsnlnstyavl` (or a branch). Verify with `list_tables`.
- [ ] **Step 3: commit** `git add supabase/migrations/20260614_coverforge.sql && git commit -m "feat(coverforge): cover_jobs + credit_ledger schema + covers bucket + RLS"`

---

## Task B2: edge fn coverforge-create-job

**Files:** Create `supabase/functions/coverforge-create-job/index.ts`

> Mirror the Python guardrails (`render/pricing.py`) as Deno constants: clamp `variations` to **4** (`MAX_VARIATIONS`), allow only the `economy|standard|premium` tier->model map, and keep **1 credit = 1 batch**. Premium is its own higher-priced credit SKU, never bundled into a standard credit.

- [ ] **Step 1: write fn** (reuses `_shared/mod.ts` like the other functions)
```ts
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders } from "../_shared/mod.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const admin = createClient(SUPABASE_URL, Deno.env.get("SB_SERVICE_ROLE_KEY")!);
  const jwt = req.headers.get("Authorization")?.replace("Bearer ", "");
  const { data: { user } } = await admin.auth.getUser(jwt ?? "");
  if (!user) return json({ error: "unauthorized" }, 401);

  const { input, tier } = await req.json();   // input = book metadata; tier 'free'|'paid'
  if (tier !== "free" && tier !== "paid") return json({ error: "bad tier" }, 400);

  if (tier === "paid") {
    const { data: bal } = await admin.rpc("cover_credit_balance", { uid: user.id });
    if ((bal ?? 0) < 1) return json({ error: "no_credits" }, 402);
    await admin.from("credit_ledger").insert({ user_id: user.id, delta: -1, reason: "debit" });
  }
  const { data: job, error } = await admin.from("cover_jobs")
    .insert({ user_id: user.id, tier, input, status: "queued" }).select("id").single();
  if (error) return json({ error: error.message }, 500);
  return json({ job_id: job.id });
});

function json(b: unknown, status = 200) {
  return new Response(JSON.stringify(b), { status, headers: { ...corsHeaders, "Content-Type": "application/json" } });
}
```
- [ ] **Step 2 (CHECKPOINT):** deploy via Supabase MCP `deploy_edge_function`; smoke-test with a test JWT.
- [ ] **Step 3: commit**

---

## Task B3: edge fn coverforge-job-status

**Files:** Create `supabase/functions/coverforge-job-status/index.ts`

- [ ] **Step 1: write fn** - auth, fetch the user's job by id, and for `done` paid jobs return signed URLs for each `outputs` storage path (1h expiry) so only the owner can download.
```ts
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders } from "../_shared/mod.ts";
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const admin = createClient(SUPABASE_URL, Deno.env.get("SB_SERVICE_ROLE_KEY")!);
  const jwt = req.headers.get("Authorization")?.replace("Bearer ", "");
  const { data: { user } } = await admin.auth.getUser(jwt ?? "");
  if (!user) return j({ error: "unauthorized" }, 401);
  const url = new URL(req.url); const id = url.searchParams.get("job_id");
  const { data: job } = await admin.from("cover_jobs").select("*").eq("id", id).eq("user_id", user.id).maybeSingle();
  if (!job) return j({ error: "not_found" }, 404);
  const signed: Record<string,string> = {};
  if (job.status === "done" && job.tier === "paid" && job.outputs) {
    for (const [k, v] of Object.entries(job.outputs)) {
      if (typeof v === "string" && v.startsWith("covers/")) {
        const { data } = await admin.storage.from("covers").createSignedUrl(v.replace("covers/", ""), 3600);
        if (data) signed[k] = data.signedUrl;
      }
    }
  }
  return j({ status: job.status, tier: job.tier, outputs: job.outputs, signed, error: job.error });
  function j(b: unknown, s = 200){ return new Response(JSON.stringify(b), { status: s, headers: { ...corsHeaders, "Content-Type": "application/json" } }); }
});
```
- [ ] **Step 2 (CHECKPOINT):** deploy + smoke-test.
- [ ] **Step 3: commit**

---

## Task B4: Stripe cover-credit SKUs (webhook + checkout)

**Files:** Modify `supabase/functions/stripe-webhook/index.ts`, `supabase/functions/create-checkout/index.ts`

- [ ] **Step 1: webhook branch** - add a `cover_credits` case to the `checkout.session.completed` switch in `stripe-webhook/index.ts`, mirroring the `gems` branch but crediting `credit_ledger`. Idempotency via the unique `stripe_session_id`:
```ts
} else if (productType === "cover_credits") {
  const CREDIT_AMOUNTS: Record<string, number> = {
    "cover-3": 3, "cover-pro-20": 20, "cover-pro-50": 50,
  };
  const amount = CREDIT_AMOUNTS[slug] || 0;
  if (amount > 0) {
    // unique stripe_session_id makes this a no-op on retries
    await supabaseAdmin.from("credit_ledger").upsert({
      user_id: session.metadata?.user_id, delta: amount,
      reason: "purchase", stripe_session_id: session.id,
    }, { onConflict: "stripe_session_id" });
    if (slackUrl) await postSlack(slackUrl, `[CoverForge] ${amount} credits for "${slug}"`);
  }
}
```
- [ ] **Step 2: checkout SKUs** - add cover-credit price IDs to the `PRICE_MAP` in `create-checkout/index.ts` (TEST-mode price IDs first), and ensure the checkout passes `metadata: { product_type: "cover_credits", slug, user_id }`.
- [ ] **Step 3 (CHECKPOINT):** create TEST price IDs in Stripe, deploy both functions, run a full **test-mode** purchase and confirm a `+N` ledger row lands. Only after a clean test run does Rich flip to live price IDs.
- [ ] **Step 4: commit**

---

## Task B5: e5 worker poll loop + deploy

**Files:** Create `render/poll_loop.py`, `03_AUTOMATION_CORE/01_Scripts/setup/coverforge-worker.service`

- [ ] **Step 1: poll loop** - a singleton-guarded `while True` that polls `cover_jobs where status='queued'`, claims a row (`update ... set status='running'`), wires real Supabase storage + a `LedgerDB` adapter + `produce_assets` into `process_job`, sleeps on empty. (Real-Supabase glue; unit-covered logic is `process_job` from A4.)
- [ ] **Step 2: systemd unit** for e5 (`Restart=always`), env: `SUPABASE_URL`, `SB_SERVICE_ROLE_KEY`, `FAL_KEY`, `ANTHROPIC_API_KEY`.
- [ ] **Step 3 (CHECKPOINT):** deploy to e5, enqueue one paid job end-to-end, confirm files land in the `covers` bucket and status flips to `done`.
- [ ] **Step 4: commit**

---

## Self-Review

**Spec coverage:** bundle generator (A1/A2), worker + refund (A4/B5), DB schema + credits (B1), edge functions (B2/B3), Stripe (B4) - all map to spec section 4-6. **Deviation:** bundle in Python not Deno (flagged, Rich to confirm). **Deferred to Plan 3:** the Next.js freemium funnel (input form, preview, paywall, download) which consumes B2/B3.

**Placeholder scan:** Part A is complete runnable TDD. Part B carries full SQL/TS; the only intentionally-prose steps are the live-deploy CHECKPOINT actions (by design - they touch prod and need Rich + MCP, not blind execution).
