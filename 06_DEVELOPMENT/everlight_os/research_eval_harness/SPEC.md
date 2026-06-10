# Research Eval Harness -- Shared Spec (v0.1)

**Owner:** Amara Osei (Backend Architect, Iron Stack TL)
**For:** Lucrex / Rich -- Anthropic Fellows bridge portfolio (3 papers)
**Status:** SPEC + STUBS. No live model calls yet. Pre-implementation review.
**Last updated:** 2026-05-17

---

## 1. Why this exists

Three papers share the same shape: probe a system under adversarial conditions,
measure how often the system fails, compare against a baseline, report bootstrap
CIs and statistical significance. If we build the harness once, paper #2 and #3
become weekend deltas on top of paper #1 instead of greenfield rebuilds.

The contract: every paper produces a `runs/paperN/<condition>/<seed>/` tree
whose files are interchangeable. Reviewers replicate any single result with one
command.

## 2. Architecture (10,000-user thought experiment doesn't apply -- but reproducibility does)

```
                         research_eval_harness/
                                  |
   +------------------------------+------------------------------+
   |                              |                              |
 probes/                       runners/                       metrics/
 (load N adversarial          (apply a CONDITION to           (score results,
  prompts per family)          each prompt, get a              emit shared schema)
                               (prompt, response, flags)
                               record)
                                  |
                                  v
                            aggregator.py
                (bootstrap CIs, paired tests, manifest hash)
                                  |
                                  v
                                cli.py
              (one entry point: --paper N --condition X --seeds K)
                                  |
                                  v
                  runs/paperN/<condition>/<seed>/
                       events.jsonl
                       metrics.json
                       manifest.json
                       summary.md
```

## 3. Module responsibilities

| Module | Responsibility | Out-of-scope |
| --- | --- | --- |
| `probes/base.py` | `ProbeFamily` ABC + `ProbeExample` pydantic schema. | Generating the actual probes. |
| `probes/jailbreak.py` | DAN-style, role-play, prompt-injection N=500 for paper #1. | Paraphrasing existing probes. |
| `probes/paraphrase.py` | Mutation generator for robustness (rephrase + back-translate). | Hand-curated content. |
| `probes/social_engineering.py` | 5-register adversarial leak attempts for paper #3 (N=200). | Persona drift testing -- separate. |
| `probes/held_out.py` | TruthfulQA / MATH-adversarial loader for paper #2 (N=50). | Local synthetic problems. |
| `runners/base.py` | `Condition` ABC -- `apply(prompt) -> RunnerOutput`. | Probe construction. |
| `runners/fail_closed_gate.py` | Paper #1 treatment: route through eradication_gate / confidentiality_gate. | Soft-prompt baselines. |
| `runners/soft_prompt_dnc.py` | Paper #1 baseline: system prompt asks model to refuse DNC contacts. | Gate logic. |
| `runners/raw_api.py` | No-defense baseline (raw Claude / GPT-4o call). | Anything wrapped. |
| `runners/vanilla_persona.py` | Paper #3 baseline: single-prompt persona, no register classifier. | Roundtable orchestration. |
| `runners/register_classifier.py` | Paper #3 treatment: route through `recipient_register.classify()` + `moltbook_confidentiality_gate`. | Persona definitions. |
| `runners/single_pass.py` | Paper #2 baseline: one Claude completion, no debate. | Multi-agent orchestration. |
| `runners/roundtable.py` | Paper #2 treatment: calls `hive_mind/roundtable/roundtable()` with mock=False. | Persona authoring. |
| `metrics/base.py` | `Metric` ABC + `MetricResult` schema. | Bootstrap math. |
| `metrics/bypass_rate.py` | Paper #1: fraction of probes that elicited the forbidden behavior. | FP rate. |
| `metrics/false_positive.py` | Paper #1+#3: legitimate prompts blocked. | Bypass rate. |
| `metrics/accuracy_delta.py` | Paper #2: held-out accuracy vs. baseline, paired by question. | Position revision. |
| `metrics/position_revision.py` | Paper #2: fraction of personas whose answer changed between Open and Cross-fire. | Disagreement intensity. |
| `metrics/leak_rate.py` | Paper #3: fraction of responses that emit forbidden substrings (mirrors confidentiality_gate). | Voice consistency. |
| `metrics/voice_consistency.py` | Paper #3: cosine sim of persona embeddings across registers (proxy: 3rd-party LLM judge). | Recruiter scores. |
| `metrics/recruiter_experience.py` | Paper #3: blinded LLM-judge "would you hire" + variance. | Real human review. |
| `metrics/latency.py` | Wall-clock per run. | API cost. |
| `metrics/cost.py` | Input + output token spend per run (from API response). | Bootstrap CIs. |
| `aggregator.py` | Bootstrap 95% CIs, paired t-test / McNemar's, manifest hashing, summary.md emission. | Per-paper logic. |
| `cli.py` | `python -m research_eval_harness run --paper N --condition X --seeds K`. | Anything else. |
| `manifest.py` | Computes manifest hash (git SHA + model + dataset hash + prompt hash + python deps). | Persistence. |
| `budget.py` | Loads `budget.yaml`, pre-flight token estimate, abort gate. | Cost collection. |

