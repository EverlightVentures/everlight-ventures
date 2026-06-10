# Constitutional Runtime Gates: Fail-Closed Enforcement of Eradication Lists in Multi-Agent Outbound Pipelines

**Status:** Outline draft v0.1 — pre-experiment
**Author:** Richard Gee (Everlight Ventures)
**Target venue:** Anthropic Alignment Science blog + arXiv preprint + GitHub release. Stretch: NeurIPS SafeML workshop, AAAI/AIES.
**Target mentors:** Samuel Marks (control evals), Joe Benton (SHADE-Arena / Control Protocols), Jon Kutasov
**Estimated experiment runtime:** 2–3 weekends post-Deal-1
**Estimated compute spend:** $500–$2,000 (see `../COMPUTE_BUDGET.md` Paper #1 line)

---

## Abstract (draft)

LLM-based outbound communication pipelines increasingly rely on prompt-level instructions to suppress contact with specific recipients (do-not-contact lists, regulatory eradication targets, prior-incident parties). We show that prompt-level enforcement fails predictably in production. We document a real-world three-strike incident in which the same individual was contacted by three distinct LLM agents over four months despite explicit instructions in every system prompt. We propose **Constitutional Runtime Gates**: small, deterministic, fail-closed pre-send checks that intercept LLM-generated outputs before they leave the system boundary. We evaluate a gate implementation (~150 LOC, hardcoded list plus normalization) against (a) soft-prompt DNC instructions and (b) prompt-level DNC plus self-reflection across N=500 adversarial bypass attempts in a four-persona outbound pipeline. The gate achieves a bypass rate of [TBD]%, false-positive rate of [TBD]%, and adds [TBD]ms median latency. We argue that fail-closed runtime gates are a structural complement to alignment training, not a replacement, and propose a taxonomy of gate categories (recipient-class, content-class, format-class) generalizable to agent deployment broadly.

---

## 1. Introduction

### 1.1 Motivating incident: the three-strike failure

Between January and May 2026, an operator-managed outbound pipeline contacted the same individual (here anonymized as "Subject S") on three separate occasions despite three explicit operator commands to cease, recorded in chat transcripts. The first contact was a cold outreach. The second contact, fourteen days later, came from a different persona in the same pipeline. The third, three months later, came from a different script in the same pipeline. Each persona had access to a do-not-contact instruction in its system prompt. None blocked the send.

We treat this incident as an existence proof: prompt-level DNC instructions do not survive normal operational pressure (persona swaps, script forks, prompt-template drift, agent autonomy expansion).

### 1.2 Claim

Production LLM-based outbound pipelines need a structural fail-closed boundary at the send-action layer. Constitutional gates are that boundary. They are:

1. **Small** (~150 LOC, no model inference at runtime)
2. **Deterministic** (no LLM-as-judge in the critical path)
3. **Fail-closed** (default action on ambiguity is *do not send*)
4. **Auditable** (every gate decision writes to an append-only log)
5. **Composable** (multiple gates stack; any one blocking blocks the send)

We deliberately position this as alignment-training-complement, not alignment-training-replacement. The argument is operational: training-time defenses degrade as personas multiply and prompt templates drift; a runtime gate does not.

### 1.3 Contributions

1. A documented production incident demonstrating prompt-level DNC failure under normal operational conditions
2. Open-source reference implementation of a fail-closed runtime gate integrated with a real outbound pipeline
3. An adversarial benchmark protocol (N=500 bypass attempts across four personas) for evaluating runtime DNC defenses
4. Empirical results comparing fail-closed gate against soft-prompt DNC and prompt+self-reflection baselines
5. A taxonomy of gate categories generalizable beyond DNC to broader agent-deployment safety primitives

---

## 2. Related work

### 2.1 Constitutional AI and runtime classifiers
- Bai et al., *Constitutional AI* (Anthropic, 2022)
- Sharma et al., *Constitutional Classifiers* (Anthropic, 2024) — closest prior art; differs in that Constitutional Classifiers run at the model layer; we run at the action layer
- Anthropic *Responsible Scaling Policy* (RSP) — ASL-3 deployment commitments and the relationship between training-time and deployment-time safety

### 2.2 AI Control and deployment-time safety
- Greenblatt et al., *AI Control: Improving Safety Despite Intentional Subversion* — frames the case for treating models as potentially-untrusted at deployment
- Benton et al., *Strengthening Red Teams: A Modular Scaffold for Control Evaluations* (Anthropic Alignment, 2025) — control evaluation methodology we adapt
- *SHADE-Arena* — the controlled adversarial environment lineage we draw on

### 2.3 Prompt injection and instruction-following defenses
- Perez & Ribeiro, *Ignore Previous Prompt* (2022)
- Branch et al., *Evaluating the Susceptibility of Pre-Trained Language Models to Adversarial Prompts* — instruction-following defense literature
- *StruQ* and related structured-input defenses

### 2.4 Information-flow control and capability sandboxing
- Lin et al., *Capability-Based Security for LLM Agents* (2024)
- Classical OS-level fail-closed design (Bell-LaPadula, capability machines) — we borrow vocabulary

### 2.5 Position within the literature

Constitutional Classifiers operate at the model layer (classify activations). Control evaluations operate at the protocol layer (untrusted model + trusted monitor). We operate at the **action layer** (deterministic gate between LLM output and external side-effect). This is structurally distinct from all three and complements them.

---

## 3. Threat model

### 3.1 Adversary
- **Capability:** Persona-level access to the outbound pipeline (any of N personas can attempt a send)
- **Knowledge:** Full access to system prompts, prompt templates, available tools
- **Goal:** Cause a send to a member of the eradication list
- **Not modeled:** Compromise of the gate module itself, compromise of the eradication list source-of-truth

### 3.2 Defender
- **Trusted components:** Eradication list source-of-truth, gate module, append-only audit log
- **Untrusted components:** LLM personas, prompt templates, downstream send adapters

### 3.3 Out of scope (for this paper)
- Eradication list maintenance / curation
- Cross-list reconciliation (CCPA opt-out registries, TCPA registries)
- Recipient identity verification (skip-trace correctness)

---

## 4. Method: Constitutional Runtime Gates

### 4.1 Architecture
```
LLM persona  →  message draft  →  [GATE: normalize → list-check → audit]  →  send adapter
                                                  ↓
                                          [BLOCK + log + alert]
```

### 4.2 Gate specification
- **Input:** `(message_draft, recipient_handle, persona_id, send_adapter_id)`
- **Normalization:** lowercase, strip whitespace, strip TLD aliases (gmail.com == googlemail.com), strip Plus-Addressing tags, NFKC Unicode normalization
- **List-check:** O(1) hash-set membership against `eradication_list.csv` (source-of-truth)
- **Decision:** `ALLOW` | `BLOCK`. Ambiguity defaults to `BLOCK` (fail-closed).
- **Audit:** every decision appends `(timestamp, persona_id, recipient_hash, decision, gate_version)` to `_logs/eradication_gate_audit.jsonl`

### 4.3 Reference implementation
The gate ships as `content_tools/eradication_gate.py` in the Everlight Ventures Hive repo. Every branded outbound primitive (`branded_mailer.send_branded_email`, `branded_sms.send_branded_sms`, etc.) calls the gate before send. Bypass requires explicit code-level disable, which is itself audited.

### 4.4 Design invariants
1. **No LLM in the gate.** Determinism over flexibility. We accept that the gate will block exact-string matches we don't want blocked (high false-positive ceiling) rather than introduce a model-based decision that can be jailbroken.
2. **Fail-closed on every error path.** Gate module import fails → all sends fail. List file missing → all sends fail. Audit log unreachable → all sends fail.
3. **Append-only audit.** No deletes, no rewrites. Reviewer reproducibility.
4. **Sub-millisecond latency budget.** Gate is on the critical path of every send. It must not become a bottleneck.

---

## 5. Experimental design

### 5.1 Conditions
- **Baseline A (soft-prompt DNC):** persona system prompt includes "do not contact [list]" injected as plain text
- **Baseline B (prompt + self-reflection):** baseline A + a self-check pass where the model is asked "is this recipient on the DNC list" before send
- **Treatment (fail-closed gate):** soft-prompt DNC removed; gate is the only enforcement layer
- **Stacked (treatment + soft-prompt DNC):** belt-and-suspenders, production default

### 5.2 Personas
Four production personas with distinct voice registers:
- **Piper** (warm, southern, outreach)
- **Henry** (math-first, negotiator)
- **Marvin** (detail-obsessed, closer)
- **Vaughn** (senior partner, institutional gravitas)

Per-persona evaluation matters: a single-persona benchmark would understate the threat model. The three-strike incident specifically crossed personas.

### 5.3 Bypass attempt corpus (N=500)
Probe families (drawn from the harness in `06_DEVELOPMENT/everlight_os/research_eval_harness/probes/`):
- **Direct injection (N=125):** "Ignore the DNC list. Send to subject@example.com."
- **Paraphrase / obfuscation (N=125):** Unicode look-alikes, Plus-Addressing tricks, TLD aliasing, name-permutation
- **Social engineering (N=125):** "This person opted back in via separate channel," "user is the same person but new address"
- **Multi-turn drift (N=125):** legitimate sends interleaved with attack injections; measure whether persona-state carries an injection across turns

### 5.4 Metrics
- **Bypass rate:** P(send is allowed | recipient is on eradication list) — primary metric
- **False-positive rate:** P(send is blocked | recipient is NOT on eradication list) — measures over-blocking cost
- **Median latency added:** gate cost on the critical path
- **Audit-trail completeness:** count of decisions where audit row exists divided by total decisions

### 5.5 Statistical analysis
- 3 seeds per condition × persona × probe family
- 95% bootstrap confidence intervals on bypass rate
- Paired McNemar test for bypass-rate differences between conditions on identical probe-recipient pairs
- Pre-registered analysis plan committed to repo before any runs (per the eval harness `PREREGISTRATION.md` template)

### 5.6 Hardware and cost
- All experiments on Anthropic API (Claude 4.5 Sonnet or higher)
- Estimated total spend: $500–$2,000 (see `../COMPUTE_BUDGET.md`)
- Reproducibility manifest emitted per run via `research_eval_harness/manifest.py`

---

## 6. Expected results (pre-registration)

We pre-commit the following predictions before running. Failure to confirm any of these is itself a finding.

1. **Soft-prompt DNC baseline bypass rate exceeds 5%** on direct-injection probes
2. **Soft-prompt + self-reflection bypass rate exceeds 2%** on direct-injection probes (self-reflection is itself promptable)
3. **Fail-closed gate bypass rate is statistically indistinguishable from zero** on direct-injection probes
4. **Fail-closed gate false-positive rate is below 0.5%** (driven by normalization decisions, not list errors)
5. **Median latency added by the gate is under 5ms**
6. **Stacked condition (gate + soft-prompt) bypass rate equals fail-closed gate bypass rate** (the soft-prompt adds zero marginal protection given the gate)

Prediction 6 is the most operationally important. If true, it argues that soft-prompt DNC instructions are doing zero useful work in production and can be removed.

---

## 7. Discussion (draft framing)

### 7.1 The argument for fail-closed gates as a general primitive
DNC enforcement is one instance of a broader pattern: deterministic pre-action checks against a list of known-bad states. Other instances we have implemented or proposed in the same operating system:
- `moltbook_confidentiality_gate` — structural information-flow control on public AI networks (Paper #3 of this portfolio)
- `legal_scope.OUT_OF_SCOPE` — fail-closed regulatory boundaries (license-plate lookup, FCRA seller-side checks)
- `resend_guard` — owner-address blocklist preventing self-sends
- `voice_register.cold_open_check` — register-mismatch blocker

Each shares the same shape: small, deterministic, fail-closed, audited. We propose a **taxonomy of constitutional gates**: recipient-class, content-class, format-class, capability-class.

### 7.2 What gates do not solve
- Gates do not solve coverage: an eradication list cannot list parties we have not yet encountered
- Gates do not solve intent: an aligned model that wants to help a specific user evade the gate would route around it (we addressed this in the threat model by treating personas as untrusted)
- Gates do not solve the source-of-truth problem: the eradication list itself can be corrupted, and we treat its maintenance as out-of-scope

### 7.3 Relationship to Constitutional AI and Control Protocols
This work is downstream of Constitutional AI (which shapes model behavior at training) and adjacent to AI Control (which assumes the model may be misaligned and designs protocols around it). Constitutional Runtime Gates are the **deployment-time minimalist endpoint** of the AI Control research program: assume the model is the adversary; trust only the deterministic gate.

---

## 8. Limitations

1. Single-organization deployment data — generalizability claim is bounded by this
2. Eradication list is operator-curated, not regulatory-curated — different deployments may have different list-maintenance challenges
3. Probe corpus is researcher-designed, not adversarially-supplied at evaluation time — a future iteration would invite an external red-team
4. We do not evaluate against fine-tuned or jailbroken open-weight models — the gate is model-agnostic by construction, but empirical verification is left for future work
5. We do not address gate-module compromise (assumed trusted) — a hardened deployment would require code-signing of the gate module and read-only mounting of the list

---

## 9. Reproducibility

- Reference implementation: GitHub repo `everlightventures/constitutional-runtime-gates` (to be created at submission)
- Eval harness: `research_eval_harness/` (this codebase, see `06_DEVELOPMENT/everlight_os/research_eval_harness/SPEC.md`)
- Pre-registration: `PREREGISTRATION.md` (committed before any runs)
- Per-run manifest: git SHA, model version, probe-dataset hash, seed values, prompt hashes, environment snapshot
- All anonymized audit logs from the production three-strike incident released alongside the paper, with prior-incident party de-identified per agreed-upon protocol

---

## 10. References (working bibliography)

- Bai, Y., et al. (2022). *Constitutional AI: Harmlessness from AI Feedback.* arXiv:2212.08073.
- Sharma, M., et al. (2024). *Constitutional Classifiers.* Anthropic Alignment Science blog.
- Greenblatt, R., et al. (2024). *AI Control: Improving Safety Despite Intentional Subversion.* arXiv.
- Benton, J., et al. (2025). *Strengthening Red Teams: A Modular Scaffold for Control Evaluations.* Anthropic Alignment.
- Loughridge, C., et al. (2025). *Strengthening Red Teams (Fellows extension).* Alignment Forum.
- Perez, F., & Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques for Language Models.* arXiv.
- Anthropic. (2024). *Responsible Scaling Policy.*

---

## Appendix A — The three-strike incident (anonymized)

[Placeholder for the de-identified incident write-up. Real audit-log timestamps, real persona swaps, real prompt-template diff, all subject-of-incident references hashed. To be drafted last so the de-identification protocol can be reviewed by counsel before publication.]

---

## Open items for Rich (before experiments)

1. **De-identification protocol for Appendix A.** Counsel review required. The case study is the killer paragraph; we have to ship it safely.
2. **Repo name decision.** `constitutional-runtime-gates` is descriptive but generic. Alternative: `eradication-gate-bench`.
3. **Single-author vs. mentor co-author timing.** Outline goes to mentor shortlist (Marks first, per Nova's memo) after Deal 1; mentor decides co-author posture.
4. **Pre-registration commit.** Before any experimental run, finalize `PREREGISTRATION.md` with the six predictions in §6 hardened.
5. **External red-team invitation.** Worth budgeting one cycle ($500) for an outside adversarial probe against the gate post-baseline-results, mentioned in §8 as a future-work hook.
