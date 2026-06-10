# Forge -- Logistics Swarm POC: Fork-and-Deploy Plan
**Author:** Franklin "Forge" Steele, Codex Labs
**Status:** DRAFT, awaiting Lucrex approval. Nothing has been executed.
**Date:** 2026-05-07

---

## 0. Operator Truth -- failures and unknowns first

- **UNVERIFIED (BLOCKER for step 2):** Oracle E5 SSH (port 22 -> 163.192.19.196) timed out from the phone twice during plan-write. Could not pull live `node --version`, `npm --version`, `python3 --version`, `which docker`, `df -h`, or `ss -ltn`. Until SSH is reachable, every claim about the target host is unverified.
- **UNVERIFIED:** Open Swarm GitHub URL is not in the transcripts -- Julian Goldie's two transcripts call it "Open Swarm" / "open-source" but the literal `github.com/...` slug is in the YouTube description, not the captions. Step 1 must resolve this before clone.
- **UNKNOWN:** whether `ANTHROPIC_API_KEY` is in `/home/opc/.env` on Oracle. Phone-side `.env` only carries `OPENAI_API_KEY` and `RESEND_API_KEY`. We have an OpenAI key for sure; Anthropic is presumed-on-Oracle, must confirm.
- **UNKNOWN:** Open Swarm sandbox model. Transcripts say data analyst "runs inside an isolated Python environment" -- need to check whether that's Docker, `subprocess` chroot, or `e2b`/`riza` SaaS (a paid sub would be a dealbreaker per free-path-only).

---

## 1. Repo discovery
- Search `github.com/JulianGoldie` and `github.com/AIProfitBoardroom` for `open-swarm` / `openswarm`. Also check the YouTube description on `c5DdXzqaeVU` and `QreoZTA4YEA` for the canonical link.
- Capture: license (must be MIT or permissive -- transcript says "fully open source"), latest tag/commit, `package.json` Node engine, `requirements.txt` Python pin, `agents.md` schema.
- Output: paste URL + commit SHA + license string into the deploy ticket. No clone yet.

## 2. Where it runs -- Oracle E5, NOT the phone
- Phone (Termux + proot + sdcard-FUSE) has a documented Node/ELF crash history (Starship replaced p10k for the same class of failure). Open Swarm needs Node >= 20 and a Python sandbox; phone is a non-starter.
- Target: Oracle E5 (163.192.19.196), same VM as n8n/Blinko/Django. 16 GB RAM, room for one more long-running Node process.
- **Pre-flight commands to run AS THE FIRST STEP after Lucrex approval (currently blocked by SSH timeout):**
  ```
  node --version          # need >= 20.x; if 18.x install nvm + node 20 LTS
  npm --version
  python3 --version       # need >= 3.10
  which docker            # for sandbox + composio fallbacks
  df -h /home/opc         # need >= 5 GB free
  ss -ltn | grep -E ':(3101|3102|3103|3104|3105|3106|3107|5678|1111|8200|8504)\b'
  ```
- Run inside `tmux` session `swarm-logistics` so long swarm runs survive SSH drops.

## 3. Fork strategy
- `git clone <upstream> /home/opc/everlight_swarms/logistics`
- Rename package + binary: `everlight-logistics-swarm`. Keep `agents.md` verbatim (it is the customization framework).
- Swap agents: keep Orchestrator + Deep Research + Data Analyst + Slides + Docs. Repurpose Virtual Assistant -> **MSA/SOW Drafter** (Logistics-specific). Park Image/Video agents v1 (no FAL/Google video keys -- gracefully degrade).
- New shared resource: `assets/everlight_brand.json` (palette, fonts, wordmark SVG path) loaded by Slides + Docs prompts.

## 4. Auth -- existing keys only, zero new subs
- Required: `OPENAI_API_KEY` (confirmed present phone-side) OR `ANTHROPIC_API_KEY` (presumed in `/home/opc/.env`, must verify).
- Skip optional paid keys: Composio, Google Gemini/VO, FAL, Tavily/Perplexity-search. Tools degrade per Julian's transcript -- we accept reduced research depth in v1.
- Wire-up: source `/home/opc/.env` in the swarm launcher script. NO new key files.

## 5. Budget gating -- token kill-switch
- Build `content_tools/swarm_budget.py` mirroring `resend_budget.py` shape:
  - daily token cap (default 500k input + 200k output per day across all swarm runs)
  - monthly cap (default 8M input / 3M output)
  - per-category buckets: `client_package` (priority), `internal_research`, `experiment`
  - kill-switch: hard-fail before any agent call if cap exceeded; Slack `#hive-alerts` warning at 80%.
- Hook: patch swarm's LLM client wrapper (likely `src/lib/llm.ts` or equivalent) to call `swarm_budget.assert_under_cap(category, est_tokens)` before each request.

## 6. Output sink + HiveArtifact registration
- Force swarm output dir to `/home/opc/hive_reports/swarm_logistics/<run_id>/`. Already served by the report nginx at `http://127.0.0.1:2200/reports/`.
- After every swarm run, post-hook script calls `content_tools.hive_logger.register_artifact()` with `{kind: 'swarm_package', run_id, agent_chain, files: [...]}` -- this is the same chokepoint every other Hive bot uses.
- Final swarm output also calls `content_tools.n8n_replacements.publish_gdoc()` per file so the deck/MSA/SOW each land in Drive + post a branded Slack card.

## 7. Branding -- slides + docs must wear the gold
- Inject into Slides agent system prompt: "All decks use Playfair Display headings, Inter body, JetBrains Mono code; palette `#D4A843 / #0A0A0A / #E8E8E8`; first slide carries the EVERLIGHT VENTURES wordmark; final slide signed by Forge / Codex Labs."
- Inject into Docs agent: same pairing, but use `content_tools.report_template.render_html()` as the wrapper for any HTML deliverable (per HTML-over-Markdown rule).
- Single source of truth stays `content_tools/report_template.py`. The swarm reads from it via a small Python shim, never hardcodes hex.

## 8. Risks + dealbreakers
- **Sandbox dependency = paid SaaS.** If Open Swarm's data-analyst sandbox is `e2b.dev` (paid), we either run Docker locally on Oracle or fork that one agent. Verify before fork.
- **Port collision.** MCP fleet owns 3101-3107. n8n=5678, Blinko=1111, Django=8504, voice=8200. Swarm API server (if enabled) must bind to a free port (propose 3120 internal-only) and never expose publicly without nginx auth.
- **License edge case.** Need to confirm MIT (or BSD/Apache). If GPL, we cannot relicense the fork as Everlight-internal -- still usable but downstream fork rules change.
- **Token burn.** A single "investor pitch" run was 15 min in Julian's demo. At Anthropic Sonnet rates that is non-trivial; budget gate (step 5) is the hedge.
- **Composio absence = 80% of integration value gone.** Free tier exists -- check before assuming we lose it. If free tier suffices for Gmail+Slack+HubSpot read-only, opt in.
- **Operator Truth check:** until step-2 SSH preflight returns clean and step-1 license is verified MIT, this plan ships nothing.

---

**Status / Next Action / Owner / ETA**
DRAFT / Lucrex review + approve / Marquise / open