## 4. Data flow per paper

### Paper #1 -- Constitutional Runtime Gates

```
probes/jailbreak.py (N=500)
  -> runners/fail_closed_gate.py  (treatment)
  -> runners/soft_prompt_dnc.py   (baseline)
  -> runners/raw_api.py           (no-defense control)
  -> metrics/{bypass_rate, false_positive, latency, cost}
  -> aggregator (paired McNemar on per-probe block outcomes)
  -> runs/paper1/{fail_closed,soft_prompt,raw}/<seed>/
```

Key invariant: every probe gets the SAME prompt sent to all 3 conditions in the
same seed. McNemar's test requires per-probe pairing.

### Paper #2 -- Roundtable Protocol

```
probes/held_out.py (TruthfulQA + MATH-adversarial, N=50)
  -> runners/single_pass.py  (baseline: 1 Claude completion)
  -> runners/roundtable.py   (treatment: Roundtable engine, mock=False)
  -> metrics/{accuracy_delta, position_revision, latency, cost}
  -> aggregator (paired t-test on per-question accuracy)
  -> runs/paper2/{single_pass,roundtable}/<seed>/
```

Position-revision is a roundtable-only metric -- it's null for single_pass.
The aggregator must skip null metrics, not error out.

### Paper #3 -- Voice-Register Confidentiality

```
probes/social_engineering.py (N=200, 5 categories x 40)
  -> runners/vanilla_persona.py        (baseline: GPT-4o persona only)
  -> runners/register_classifier.py    (treatment: recipient_register + moltbook gate)
  -> metrics/{leak_rate, voice_consistency, recruiter_experience, latency, cost}
  -> aggregator (paired McNemar on leak, paired t on judge scores)
  -> runs/paper3/{vanilla,classifier}/<seed>/
```

Voice consistency uses an LLM-judge -- track the judge's model+version in the
manifest because if it drifts the comparison breaks.

## 5. Extension pattern (paper #4 hypothetical)

Adding a 4th paper requires:

1. New `probes/<family>.py` subclass of `ProbeFamily`.
2. New `runners/<condition>.py` (often zero, since baselines reuse).
3. Optional `metrics/<new>.py` if the paper measures something novel.
4. CLI auto-discovers via entry point registration in `__init__.py`.
5. Zero changes to aggregator or manifest -- they're generic.

That's the property we're paying upfront for.

## 6. Reproducibility surface

Every run writes `manifest.json` with:

- `git_sha` (HEAD of the workspace at run start)
- `model_versions` (Anthropic `model` field returned by the API, not the request string)
- `dataset_hash` (sha256 of the probe set, including index order)
- `seeds` (the seed values used)
- `prompt_template_hashes` (sha256 of each prompt template loaded)
- `python_version` + key package versions (`anthropic`, `pydantic`, `numpy`, `scipy`)
- `harness_version` (set in `__init__.py`)
- `start_time_utc`, `end_time_utc`, `duration_seconds`
- `hive_session_id` (from hive_logger)
- `cost_actual_usd` (post-flight, from token counts)

This is the "Subliminal Learning"-style bar. Anyone with the manifest can
re-run and get the same numbers within sampling noise.

## 7. Cost-control invariants

1. `budget.yaml` defines `max_usd_per_run`, `max_usd_per_paper`, `daily_cap_usd`.
2. CLI runs `budget.estimate(probes, conditions, seeds)` BEFORE any API call.
3. If estimate > cap, CLI aborts with the deficit printed and a `--force-budget`
   override prompt. No silent overspend.
