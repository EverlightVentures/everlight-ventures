---
name: claude_finance_prompts
description: Three template-first prompting patterns for Claude in financial analysis (variance, deal modeling, trade decisions). Sourced from "One Month of Claude in Finance" transcript.
---

When to use:
- claude_advisor.py XLM trade decisions (ENTER/EXIT/HOLD).
- Penny / Cash variance vs budget / revenue driver decomposition / churn synthesis.
- Broker analytics deal modeling (expected value, CAC vs LTV).
- Any FP&A-style ask: structured numerical data + qualitative context -> commentary.

NOT for:
- Pure formula generation.
- Pure code (use feature-dev or claude-api skill).
- Decisions that touch live capital without a deterministic post-check (use Operator Truth Doctrine).

Three patterns (copy-pastable):

**Pattern 1 -- Template-first, not analysis-first:**
```
"Here is my variance template with columns
[Actual, Budget, Variance, Variance%, Driver, Commentary].
Populate ONLY the Driver and Commentary columns
for rows where abs(Variance%) > 5%.
Match the tone and structure of these 3 example rows
I have already filled in: [paste examples].
Do not restructure the template."
```

**Pattern 2 -- Explicit-field steering with exclude flag:**
```
"Analyze the [revenue|trade|deal] dataset.
Reference these fields ONLY:
[current_period, budget, prior_period, driver_tag, exclude_flag].
If exclude_flag = 'Y', skip that row entirely.
Tie qualitative context from tab/section
[churn_reasons|trade_log|ops_notes]
to each row by [customer_id|trade_id|deal_id]."
```

**Pattern 3 -- Three-column delta framing:**
```
"For each row I have current_period, budget, prior_period
as separate columns. Generate commentary explaining
(a) variance vs budget AND (b) variance vs prior, in that order.
Flag any row where the two variances disagree in sign --
those are the interesting ones."
```

Caveats (do NOT):
- Do not ask Claude to "review the whole worksheet for errors" -- it returns false-clean. Ask for specific check types one at a time.
- Do not let Claude generate the template from scratch; build the template, then have Claude populate.
- Do not trust 100%; transcript confirms "80% of the way there" -- always validate with a deterministic post-check (PnL sanity, position-size cap) before any ENTER on claude_advisor.
- Excel-embedded Claude has no cross-session memory; pass full context every prompt.

Hive-specific application:
- claude_advisor.py: refactor prompts to template-first. Pre-fill ENTER/EXIT/HOLD scaffold with [signal, threshold, current, decision_field, rationale_field]. Claude only populates decision + rationale.
- Add `exclude_flag` column to wholesale lead and trade-log schemas so agents can mark rows as "do not analyze" without prompt-engineering around them.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/one_month_of_claude_in_finance.txt
Owner: Penny + Cash + Rex Thornton (XLM).
