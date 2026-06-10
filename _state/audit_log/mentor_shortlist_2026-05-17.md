# Anthropic Fellows Mentor Shortlist
**Date:** 2026-05-17
**Author:** Nova Ling (Tech/AI beat, Hive)
**Context:** Pre-application warm-engagement targeting for 3-paper bridge portfolio (Constitutional Runtime Gates / Roundtable Protocol / Voice-Register Confidentiality Envelopes).

---

## TL;DR

Five of the six candidates are confirmed alive at Anthropic, all are MATS or Fellows mentors, all publish on Alignment Forum + X. The targeting thesis from earlier holds: every recent Anthropic Fellows paper has 2-3 Anthropic insiders co-authored, not just listed as "advisors." Cold-engagement before applying is real signal.

**Doctrine-shifting find:** Mrinank Sharma (former Safeguards Research Team lead, would have been a natural Paper #1 target) resigned from Anthropic on 2026-02-09. Drop him from any list. The Safeguards/Constitutional Classifiers lane now flows through Hoagy Cunningham and Alwin Peng. See memory entry filed alongside this memo.

**Procedural reality check:** Joe Benton (Fellows research lead) explicitly states "applications must go through the official form, not the mentors" and that he doesn't reply to most cold inbound. This does NOT mean cold engagement is worthless. It means: do the engagement on the public surface (X, Alignment Forum, LessWrong), build a body of public technical signal they can find when your application crosses their desk, and route the actual ask through Greenhouse.

---

## Summary table

| # | Name | Paper | Alignment | Public surface | Receptiveness | First-contact vector |
|---|---|---|---|---|---|---|
| 1 | Samuel Marks | #1 Runtime Gates | 8/10 | X @saprmarks, LW/AF active shortform | High (DMs open per his own X post) | LW comment on his "Alignment Auditing as Numbers-Go-Up Science" with eradication-gate benchmark numbers |
| 2 | Joe Benton | #1 Runtime Gates | 9/10 | joejbenton.com, AF, scholar | Low to medium (research lead, gets flooded). Route through Fellows app. | Cite his SHADE-Arena + Control Evaluations papers in Paper #1 abstract; apply via Greenhouse listing him as preferred mentor |
| 3 | Jon Kutasov | #1 Runtime Gates | 9/10 | LinkedIn, ResearchGate, co-author w/ Benton on Control Evals | Medium (early-career, less swamped than Benton) | X reply to Buck Shlegeris's thread on Kutasov's side-task agent eval paper, with a concrete observation from runtime-gate logs |
| 4 | Sam Bowman | #2 Roundtable | 7/10 | X @sleepinyourhat (active), AF, MATS mentor | Medium (high profile, will engage substantive critique) | AF comment on his "Scaling Laws for Scalable Oversight" with position-revision data from probe phase |
| 5 | Ethan Perez | #2 Roundtable | 10/10 | ethanperez.net, AF, MATS megastream mentor | High structurally (MATS megastream is the cleanest path) | Apply to MATS Summer 2026 megastream with Perez as preferred mentor; cite his ICML 2024 best-paper on persuasive-debate-improves-truthfulness as direct lineage |
| 6 | Jack Lindsey | #3 Voice-Register | 10/10 | X @Jack_W_Lindsey, jlindsey15.github.io, leads "Model Psych" team | High (active poster, niche topic, less swamped than safety leads) | X reply to his Persona Vectors thread with a concrete leakage-prevention experiment from our voice-register classifier; cite his paper in our abstract |
| 7 | Andy Arditi | #3 Voice-Register | 9/10 | AF profile, came up through SPAR under Nina Rimsky | High (early-career, came up through a public mentorship program himself) | AF comment on Persona Vectors with a probing methodological question about persona-vector + classifier ensemble |
| 8 | Fabien Roger | #3 Voice-Register (backup) | 8/10 | AF, LW, MATS mentor, scholar | Medium-high (active AF poster, replies in threads) | AF reply on his Alignment Faking shortform with a connection to information-flow control |

---

## Per-candidate intel

### 1. Samuel Marks -- Paper #1 (Runtime Gates)
- **Role at Anthropic:** Leads the cognitive oversight subteam under the Alignment Science org. Mandate is to oversee AI systems based on whether anything looks suspicious about the cognitive processes, not just I/O behavior.
- **Recent overlapping work:** "Auditing Language Models for Hidden Objectives" (2025) -- audit methodology that overlaps with our fail-closed enforcement angle in spirit. Also "Sparse Feature Circuits" interpretability lineage.
- **Public surface:** X @saprmarks (active, replies to technical questions), LessWrong/Alignment Forum active shortform.
- **Alignment:** 8/10 -- our paper is more deployment-infra than mech-interp, but the audit lineage maps. Marks is a MATS mentor and his public posture is "DMs open for those interested in joining."
- **First-contact vector:** Comment on his LW post "Towards Alignment Auditing as a Numbers-Go-Up Science" with a concrete observation -- e.g., "we ran a 3-strike eradication-gate against a multi-agent outbound pipeline and got [N] catches over [M] sends; the audit pattern here looks isomorphic to your numbers-go-up framing." Single technical sentence. No pitch.
- **Receptiveness signal:** High. His own X post explicitly invited DM-inbound.

### 2. Joe Benton -- Paper #1 (Runtime Gates)
- **Role at Anthropic:** Manages the Scalable Oversight team AND is the **research lead for the Anthropic Fellows Program.** This is the highest-leverage single name on this list, but also the most defended inbox.
- **Recent overlapping work:** "Evaluating Control Protocols for Untrusted AI Agents" (arXiv 2025, with Kutasov), "SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents" (arXiv 2025), "A3: An Automated Alignment Agent for Safety Finetuning" (2026 Anthropic blog). Control protocol evaluation is exactly the conceptual neighborhood of our runtime-gate paper.
- **Public surface:** joejbenton.com + research page on github.io. Has a Google Scholar with strong recent throughput. Not heavily on X.
- **Alignment:** 9/10. His SHADE-Arena and Control Protocols papers ARE the parent body of work our paper is contributing to. Cite them as direct lineage in our abstract.
- **First-contact vector:** DO NOT email him. He explicitly states (on his own site) that he gets too many emails and can't reply. Route is: write Paper #1 with explicit citation of his Control Protocols and SHADE-Arena papers, apply to the Fellows program through Greenhouse, list Benton as a preferred mentor. The paper itself is the cold-contact.
- **Receptiveness signal:** Low for direct outreach, high for application-channel. He has "supervised 15+ fellows" so the volume of work he absorbs through the official channel is real.

### 3. Jon Kutasov -- Paper #1 (Runtime Gates)
- **Role at Anthropic:** Automated Alignment Research Trainer. Fellows Program mentor. Likely lower inbox volume than Benton.
- **Recent overlapping work:** "SHADE-Arena" (co-lead author with Benton). "Natural Emergent Misalignment from Reward Hacking in Production RL" (Anthropic 2025) -- shows production RL producing emergent misalignment, our paper's "fail-closed gate" is the structural defense for exactly this failure mode.
- **Public surface:** LinkedIn, ResearchGate, OpenReview. Less X-active. Buck Shlegeris (Redwood) posts about his work on X regularly.
- **Alignment:** 9/10. The Natural Emergent Misalignment paper is the textbook motivation for runtime gates.
- **First-contact vector:** Reply on Buck Shlegeris's X thread about Kutasov's side-task agent eval paper with: "Ran a runtime-gate variant of this on a multi-agent outbound pipeline -- caught the side-task in [N]/[M] adversarial scenarios. The fail-closed property mattered more than classifier accuracy." Concrete, technical, no ask.
- **Receptiveness signal:** Medium. Earlier-career and less swamped than Benton, but the right channel is still public-then-application.

### 4. Sam Bowman -- Paper #2 (Roundtable Protocol)
- **Role at Anthropic:** Leads a research group on AI alignment + welfare, with a focus on evaluation. On leave from NYU. MATS mentor.
- **Recent overlapping work:** "Measuring Progress on Scalable Oversight" (the foundational paper for the entire scalable-oversight evaluation methodology, our Paper #2 contributes a debate-with-position-revision measurement to this lineage), "Scaling Laws for Scalable Oversight" (arXiv 2025), the Khan et al. (2024) debate paper "Debating with More Persuasive LLMs Leads to More Truthful Answers" (ICML 2024 best paper).
- **Public surface:** X @sleepinyourhat (very active, replies to substantive technical critique), Alignment Forum, MATS mentor profile.
- **Alignment:** 7/10. He's more eval-methodology than multi-agent debate specifically, but our position-revision-under-probe metric is exactly the kind of empirical contribution he engages with. The Khan et al. paper is the closest direct parent.
- **First-contact vector:** AF comment on "Scaling Laws for Scalable Oversight" with position-revision data: "In a 5-phase 6-persona protocol we observed measurable position-revision in [X]% of probe-phase exchanges. Curious if you'd consider this orthogonal to or a special case of the scaling-laws framing." One sharp question, public surface.
- **Receptiveness signal:** Medium to high. He engages substantive critique on X and AF; he just won't reply to "advice please" inbound.

### 5. Ethan Perez -- Paper #2 (Roundtable Protocol)
- **Role at Anthropic:** Leads a team on AI control, adversarial robustness, AI safety. ICML 2024 best paper on debate-improves-truthfulness. MATS Summer 2026 megastream mentor (joint Anthropic + OpenAI).
- **Recent overlapping work:** The 2024 debate paper IS the foundational empirical result for the entire "debate improves truthfulness" research direction. Our Paper #2 sits one rung downstream -- we measure position-revision (a finer-grained signal than aggregate truthfulness). Also recent work on CoT monitoring (2025) and an inverse-scaling result on test-time reasoning compute.
- **Public surface:** ethanperez.net (active personal site with hiring/mentor advice), Alignment Forum, MATS megastream mentor profile. He has a public "advice for strong Fellows applicants" essay that Joe Benton explicitly tells people to read.
- **Alignment:** 10/10. Closest topical match on this list.
- **First-contact vector:** Apply to MATS Summer 2026 megastream listing Perez as preferred mentor. The megastream is the CLEANEST receptiveness path on this list -- it's an explicit "by applying you're being considered for all megastream mentors, indicate which one you want" structure. Side-channel: read his "advice for strong Fellows applicants" essay, structure Paper #2 to embody every recommendation in it.
- **Receptiveness signal:** Highest of the list, structurally. He runs an open recruiting funnel via MATS.

### 6. Jack Lindsey -- Paper #3 (Voice-Register Confidentiality)
- **Role at Anthropic:** Leads the "Model Psych" team, studying introspection, situational awareness, personas, emotion representations. Co-author on the Persona Vectors paper (arXiv 2507.21509, July 2025).
- **Recent overlapping work:** "Persona Vectors: Monitoring and Controlling Character Traits in Language Models" (July 2025) -- this is the direct parent paper for our Paper #3. Persona vectors are interpretability handles INSIDE the model; voice-register classifiers are deployment-time handles OUTSIDE the model. The papers are complementary. Also recent work on Claude's "introspection rate" and emotion vectors.
- **Public surface:** X @Jack_W_Lindsey (active, niche-topic), jlindsey15.github.io, Niskanen Center podcast appearance on "AI psychology."
- **Alignment:** 10/10. Strongest topical match for Paper #3.
- **First-contact vector:** X reply on his Persona Vectors announcement thread with one concrete experiment: "Built a voice-register classifier as an information-flow gate for a persona deployed on a public AI-agent network; got [N]% leakage prevention on Hive-internal terms across [M] turns. Looks like the deployment-side dual of persona vectors. Will share writeup." This is the single highest-leverage cold contact on the list -- niche topic, active poster, our paper directly extends his.
- **Receptiveness signal:** High. Lower inbox volume than safety leads, niche enough that a serious technical contribution stands out.

### 7. Andy Arditi -- Paper #3 (Voice-Register Confidentiality)
- **Role at Anthropic:** Researcher, persona vectors co-author. Came up through Berkeley's SPAR program under Nina Rimsky -- which is relevant because SPAR is itself a public mentorship pipeline, and Arditi is therefore biographically receptive to non-traditional applicants.
- **Recent overlapping work:** Persona Vectors (co-author). Earlier mech-interp work on refusal directions.
- **Public surface:** Alignment Forum profile (active). Less X-prominent than Lindsey.
- **Alignment:** 9/10.
- **First-contact vector:** AF comment on Persona Vectors thread with a probing methodological question: "Curious how persona-vector steering interacts with a deployment-time register classifier ensemble -- specifically, does the classifier 'see' a register shift before the vector activation crosses the steering threshold, or after?" Sharp, specific, signals you've actually read the paper.
- **Receptiveness signal:** High. SPAR alum, so the "early-career researcher who came up through a public mentorship" pattern is something he literally lived through. Strong instinct to pay it forward.

### 8. Fabien Roger -- Paper #3 backup (also could fit Paper #1)
- **Role at Anthropic:** AI safety researcher, previously Redwood Research. Works on AI control and alignment faking. MATS mentor.
- **Recent overlapping work:** Co-author on Alignment Faking in Large Language Models (Dec 2024). Built ShadeArena, BashArena, SusEval, ControlArena -- platform-grade evaluation infra, which is the same flavor as our Paper #1 runtime-gate work.
- **Public surface:** Alignment Forum (very active shortform), LessWrong, Google Scholar, MATS mentor profile.
- **Alignment:** 8/10 for Paper #3, 9/10 for Paper #1.
- **First-contact vector:** AF reply on his shortform tying voice-register information-flow control to his control-eval framework: "Reads like a control-eval variant where the 'untrusted' surface is the persona's outbound text and the gate is a classifier."
- **Receptiveness signal:** Medium-high. Active AF replier.

---

## Paper #3 candidate proposals

Original shortlist had Paper #3 TBD. Proposing three names in confidence order:

1. **Jack Lindsey** -- direct parent paper (Persona Vectors), active X poster, niche-topic-not-swamped, leads Model Psych team. Pair our deployment-side persona-as-information-flow-channel work with his interpretability-side persona-vectors work. Highest single-name leverage on Paper #3.

2. **Andy Arditi** -- co-author on same Persona Vectors paper, earlier-career, came up through a public mentorship program (SPAR), receptive to non-traditional applicants by biography.

3. **Fabien Roger** -- if Paper #3 doesn't land with Lindsey/Arditi, Roger's control-eval framework absorbs information-flow-control as a natural variant. Also a backup co-mentor for Paper #1.

Considered and dropped: **Mrinank Sharma** (resigned 2026-02-09, no longer at Anthropic). **Hoagy Cunningham** and **Alwin Peng** (constitutional classifiers lineage) -- strong topical fit for Paper #1 but Marks/Benton/Kutasov already cover that lane better with more papers cited.

---

## Ranked outreach order

1. **Jack Lindsey (X reply on Persona Vectors thread)** -- highest leverage cold contact. Niche topic, active poster, direct parent paper, low inbox volume. If we get one engagement-signal in the next 4-6 weeks before applying, this is where it comes from.
2. **Ethan Perez (MATS megastream application)** -- cleanest structural path. Apply to MATS Summer 2026 listing Perez as preferred mentor BEFORE applying to the main Fellows program. MATS is the funnel that feeds Fellows; doing both is a stronger signal than doing only Fellows.
3. **Samuel Marks (LW comment on alignment-auditing post)** -- DMs are explicitly open, public surface is active, audit lineage maps to our runtime-gate work.
4. **Andy Arditi (AF comment on Persona Vectors thread)** -- early-career, biographically receptive, lower inbox volume than Lindsey.
5. **Jon Kutasov (X reply on Shlegeris's thread about his side-task paper)** -- public surface less active but the technical adjacency is real.
6. **Sam Bowman (AF comment on Scaling Laws for Scalable Oversight)** -- substantive critique only, no soft outreach.
7. **Fabien Roger (AF reply on shortform)** -- backup signal-builder.
8. **Joe Benton** -- DO NOT cold contact. The paper itself, citing his work, submitted through Greenhouse, IS the contact.

**Hard rule:** every cold-contact carries one concrete experimental observation or one sharp methodological question. Zero pitches. Zero "I'm building a portfolio" framing. We are an engineer reporting a result, not a candidate seeking attention. The portfolio shows up when they look us up after we say something useful.

---

## Sources

- [Samuel Marks - MATS Mentor](https://www.matsprogram.org/mentor/marks)
- [Samuel Marks (@saprmarks) / X](https://x.com/saprmarks)
- [Sam Marks - LessWrong](https://www.lesswrong.com/users/sam-marks)
- [Joe Benton personal site](https://joejbenton.com/)
- [Joe Benton Research](https://joejbenton.github.io/research/)
- [Jon Kutasov LinkedIn](https://www.linkedin.com/in/jonathan-kutasov/)
- [Sam Bowman (@sleepinyourhat) / X](https://x.com/sleepinyourhat)
- [Sam Bowman - MATS Mentor](https://www.matsprogram.org/mentor/bowman)
- [Ethan Perez personal site](https://ethanperez.net/)
- [Ethan Perez - MATS Megastream](https://www.matsprogram.org/mentor/megastream)
- [Anthropic and OpenAI Megastream at MATS Summer 2026](https://www.matsprogram.org/stream/megastream)
- [Jack Lindsey (@Jack_W_Lindsey) / X](https://x.com/Jack_W_Lindsey)
- [Jack Lindsey personal site](https://jlindsey15.github.io/)
- [Persona Vectors paper (arXiv 2507.21509)](https://arxiv.org/abs/2507.21509)
- [Persona Vectors -- Anthropic Research blog](https://www.anthropic.com/research/persona-vectors)
- [Andy Arditi - Alignment Forum](https://www.alignmentforum.org/users/andy-arditi)
- [Fabien Roger - Alignment Forum](https://www.alignmentforum.org/users/fabien-roger)
- [Fabien Roger - MATS Mentor](https://www.matsprogram.org/mentor/roger)
- [Anthropic Fellows Program 2026](https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/)
- [Greenhouse: Anthropic Fellows Program -- AI Safety](https://job-boards.greenhouse.io/anthropic/jobs/5183044008)
- [Greenhouse: Anthropic Fellows Program -- AI Security](https://job-boards.greenhouse.io/anthropic/jobs/5030244008)
- [Mrinank Sharma resignation coverage](https://thefederal.com/category/business/who-is-mrinank-sharma-why-did-he-quit-anthropic-229292)
- [Reasoning Models Don't Always Say What They Think (Benton et al.)](https://assets.anthropic.com/m/71876fabef0f0ed4/original/reasoning_models_paper.pdf)
- [Natural Emergent Misalignment from Reward Hacking (Kutasov et al.)](https://assets.anthropic.com/m/74342f2c96095771/original/Natural-emergent-misalignment-from-reward-hacking-paper.pdf)