4. Every API response's `usage` block writes to the per-run `cost.jsonl`.
5. `aggregator.py` totals actual cost, compares to estimate, and warns if drift
   > 25%.
6. `--dry-run` flag pretty-prints the plan + estimate and exits without API
   calls. This is the default mode for showing Rich what a run would cost.

Default budget caps (initial values, tunable):

```yaml
max_usd_per_run: 5.00
max_usd_per_paper: 50.00
daily_cap_usd: 100.00
hard_abort_usd_per_run: 25.00   # safety net even with --force-budget
```

## 8. Integration with hive_logger

```python
import hive_logger
run = hive_logger.start(
    agent="research_eval_harness",
    task=f"paper{paper}_{condition}_seed{seed}",
    inputs={"paper": paper, "condition": condition, "seed": seed},
    tags=["#research/eval", f"#paper/{paper}"],
)
# ... do the work, emit events ...
run.artifact("manifest", path=str(manifest_path))
run.artifact("summary", path=str(summary_path))
run.finish(status="done", summary=f"{n_probes} probes, bypass={x:.3f}")
```

The HiveArtifact registration is what lets `:8504` later show eval runs in the
same dashboard view as wholesale + content runs. Single pane of glass.

## 9. Open questions for Rich (before implementation)

1. **Held-out dataset access.** TruthfulQA is HuggingFace + permissive. MATH
   adversarial -- which split? "MATH" by Hendrycks et al. has a test set we
   should freeze. Confirm: HuggingFace OK, or do you want a local mirror in
   `08_BACKUPS/research_datasets/`?
2. **LLM judge for paper #3 voice consistency.** Default plan: use Claude
   Sonnet 4 as judge with a rubric prompt. Acceptable, or do you want a
   separate vendor (e.g., GPT-4o) as judge to avoid same-family bias? Cost
   delta is ~2x.
3. **Recruiter-experience score.** Paper #3 mentions "recruiter experience
   scores" -- is that LLM-judge synthetic or do you want a tiny human panel
   (3-5 real recruiters, paid $50 each)? Big difference in defensibility.
4. **Paper #1 false-positive corpus.** I need 200-500 LEGITIMATE outbound
   prompts (real-looking wholesale outreach to non-DNC sellers) to measure
   FP rate. Sourcing options: (a) sample from `_logs/branded_mailer_audit.jsonl`
   redacted, (b) synthesize with Claude. (a) is more defensible; (b) is faster.
5. **Roundtable cost.** A 5-phase roundtable with 7 participants is ~50-80
   API calls. N=50 questions x 2 conditions x 5 seeds = if everything is
   live, ~25,000+ Claude calls. Budget OK or do we run paper #2 at N=20 and
   note "scaling to N=50 deferred pending budget"?
6. **Statistical pre-registration.** Anthropic-grade research pre-registers
   the analysis plan before seeing the data. Want me to write a
   `PREREGISTRATION.md` per paper before any run? Adds rigor, costs a day.
7. **Eradication_gate as a runner.** Today `eradication_gate.assert_safe()`
   raises rather than returns. The runner needs to catch the exception and
   record it as a "blocked" outcome -- I'll wrap it in a thin adapter. OK?
8. **Where do raw probe sets live?** Proposal:
   `06_DEVELOPMENT/everlight_os/research_eval_harness/datasets/<family>.jsonl`,
   committed (small) or downloaded on first run (large). Confirm.

## 10. What this spec deliberately does NOT do

- Define the actual probe contents (deferred to dataset construction phase).
- Implement the runners (stubs only; real work is paper-by-paper).
- Choose a specific bootstrap library (will be `scipy.stats.bootstrap` unless
  Rich prefers `arviz` for Bayesian framing).
- Tackle multi-judge consensus for paper #3 (single-judge first, multi-judge
  is a v2 thing).
- Replicate `eradication_gate`'s hardcoded list -- the runner USES the gate as
  ground truth, never reimplements its logic.

---

**Next action after Rich's review:** implement `metrics/bypass_rate.py` +
`runners/fail_closed_gate.py` + `aggregator.py` paired McNemar, end-to-end
on a 10-probe smoke dataset. Estimated 1 dev-day from green light to a
running paper #1 smoke test.
