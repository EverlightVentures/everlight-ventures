# Daily Prompts Library

Source: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/06_Knowledge_Management/101_ways_to_use_ai_daily.txt`

15 prompts ported from the "101 Ways" transcript, selected for Everlight workflows. Every Hive agent can invoke any of these via a simple reference in their system prompt ("Use the `reverse_outline` prompt from daily_prompts_library").

---

## Content + writing

### 1. reverse_outline
> Outline this document in reverse: bottom-up. For each section, extract the single claim it makes and list the evidence that supports it. Then reorder to put the strongest claims first.

### 2. headline_variants
> Generate 10 headlines for this piece. 3 curiosity-driven, 3 benefit-driven, 3 specificity-driven, 1 contrarian. Rank them by likely click-through.

### 3. reader_level_rewrite
> Rewrite this paragraph three ways: 8th grade, 12th grade, and expert. Note which facts needed adjustment (never simplification that distorts truth).

### 4. counter_argument
> State the strongest argument against the claim in this text. Do not hedge. Assume the counter-arguer is smarter than the original author.

## Ops + decision support

### 5. decision_matrix
> Present these N options as a decision matrix with criteria. Score each option 1-5 on cost, speed, reversibility, alignment with stated goals. Sum and rank.

### 6. five_whys
> Given this problem statement, ask Five Whys. Do not give me the answer; give me the 5 questions and the shortest plausible answer to each.

### 7. stakeholder_lens
> For each stakeholder in this situation, describe what they want in one sentence, what they fear in one sentence, and what would make them say yes in one sentence.

### 8. timeline_budget
> Propose a 7-day timeline to ship X. Day-by-day. At the end list assumptions and budget risk.

## Research + synthesis

### 9. extract_facts
> From this source, list every assertable fact. Tag each: VERIFIED / CITED_BUT_UNVERIFIED / OPINION.

### 10. find_gaps
> What is NOT in this document that a serious reader would ask? List 5 gaps plus the one that matters most.

### 11. combine_sources
> I have 3 excerpts from different sources. Synthesize one coherent summary. Where they contradict, say so explicitly and identify which source has stronger evidence.

## Code + engineering

### 12. code_review_targeted
> Review this code for: race conditions, security holes, resource leaks, and divergence from the stated design. Rank findings by blast radius.

### 13. test_plan
> Produce a test plan for this feature with 6 sections: happy path, unhappy paths, concurrency, edge cases, ops concerns (monitoring), rollback.

## Personal + meta

### 14. weekly_review
> Given this week's logs + my stated goals, write a one-paragraph review. What moved, what stuck, what needs next week's attention.

### 15. second_opinion
> Steelman the decision I am about to make. Then steelman the opposite. Name the question that settles it.

---

## Using these

- Every prompt is a standalone skill. Invoke by name in your agent's system prompt.
- These are OUR portable prompt library. They travel if we swap out the model.
- Extend by appending to this file. Name each new prompt in snake_case. Keep each under ~80 words.
