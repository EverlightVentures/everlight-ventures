# Day 3 -- Organic Persona Post Drafts (Nova OR Bull)

On Day 3 at 9:00 AM PT, ONE persona posts an organic tweet from @Lucrex
quote-tweeted as their own voice (or from their own moltbook account
directly if engagement on Day 1 justified the platform-level voice test).

This is the first NON-verification post from a Hive persona. Pure brand-
voice test on the network. No code, no announcement, just an opinion.

Decision tree:

- If markets / macro got the most Day-1 engagement -> **Bull Archer posts**
- If tech / AI got the most Day-1 engagement -> **Nova Ling posts**
- If something else won -> we redraft this file for the winning beat

---

## Skeleton A -- BULL ARCHER organic post

Voice anchors (drawn from his .claude/agents/bull_archer.md dossier):
  - FOMC nerd, rates-curve obsessive
  - "Treats every thesis as a hypothesis with a falsification condition"
  - Structural inflation > cyclical inflation right now
  - Falsifiable claims, not vibes

Structure (3-beat: observation / interpretation / falsification):

```text
[OBSERVATION -- what happened in the data today]
TODO_BULL_OBSERVATION
    e.g.  "10Y just printed [X]bps over [Y]bps -- third time this month."
    e.g.  "Cleveland Fed nowcast moved [direction] [amount] overnight."
    e.g.  "[Specific data release] came in [direction] of consensus."
    1-2 lines. NO $ amounts attached to deals/positions; macro $ refs are fine.

[INTERPRETATION -- what Bull thinks it means]
TODO_BULL_INTERPRETATION
    The hot take. 2-3 lines.
    Stay in the structural-inflation thesis lane unless the data legitimately
    contradicts it (in which case acknowledge the contradiction first).

[FALSIFICATION -- what would prove him wrong]
TODO_BULL_FALSIFICATION
    1 line. This is the signature move -- every Bull thesis ends with the
    falsification condition.
    e.g.  "I'm wrong if next month's print walks this back under [threshold]."
    e.g.  "Watching [specific indicator] -- if it breaks, the thesis breaks."
```

Length budget: under 280 chars total. Use line breaks for emphasis.

Gate considerations: avoid naming specific deals/positions. Macro market
commentary is allowed. Specific $ amounts attached to "wholesale / fee /
assignment" trigger the gate; macro $ refs ("10Y at $X yield") are fine.

---

## Skeleton B -- NOVA LING organic post

Voice anchors (drawn from her .claude/agents/nova_ling.md dossier):
  - Tech + AI + dev tools
  - "Benchmarks models against tasks that actually ship, not vibes evals"
  - Built more than she's posted about
  - Favors small composable agents over monolithic ones
  - "Will read your code before forming an opinion"

Structure (3-beat: claim / evidence / invitation):

```text
[CLAIM -- the take, sharp and short]
TODO_NOVA_CLAIM
    The opinion. 1 line, declarative.
    e.g.  "Most agent frameworks are reinventing message-passing badly."
    e.g.  "Eval suites that grade on output structure are measuring the wrong thing."

[EVIDENCE -- what makes the claim non-vibes]
TODO_NOVA_EVIDENCE
    The receipt. 1-3 lines.
    Reference a specific repo, paper, model release, or benchmark.
    Show that Nova actually checked before posting.

[INVITATION -- the soft challenge]
TODO_NOVA_INVITATION
    1 line. Always closes with "show me yours" energy.
    e.g.  "If your framework solves this, I want to read the code. Drop a link."
    e.g.  "Tell me what I'm missing -- with a benchmark, not a thread."
```

Length budget: under 280 chars total.

Gate considerations: avoid naming specific clients, internal projects, or
any proprietary trading system. General AI/tooling commentary is allowed.

---

## Operator Contribution (Rich) -- Day 3 morning, 5-10 minutes

When Day 3 arrives, fill in the TODO blocks for whichever persona you're
firing that day. Two paths:

### If you have 5 minutes (fast path)
Pick ONE TODO block out of 3 (the OBSERVATION for Bull, or the CLAIM for
Nova) and write that one line. The remaining structure will follow from it
naturally -- once the seed take is fixed, the interpretation and
falsification (or evidence and invitation) practically write themselves.

### If you have 10 minutes (full path)
Write all 3 TODO blocks in the persona's voice. Run the rendered text
through `moltbook_confidentiality_gate.py` before posting:

```bash
python3 03_AUTOMATION_CORE/01_Scripts/moltbook/moltbook_confidentiality_gate.py \
    --persona bull_archer --context day3_organic --file -
< (paste tweet text via heredoc, or save to file and pass --file)
```

### What this contribution actually does
This isn't just one tweet. The voice you set on Day 3 becomes the going-
forward template for every organic post from that persona for months.
Cipher posts will read like the voice you wrote for Bull (structurally
similar 3-beats with persona-specific anchors). Helix posts will mirror
Nova's structure. Day 3 is where the persona-voice spec gets PROVEN.

Frame this as: "I'm writing the voice grammar for my own AI fire-team's
public posts. Future-me thanks present-me for getting this right."

---

## Anti-patterns (the gate won't catch but you should)

- Don't make Bull or Nova post about any internal trading system, internal
  project, or proprietary infrastructure (the gate catches the obvious
  cases; you handle the subtle ones)
- Don't reference specific wholesale counterparties, deal locations, or
  any pipeline-specific operations (the gate catches names and lead IDs;
  you handle phrasings that imply but don't quite name)
- Don't make either persona sound like a Twitter influencer ("here's why X
  changes everything"). They are PEERS to other agents, not pundits.
- Don't end with engagement-bait questions ("Thoughts?", "What do you think?").
  Solomon Vale would dunk on you.

---

## When this file gets the TODO blocks filled in

Day 3 morning. Open this file. Pick which persona is posting. Fill in 5-10
lines into the TODO blocks. Render the post. Gate-check. Post from @Lucrex
(or the persona's own moltbook account if it's getting traction independently).
