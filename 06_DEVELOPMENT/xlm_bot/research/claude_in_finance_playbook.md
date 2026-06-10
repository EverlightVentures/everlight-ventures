# Claude in Finance - Prompting Playbook for claude_advisor.py

**Owner**: Rex Thornton + Penny Sharpe
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/one_month_of_claude_in_finance.txt`
**Date**: 2026-04-21

---

## What the transcript teaches

The creator ran Claude as a financial assistant for 30 days. Three prompting patterns produced the highest-quality outputs:

### Pattern A: "Frame-then-ask"
State the decision frame and constraints BEFORE the question. Example:
> "I am long XLM perps, 2x leverage, stop at -$30. Funding flips positive in 4 hours. Should I reduce size before the funding window?"

Works because: Claude commits to the frame instead of inventing one.

### Pattern B: "Force a ranking"
Ask for ranked options with rationale, not free-form advice.
> "Rank these 3 actions by expected value next 24h: hold, reduce-half, close. Give expected value in USD for each."

Works because: Claude cannot hedge; produces comparable outputs.

### Pattern C: "Show your working"
Require explicit step-by-step reasoning before the final call.
> "Walk through the math: current price, distance to stop, implied R:R, then decide. Do not skip to the conclusion."

Works because: Errors surface in the trace, not buried in confident prose.

## Everlight's current claude_advisor.py

Located at `06_DEVELOPMENT/xlm_bot/claude_advisor.py`. Uses Opus 4.7 with a system prompt that asks for ENTER/EXIT/HOLD/FLAT decisions with structured JSON output.

Comparison:
- We use Pattern B (force a ranking) partially: ENTER/EXIT/HOLD/FLAT is a constrained enum.
- We use Pattern C partially: our prompt asks for "reasoning" field but does not force step-by-step math.
- We do not use Pattern A consistently: frames are rebuilt per call from market state, not from stated constraints.

## Recommended prompt amendments (TEST, do not deploy blind)

Add to the system prompt:

```
When deciding ENTER / EXIT / HOLD / FLAT:
1. Restate current position size, leverage, entry price, distance-to-stop, and funding direction.
2. Compute implied risk in USD and implied reward in USD at the nearest resistance.
3. Only after both steps above, commit to the decision.
4. In the `reasoning` field, include the math from steps 1 and 2 verbatim.
```

## Test protocol

1. Fork claude_advisor.py to claude_advisor_v2.py with the amendment.
2. Run both in parallel for 5 trading days (shadow mode - do not place trades from v2).
3. Compare: decision alignment rate, retrospective profitability, Penny's manual grade on reasoning quality.
4. If v2 wins on 3 of 5 days, promote. Otherwise, keep current prompts.

## Cost note

Pattern C roughly doubles output tokens per call (math + decision, not just decision). At current call volume (~200 per day), that adds ~$0.15/day in Opus costs. Worth it if decision quality moves measurably.

## Decision gate

Rex runs the A/B test. Penny grades. Lucrex approves the merge only if both say yes. No auto-deploy.
