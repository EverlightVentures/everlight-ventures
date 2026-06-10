# AI-Safety Paper Portfolio — Compute & API Budget

**Status:** v0.1 — pre-experiment
**Date:** 2026-05-17
**Owner:** Richard Gee
**Scope:** 3-paper bridge portfolio to Anthropic Fellows / MATS / alt-vector AI-safety lanes

---

## Headline

| Line | Range | Mid-point |
|------|-------|-----------|
| Paper #1 — Constitutional Runtime Gates | $500 – $2,000 | $1,200 |
| Paper #2 — Roundtable Protocol | $1,000 – $2,500 | $1,750 |
| Paper #3 — Voice-Register Confidentiality | $1,000 – $2,000 | $1,500 |
| External red-team budget (optional, §6) | $0 – $1,000 | $500 |
| Buffer for re-runs / scope creep | $500 – $1,500 | $1,000 |
| **Portfolio total** | **$3,000 – $9,000** | **$5,950** |

Mid-point assumption: ship all three papers + modest red-team budget. Lower bound: ship Paper #1 only, defer #2 and #3 if Deal 1 cash flow tightens. Upper bound: scope creep on Paper #2 (Roundtable runs explode if we expand persona count or N).

**Funding gate:** all three papers ⏸ POST-DEAL-1 per macro/micro doctrine. No portfolio API spend until Deal 1 closes ($5–$10k finder fee).

---

## Paper #1 — Constitutional Runtime Gates: detailed estimate

**Configuration:** N=500 bypass attempts × 4 personas × 4 conditions (baseline A / baseline B / treatment / stacked) × 3 seeds = **24,000 model calls**

**Cost model (Claude 4.5 Sonnet, current API rates):**
- Mean tokens per call: ~600 input + ~200 output
- Per-call cost: ~$0.003 input + $0.003 output = ~$0.006
- 24,000 calls × $0.006 = **~$144 base**

**Multipliers:**
- Self-reflection condition (baseline B) doubles call count on that condition → +$36
- Re-runs for failed seeds / debugging: 2× buffer → +$180
- Manifest verification + final replication pass: +$50
- Optional model-comparison column (Sonnet vs. Opus): +$300

**Subtotal: $250 – $700**

**Why the budget range is $500–$2,000 (above the math):** the gap is for **probe corpus construction**. We need 500 high-quality adversarial probes (direct injection / paraphrase / social engineering / multi-turn drift). Pure researcher-handwriting is too slow. Realistic flow: use Claude or GPT-5 to generate candidate probes against a probe spec, hand-curate the top N, iterate. That generation step adds ~$200–$600 in API spend depending on how many cycles of generate-curate-discard we run.

**Sensitivity:** if we ship at N=200 instead of N=500 (smaller per-cell sample, same number of cells), total drops to $250–$800.

---

## Paper #2 — Roundtable Protocol: detailed estimate

**Configuration:** N=50 questions × 3 conditions (single-pass / vanilla CoT / Roundtable) × 5 seeds = **750 base experimental runs**

**The Roundtable expansion factor:** each Roundtable run is itself 7 persona calls × 5 phases = ~35 API calls per "run" instance. So:
- Single-pass condition: 50 × 5 = 250 calls
- Vanilla CoT: 50 × 5 = 250 calls
- Roundtable: 50 × 5 × 35 = **8,750 calls**
- **Total: ~9,250 calls**

**Cost model (Claude 4.5 Sonnet):**
- Roundtable calls are longer (~1,500 input + ~400 output) → ~$0.011 per call
- 8,750 × $0.011 = **~$96 (Roundtable)**
- 500 × $0.006 = $3 (single-pass + CoT)
- **Base subtotal: ~$100**

