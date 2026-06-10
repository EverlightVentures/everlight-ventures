# research_eval_harness

Shared eval harness for the 3-paper Anthropic bridge portfolio.
Built once, reused three times. Full architecture in `SPEC.md`.

## Quick start (future Rich)

```bash
# Dry-run -- show what would happen + cost estimate, no API calls
python -m research_eval_harness run --paper 1 --condition fail_closed_gate \
    --seeds 5 --dry-run

# Real run -- writes to runs/paper1/fail_closed_gate/<seed>/
python -m research_eval_harness run --paper 1 --condition fail_closed_gate \
    --seeds 5 --output runs/paper1/

# Aggregate across conditions for a paper, emit summary.md + CIs
python -m research_eval_harness aggregate --paper 1 --runs runs/paper1/

# Re-verify a published result from its manifest
python -m research_eval_harness verify --manifest runs/paper1/fail_closed_gate/seed0/manifest.json
```

## Status (2026-05-17)

- SPEC complete. Stubs in place. NO live model calls yet.
- Pre-implementation review pending Rich on the 8 open questions in `SPEC.md` §9.
- Estimated 1 dev-day from green light to a paper #1 smoke test.

## File tree

```
research_eval_harness/
  SPEC.md                  # architecture doc
  README.md                # this file
  __init__.py              # version + capability registry
  cli.py                   # one CLI entry point
  aggregator.py            # bootstrap CIs + paired stats + manifest hashing
  manifest.py              # reproducibility manifest
  budget.py                # pre-flight cost gate
  budget.yaml              # cost caps config
  probes/                  # pluggable probe families
    base.py                # ProbeFamily ABC + ProbeExample schema
    jailbreak.py           # paper #1 -- DAN-style, role-play, prompt-injection
    paraphrase.py          # paper #1 mutation generator
    social_engineering.py  # paper #3 -- 5-register leak attempts
    held_out.py            # paper #2 -- TruthfulQA / MATH-adversarial
  runners/                 # pluggable conditions
    base.py                # Condition ABC + RunnerOutput schema
    fail_closed_gate.py    # paper #1 treatment
    soft_prompt_dnc.py     # paper #1 baseline
    raw_api.py             # paper #1 control
    vanilla_persona.py     # paper #3 baseline
    register_classifier.py # paper #3 treatment
    single_pass.py         # paper #2 baseline
    roundtable.py          # paper #2 treatment
  metrics/                 # pluggable scorers
    base.py                # Metric ABC + MetricResult schema
    bypass_rate.py
    false_positive.py
    accuracy_delta.py
    position_revision.py
    leak_rate.py
    voice_consistency.py
    recruiter_experience.py
    latency.py
    cost.py
```

## Integration

- `hive_logger.start()` opens a session per run; manifest + summary register as artifacts.
- `eradication_gate.assert_safe()` is wrapped, not reimplemented, by `runners/fail_closed_gate.py`.
- `recipient_register.classify()` is wrapped by `runners/register_classifier.py`.
- `moltbook_confidentiality_gate.assert_safe()` is wrapped by `runners/register_classifier.py`.
- `roundtable.roundtable(mock=False)` is called by `runners/roundtable.py`.
- Branded publishing (`publish_gdoc` + `branded_slack`) is used by `aggregator.py` for the per-paper summary report.

## Reproducibility

Every run emits `manifest.json` containing git SHA, model version (from API
response, not request), dataset hash, prompt hashes, seeds, Python + key
package versions, harness version. See `SPEC.md` §6.

## Budget guardrails

`budget.yaml` caps spend per-run / per-paper / per-day. `cli.py` pre-flight
estimates cost; abort if over cap unless `--force-budget`. Default caps in
`SPEC.md` §7.
