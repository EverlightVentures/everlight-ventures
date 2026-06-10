---
name: everlight_humanizer
description: Strip the AI tells out of copy and match it to Rich's voice + the target reader's register. Wraps style_enforcer + everlight_copy_guard. Use as the final pass before any human reads Everlight copy.
---

When to use:
- Final pass on any prose a human will read for content (email body, landing copy, post, report intro, book passage).
- After a draft comes back from a model and reads generic or robotic.

NOT for:
- Code, logs, config, one-line ops pings.
- Numbers-only outputs (contract math, KPI tables).

Procedure:
1. Run everlight_copy_guard first: no em-dashes, no filler, concrete language, claims map to evidence.
2. Kill the AI tells: "delve", "in today's fast-paced", "it's important to note", "unlock", "elevate", "seamless", "robust", "leverage" as a verb, hollow tricolons, hedging ("may", "might", "could" stacked).
3. Set the register via content_tools/recipient_register.py: operator | warm | peer | consultative | professional_direct. Voice scales to the READER, not the sender.
4. Match Rich's cadence: confident, direct, street-smart, no hedging. Short sentences carry weight. Cut throat-clearing intros.
5. Keep the persona's own voice intact (Piper warm Nashville, Hammer "champ when do we close", Lucrex Cold Scripture only on genuine disrespect, else WARM_CURIOUS).
6. Final check via style_enforcer agent for tone + register consistency.

Register in roster.yaml under skills: owner = style_enforcer (41_style_enforcer), buddy = everlight_content_director.