**Multipliers and add-ons:**
- Held-out eval dataset license / API access (TruthfulQA is free, MATH-adversarial may need HF hub egress) — $0 expected, $50 buffer
- LLM-as-judge for position-revision scoring (~50 × 5 × 5 = 1,250 judge calls): ~$10
- GPT-5 judge for same-family bias control (per architect's question #2): +$50–$100
- Pre-registration analysis dry runs on N=5 to confirm pipeline before full sweep: $20
- Re-run buffer: 2× → +$200
- **Realistic landing: $400 – $1,000**

**Why the headline range is $1,000–$2,500:** the architect raised a real cost concern (his Q#5): at the full N=50 × 5 seeds × 7-persona Roundtable, we hit ~25k+ Claude calls if we expand judge model usage. **Decision pending Rich's review of question #5 in `research_eval_harness/SPEC.md`.** Conservative: run Paper #2 at **N=20** to stay under $750 and write that limitation into §8.

---

## Paper #3 — Voice-Register Confidentiality: detailed estimate

**Configuration:** N=200 adversarial leak attempts × 3 conditions (vanilla persona / register classifier alone / register + confidentiality gate) × 3 seeds × 2 personas (Lucrex-Moltbook and one held-out) = **3,600 calls**

**Cost model:**
- Persona-on-public-network simulation requires multi-turn conversations (~3–5 turns per probe)
- Effective call count: 3,600 × 4 (turns) = ~14,400 calls
- Per-call cost: ~$0.008 (longer context)
- **Subtotal: ~$115**

**Add-ons:**
- LLM-as-judge for leak detection (binary: did any forbidden state leak? — ~14,400 judge calls): $115
- LLM-as-judge for voice consistency (Likert 1–5 per response, calibrated): $115
- Recruiter-experience score: **decision pending** (architect Q#3) — synthetic LLM-judge ($50) vs. real recruiter panel (3–5 humans × $50 = $150–$250)
- Re-run buffer: +$150
- **Realistic landing: $600 – $1,200**

**Why the range is $1,000–$2,000:** recruiter-panel option pushes us up; held-out persona generation (we need at least one persona we did NOT train the classifier on, to demonstrate generalization) adds construction cost ~$150.

---

## Funding sources (priority-ordered)

1. **Everlight operating budget post-Deal-1.** Deal 1 finder fee target: $5,000–$10,000. Even at the low end, the full portfolio mid-point ($5,950) is covered with margin if we phase across 14 weeks.

2. **Anthropic developer API credits.** Standard new-account credits ($5–$25) are nuisance-level but may cover Paper #1 generation phase. Worth claiming if Rich opens a fresh API account for the research workstream (separate billing from Hive Mind production keys).

3. **OpenRouter free-tier routing for low-stakes probe generation.** Probe-corpus construction is judge-on-judge work; Llama / Mistral / Qwen via OpenRouter free tier can carry it at zero marginal cost. Production runs (Paper #1 main experiment) still on Anthropic API — per the existing `openrouter_fallback` skill which forbids OpenRouter for "compliance" and "final branded renders" but allows it for low-stakes generative work.

4. **AceMagician / Oracle local inference for open-weight baseline comparisons.** Mentioned in §8 of Paper #1 as future-work — if we ever want a fine-tuned-attacker baseline, we'd run it on AceMagician's local GPU rather than burning API budget on adversarial fine-tunes. Not in the headline budget; flagged for completeness.

5. **MATS / Constellation compute grants.** If Rich applies to MATS Summer 2026 Megastream (per Nova's mentor memo, the structurally cleanest channel to Fellows), accepted mentees get compute budget directly. **This is the highest-leverage funding source** if it materializes — would offset Papers #2 and #3 entirely.

---

## Spend cadence (post-Deal-1)

```
Week  0:  Deal 1 closes. Budget gate opens.
Week  1:  $50  — probe-corpus generation (Paper #1)
Week  2:  $200 — Paper #1 main experiment, baseline conditions
Week  3:  $200 — Paper #1 treatment + stacked, replication, manifest
Week  4:  $50  — Paper #1 buffer / re-runs
Week  5:  $100 — Paper #2 probe-corpus + dry-run (N=5 sanity check)
Week  6:  $400 — Paper #2 main experiment (N=20–30 depending on Q#5)
Week  7:  $200 — Paper #2 re-runs + judge passes
Week  8:  $100 — Paper #2 manifest + replication
Week  9:  $200 — Paper #3 probe-corpus + leak harness
Week 10:  $400 — Paper #3 main experiment
Week 11:  $300 — Paper #3 judge passes (voice consistency + leak detection)
Week 12:  $200 — Paper #3 re-runs + buffer
Week 13:  $500 — optional external red-team (per Paper #1 §8 hook)
Week 14:  $500 — portfolio-wide buffer for late-stage re-runs

Total scheduled: ~$3,400 (under mid-point, headroom for surprises)
```

---

## Cost-control invariants (per eval-harness SPEC.md §6)

1. **Pre-flight estimate before every run.** `python -m research_eval_harness run --dry-run` outputs estimated spend in USD. No run executes without a printed estimate the operator confirms.
2. **Per-run hard cap: $25.** `budget.yaml` enforces. `--force-budget` flag exists but cannot override `hard_abort_usd_per_run`.
3. **Per-paper soft cap: $2,000.** Warning at 75%, abort at 100% unless explicit override committed to repo.
4. **Per-day cap: $500.** Prevents runaway experiments.
5. **Budget alerts to Slack `#research-spend`** when any cap is crossed. Per the branded-pipeline doctrine.
6. **Audit log of all API spend** writes to `_logs/research_api_spend.jsonl`, reconciled monthly against Anthropic billing.

---

## Open questions for Rich

1. **Run Paper #2 at N=20 or N=50?** Architect's Q#5. N=20 saves ~$700 but weakens the statistical claim. N=50 is publishable-tier; N=20 is workshop-tier. **Recommend: N=20 for v0, scale to N=50 post-feedback.**
2. **Recruiter-experience metric: synthetic vs. real panel?** Architect's Q#3. Real panel is +$150–$250 and significantly more defensible. **Recommend: synthetic for v0, real panel for camera-ready if accepted.**
3. **Anthropic vs. mixed-model judge for Papers #2 and #3?** Architect's Q#2. Same-family bias is real but +50–100% cost. **Recommend: Anthropic-only for v0, add GPT-5 spot-check on 10% sample for bias disclosure.**
4. **External red-team budget: ship or skip?** Optional $500–$1,000. Strengthens Paper #1 §8 substantially. **Recommend: defer until v0 of Paper #1 is drafted and we know the bypass-rate number — if the gate looks bulletproof, an external probe is high-leverage; if it's borderline, save the money.**
5. **MATS application timing.** Per Nova's memo, MATS Summer 2026 Megastream is the cleanest channel into Fellows. Applying to MATS first (with a Paper #1 draft in hand) is structurally superior to cold-Fellows-applying. **Decision: when does Rich want to commit the MATS application — alongside Paper #1 v0, or after Paper #2?**

---

## Bottom line

**Mid-point portfolio cost: ~$6,000.** Well within reach of a single $5–10k wholesale finder fee. Cadenced spend across 14 weeks rather than front-loaded. Cost-control invariants enforced at the harness layer so no single run can blow the budget. Open questions are scope decisions, not budget unknowns — the numbers are bounded.

**Single biggest cost lever:** Paper #2 N decision (N=20 vs. N=50 changes total by ~$700). Second biggest: recruiter-panel decision on Paper #3 (~$200). Third biggest: external red-team yes/no on Paper #1 (~$500).

All other variables are noise at this scale.
