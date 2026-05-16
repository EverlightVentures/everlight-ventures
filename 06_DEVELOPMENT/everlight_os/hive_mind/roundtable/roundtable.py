"""Hive Roundtable -- Solomon Vale's 5-phase persona orchestration engine.

Solomon convenes the room. He does not vote. He does not synthesize toward
consensus. He surfaces disagreement, names provenance, and hands the result
to Lucrex / Rich for the actual decision.

Phases:
  1. Open       -- each persona answers the question in parallel
  2. Cross-fire -- each persona reads peers, pushes back on 1-2 specific points
  3. Probe      -- Solomon picks the sharpest disagreement, asks all to address
  4. Synthesis  -- Solomon produces transcript + executive synthesis + dissents
  5. Publish    -- Branded Google Doc + Slack card + 08_BACKUPS archive

Constitutional guards:
  - eradication_gate.assert_safe() pre-flight (Streubel doctrine, fail-closed)
  - Justine Park's compliance veto is honored (any gate raise = hard abort)
  - hive_logger.start() canonical session log
  - publish_gdoc() = branded pipeline (no n8n, no raw API)
  - Anthropic SDK only -- no third-party AI vendor
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

# --- Workspace paths ---------------------------------------------------------
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
for candidate in (
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
):
    if candidate.exists():
        WORKSPACE = candidate
        break

AGENTS_DIR = WORKSPACE / ".claude" / "agents"
ROUNDTABLE_DIR = WORKSPACE / "06_DEVELOPMENT" / "everlight_os" / "hive_mind" / "roundtable"
GUESTS_DIR = ROUNDTABLE_DIR / "guests"
ARCHIVE_DIR = WORKSPACE / "08_BACKUPS" / "roundtables"
CONTENT_TOOLS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"

# --- content_tools imports (constitutional guards) --------------------------
if str(CONTENT_TOOLS) not in sys.path:
    sys.path.insert(0, str(CONTENT_TOOLS))

try:
    import eradication_gate  # type: ignore
    from eradication_gate import EradicationViolation  # type: ignore
except Exception as e:
    print(f"[roundtable] CRITICAL: eradication_gate unavailable ({e}). Refusing to run.", file=sys.stderr)
    raise

try:
    import hive_logger  # type: ignore
except Exception:
    hive_logger = None  # logging is best-effort, never blocks the run

try:
    from n8n_replacements import publish_gdoc  # type: ignore
except Exception:
    publish_gdoc = None

try:
    import branded_slack  # type: ignore
except Exception:
    branded_slack = None

# --- Constants ---------------------------------------------------------------
CLAUDE_MODEL = "claude-opus-4-7"        # primary model
CLAUDE_MODEL_LITE = "claude-haiku-4-5-20251001"  # cheap fallback if needed
SOLOMON_DOSSIER_PATH = AGENTS_DIR / "solomon_vale.md"


class RoundtableError(Exception):
    """Raised when the roundtable cannot proceed (compliance, persona missing, etc.)"""


# --- Persona loading ---------------------------------------------------------
def load_persona(name: str) -> dict[str, Any]:
    """Load a persona dossier from .claude/agents/ or roundtable/guests/.

    Search order:
      1. .claude/agents/{name}.md (named subagent format)
      2. roundtable/guests/{name}.md (generated guest)
      3. .claude/agents/*.md (numbered files matching by **Name:** field)
    """
    candidates = [
        AGENTS_DIR / f"{name}.md",
        GUESTS_DIR / f"{name}.md",
    ]
    for c in candidates:
        if c.exists():
            return {
                "key": name,
                "display_name": _extract_display_name(c.read_text(errors="ignore")) or name,
                "system_prompt": c.read_text(errors="ignore"),
                "source": str(c),
            }

    # Fallback: scan numbered dossiers by **Name:** match
    if AGENTS_DIR.exists():
        for f in sorted(AGENTS_DIR.glob("*.md")):
            txt = f.read_text(errors="ignore")
            if f"**Name:** {name}" in txt or f"name: {name}" in txt.lower():
                return {
                    "key": name,
                    "display_name": _extract_display_name(txt) or name,
                    "system_prompt": txt,
                    "source": str(f),
                }

    raise RoundtableError(
        f"No persona dossier found for {name!r}. "
        f"Looked in {AGENTS_DIR} and {GUESTS_DIR}."
    )


def _extract_display_name(dossier: str) -> str | None:
    """Pull the human-readable name from a dossier markdown."""
    m = re.search(r"\*\*Name:\*\*\s+([^\n]+)", dossier)
    if m:
        return m.group(1).strip()
    m = re.search(r"^name:\s+(\S+)", dossier, re.MULTILINE)
    if m:
        return m.group(1).strip().replace("_", " ").title()
    return None


# --- Constitutional guard ----------------------------------------------------
def _compliance_gate(question: str, context: str, participants: list[str]) -> None:
    """Run eradication_gate.assert_safe over every plausible identifier in the payload.

    This adapts the field-typed gate to the freeform-text reality of a roundtable
    input by extracting candidate emails / names / addresses from the question +
    context and asserting safety for each.
    """
    text = f"{question}\n\n{context}"

    # Hard halt env check
    if eradication_gate.outbound_halted():
        raise RoundtableError(
            "WHOLESALE_OUTBOUND_HALT=1 is active. Roundtable refused per Layer 1 gate."
        )

    # 1) Direct email scan
    for email in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        eradication_gate.assert_safe(email=email, caller="solomon_roundtable")

    # 2) Participants must not be eradicated subjects
    for p in participants:
        eradication_gate.assert_safe(name=p, caller="solomon_roundtable.participant")

    # 3) Substring scan against the hardcoded eradication list (find_hit handles this)
    #    We pass the full question as the name field -- find_hit does case-folded
    #    exact match, so this only catches a full subject-name match in the question.
    hit = eradication_gate.find_hit(name=question)
    if hit:
        raise RoundtableError(
            f"Eradication subject {hit['subject_name']!r} referenced in question. Refused."
        )


# --- Anthropic SDK with mock fallback ---------------------------------------
def _get_client():
    """Lazy import anthropic; return a real client OR raise with install hint."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RoundtableError(
            "anthropic SDK not installed. Run: pip install anthropic\n"
            "For phone-side smoke testing without spending tokens, pass --mock."
        )
    return anthropic.Anthropic()


def _persona_speak(client, persona: dict, prompt: str, prior_context: str = "", max_tokens: int = 1500) -> str:
    """Call Claude with the persona's dossier as the system prompt."""
    user_msg = f"{prior_context}\n\n---\n\n{prompt}" if prior_context else prompt
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=persona["system_prompt"],
        messages=[{"role": "user", "content": user_msg}],
    )
    return msg.content[0].text


def _mock_speak(persona: dict, prompt: str, prior_context: str = "", **_) -> str:
    """Canned response for smoke testing. NEVER use for real decisions."""
    name = persona["display_name"]
    return (
        f"[MOCK voice of {name}] On the question at hand, my read is: "
        f"prompt fingerprint = {hash(prompt) % 10000:04d}. "
        f"I would push back on any peer claiming this is simple. "
        f"My signature concern: {name.split()[0]}'s usual lane."
    )


# --- Phase 1: Open -----------------------------------------------------------
def _phase_open(speak_fn, client, question: str, context: str, personas: list[dict]) -> dict[str, str]:
    """Each persona gives an opening answer in parallel."""
    openings: dict[str, str] = {}
    prompt = (
        f"You are seated at a Hive Roundtable convened by Solomon Vale.\n\n"
        f"QUESTION: {question}\n\n"
        f"Give your opening answer in your own voice. Be concrete. Be brief "
        f"(under 250 words). Do not hedge. Speak as the persona you are."
    )
    with ThreadPoolExecutor(max_workers=max(2, len(personas))) as pool:
        futures = {
            pool.submit(speak_fn, client, p, prompt, context): p["display_name"]
            for p in personas
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                openings[name] = fut.result()
            except Exception as e:
                openings[name] = f"[error: persona failed to speak -- {e}]"
    return openings


# --- Phase 2: Cross-fire -----------------------------------------------------
def _phase_cross_fire(speak_fn, client, question: str, openings: dict[str, str], personas: list[dict]) -> dict[str, str]:
    """Each persona reads peers' openings and pushes back on 1-2 specific points."""
    cross_fire: dict[str, str] = {}

    def _run_for(persona):
        peers = "\n\n".join(
            f"**{n}:** {t}" for n, t in openings.items() if n != persona["display_name"]
        )
        prompt = (
            f"You opened the floor on: \"{question}\"\n\n"
            f"Your peers said:\n\n{peers}\n\n"
            f"Now: pick 1-2 specific points where you DISAGREE with a peer "
            f"(cite the peer by name). If you fully agree, say so plainly and "
            f"add one consideration nobody named. No performative disagreement. "
            f"No consensus theater. Under 200 words."
        )
        return speak_fn(client, persona, prompt, "")

    with ThreadPoolExecutor(max_workers=max(2, len(personas))) as pool:
        futures = {pool.submit(_run_for, p): p["display_name"] for p in personas}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                cross_fire[name] = fut.result()
            except Exception as e:
                cross_fire[name] = f"[error in cross-fire -- {e}]"
    return cross_fire


# --- Phase 3: Probe ----------------------------------------------------------
def _phase_probe(speak_fn, client, question, openings, cross_fire, personas, solomon_dossier):
    """Solomon picks the sharpest disagreement, then each persona answers his probe."""
    transcript_so_far = _format_transcript(openings, cross_fire)

    pick_prompt = (
        f"The roundtable so far:\n\n{transcript_so_far}\n\n"
        f"Identify the SHARPEST disagreement the room has NOT resolved. State it in "
        f"one sentence, naming the two opposing participants. Then write a single "
        f"probe question that forces everyone to confront it head-on.\n\n"
        f"Output format (use these literal headers):\n"
        f"SHARPEST DISAGREEMENT: <one sentence, name the two participants>\n"
        f"PROBE QUESTION: <a single question for everyone>"
    )

    solomon_persona = {"display_name": "Solomon Vale", "system_prompt": solomon_dossier}
    raw_pick = speak_fn(client, solomon_persona, pick_prompt, "", max_tokens=400)

    # Extract probe question
    probe_question = ""
    for line in raw_pick.split("\n"):
        if line.strip().upper().startswith("PROBE QUESTION:"):
            probe_question = line.split(":", 1)[1].strip()
            break
    if not probe_question:
        probe_question = "Sharpen your position in one sentence. What's the consequence if you're wrong?"

    # All personas answer the probe in parallel
    probe_prompt = (
        f"Solomon's probe: {probe_question}\n\n"
        f"Answer in one tight paragraph. Under 150 words."
    )
    answers: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(2, len(personas))) as pool:
        futures = {
            pool.submit(speak_fn, client, p, probe_prompt, transcript_so_far): p["display_name"]
            for p in personas
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                answers[name] = fut.result()
            except Exception as e:
                answers[name] = f"[error answering probe -- {e}]"

    return {"solomon_pick": raw_pick, "probe_question": probe_question, "answers": answers}


# --- Phase 4: Synthesis ------------------------------------------------------
def _phase_synthesis(speak_fn, client, question, openings, cross_fire, probe, solomon_dossier):
    """Solomon produces transcript + executive synthesis + unresolved disagreements."""
    full_transcript = _format_transcript(openings, cross_fire, probe=probe)
    solomon_persona = {"display_name": "Solomon Vale", "system_prompt": solomon_dossier}

    synth_prompt = (
        f"QUESTION: {question}\n\n"
        f"FULL TRANSCRIPT:\n\n{full_transcript}\n\n"
        f"You will now produce THREE sections, in this order, using EXACTLY these "
        f"markdown headers:\n\n"
        f"## TRANSCRIPT\n"
        f"Voice-by-voice debate, each participant's contributions grouped under "
        f"their name. PRESERVE VOICE. No synthesis here.\n\n"
        f"## EXECUTIVE SYNTHESIS\n"
        f"The merged read: what the group converged on, the actionable decision, "
        f"and who contributed which idea (provenance cited inline). No "
        f"consensus-bias -- if a dissent is real, name it inside the synthesis.\n\n"
        f"## UNRESOLVED DISAGREEMENTS\n"
        f"List every disagreement that did NOT resolve as bullet points. For each: "
        f"who disagreed with whom, and on what. If none, write a single bullet: "
        f"\"- None unresolved.\"\n\n"
        f"Sign the synthesis section with: -- Solomon Vale, 1962 Parker 51"
    )

    raw = speak_fn(client, solomon_persona, synth_prompt, "", max_tokens=4000)

    transcript_section = _extract_section(raw, "TRANSCRIPT", "EXECUTIVE SYNTHESIS") or full_transcript
    synthesis_section = _extract_section(raw, "EXECUTIVE SYNTHESIS", "UNRESOLVED DISAGREEMENTS") or raw
    disagreements_section = _extract_section(raw, "UNRESOLVED DISAGREEMENTS", None) or ""

    disagreements = []
    for line in disagreements_section.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "*")) or re.match(r"^\d+\.\s", line):
            cleaned = re.sub(r"^[\-\*\d\.]\s*", "", line).strip()
            if cleaned and "none unresolved" not in cleaned.lower():
                disagreements.append(cleaned)

    return {
        "transcript": transcript_section,
        "synthesis": synthesis_section,
        "disagreements": disagreements,
        "raw": raw,
    }


# --- Phase 5: Publish + Archive ---------------------------------------------
def _publish_branded(result: dict, channel: str, smoke_test: bool) -> dict:
    """Publish to Google Doc via the branded pipeline, fall back to direct Slack post."""
    title_prefix = "[SMOKE TEST] " if smoke_test else ""
    title = f"{title_prefix}Hive Roundtable: {result['question'][:80]}"

    body_md = _format_full_report(result, smoke_test=smoke_test)
    summary = (
        f"{len(result['participants'])} voices, "
        f"{len(result['disagreements'])} unresolved dissents. "
        f"Convened by Solomon Vale."
    )

    info: dict[str, Any] = {"smoke_test": smoke_test}

    if publish_gdoc is None:
        info["publish_error"] = "publish_gdoc unavailable in this environment"
    else:
        try:
            r = publish_gdoc(
                title=title,
                body=body_md,
                channel=channel,
                folder_key="ai_hive",
                summary=summary,
                extra_meta={
                    "Convener": "Solomon Vale",
                    "Participants": ", ".join(result["participants"]),
                    "Unresolved Disagreements": str(len(result["disagreements"])),
                    "Mode": "smoke test" if smoke_test else "live",
                },
            )
            if isinstance(r, dict):
                info.update({
                    "doc_url": r.get("doc_link"),
                    "html_url": r.get("html_link"),
                    "slack_ts": r.get("slack_ts"),
                    "publish_ok": r.get("ok"),
                    "publish_error": r.get("error"),
                })
        except Exception as e:
            info["publish_error"] = f"publish_gdoc exception: {e}"

    # If branded pipeline failed, try a direct branded Slack post as fallback
    if branded_slack and not info.get("slack_ts"):
        try:
            slack_r = branded_slack.post_branded_slack(
                channel=channel,
                title=title,
                summary=summary,
                body=result["synthesis"][:1500],
                fields={
                    "Participants": str(len(result["participants"])),
                    "Disagreements": str(len(result["disagreements"])),
                    "Mode": "smoke test" if smoke_test else "live",
                },
                agent_name="Solomon Vale",
                agent_title="Roundtable Convener",
                category="report",
            )
            if isinstance(slack_r, dict):
                info["slack_ts"] = slack_r.get("ts")
                info["slack_fallback"] = True
        except Exception as e:
            info["slack_error"] = f"branded_slack exception: {e}"

    return info


def _archive_transcript(result: dict) -> str:
    """Always archive to 08_BACKUPS/roundtables/ per the no-trash doctrine."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug(result["question"])
    fname = f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_{slug}.md"
    fpath = ARCHIVE_DIR / fname
    fpath.write_text(_format_full_report(result, smoke_test=bool(result.get("smoke_test")), archive=True))
    return str(fpath)


# --- Formatting helpers ------------------------------------------------------
def _format_transcript(openings, cross_fire, probe=None) -> str:
    out: list[str] = ["## Phase 1 -- Opening Statements", ""]
    for name, text in openings.items():
        out.extend([f"### {name}", text, ""])

    out.extend(["## Phase 2 -- Cross-Fire", ""])
    for name, text in cross_fire.items():
        out.extend([f"### {name}", text, ""])

    if probe:
        out.extend([
            "## Phase 3 -- Probe",
            "",
            f"**Solomon's pick:** {probe['solomon_pick']}",
            "",
            f"**Probe question:** {probe['probe_question']}",
            "",
        ])
        for name, text in probe["answers"].items():
            out.extend([f"### {name}", text, ""])

    return "\n".join(out)


def _format_full_report(result: dict, smoke_test: bool = False, archive: bool = False) -> str:
    header_prefix = "[SMOKE TEST] " if smoke_test else ""
    archive_note = "\n\n*Archived to 08_BACKUPS/roundtables/ per no-trash doctrine.*" if archive else ""
    dissent_md = "\n".join(f"- {d}" for d in result["disagreements"]) or "- None unresolved."

    # Routing block -- documents WHY this team was composed
    routing = result.get("routing", {})
    routing_block = ""
    if routing.get("auto_routed"):
        composition_md = "\n".join(
            f"- {a} [{src}]" for a, src in routing.get("composition", [])
        ) or "- (composition unavailable)"
        dropped_md = ""
        if routing.get("dropped"):
            dropped_md = "\n\n**Dropped by max_participants cap:**\n" + "\n".join(
                f"- {a} [{reason}]" for a, reason in routing["dropped"]
            )
        routing_block = f"""---

## Routing & Composition

**Process:** `{routing.get('process', '?')}`
**State injection:** {routing.get('detected_state') or '_none_'}
**Topic triggers:** {', '.join(routing.get('detected_topics', [])) or '_none_'}
**Classifier confidence:** {routing.get('confidence', '?')}

**Seated (in order):**
{composition_md}{dropped_md}

"""
    elif routing.get("manual_participants"):
        routing_block = "---\n\n## Routing & Composition\n\n**Manual participant list** (auto-routing not used).\n\n"

    return f"""# {header_prefix}Hive Roundtable

**Question:** {result['question']}

**Participants:** {', '.join(result['participants'])}
**Convened by:** Solomon Vale, Roundtable Convener
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M PT')}
**Mode:** {'SMOKE TEST -- no real stakes' if smoke_test else 'Live'}

{routing_block}---

## Transcript (voice-by-voice)

{result['transcript']}

---

## Executive Synthesis

{result['synthesis']}

---

## Unresolved Disagreements

{dissent_md}

---

*Convened by Solomon Vale. Transcript preserved per the Article III standard: no consensus theater, no sanitized synthesis. -- 1962 Parker 51*{archive_note}
"""


def _extract_section(text: str, start_marker: str, end_marker: str | None) -> str:
    """Pull the block between two markdown headers (## STARTS).Header detection is permissive (## or ### or **bold**)."""
    lines = text.split("\n")
    start_re = re.compile(rf"^\s*(#+|\*\*).*{re.escape(start_marker)}", re.IGNORECASE)
    end_re = re.compile(rf"^\s*(#+|\*\*).*{re.escape(end_marker)}", re.IGNORECASE) if end_marker else None
    in_block = False
    out: list[str] = []
    for line in lines:
        if start_re.search(line):
            in_block = True
            continue
        if in_block and end_re and end_re.search(line):
            break
        if in_block:
            out.append(line)
    return "\n".join(out).strip()


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "untitled"


# --- Main entry point -------------------------------------------------------
def roundtable(
    question: str,
    participants: list[str] | None = None,
    process: str | None = None,
    state: str | None = None,
    severity: str = "normal",
    extras: list[str] | None = None,
    excludes: list[str] | None = None,
    context: str = "",
    channel: str = "#war-room",
    publish: bool = True,
    smoke_test: bool = False,
    mock: bool = False,
) -> dict[str, Any]:
    """Run a 5-phase Hive Roundtable convened by Solomon Vale.

    Banking-committee model: pick the right team automatically based on the
    process being discussed (auto-routing), with state-pair injections and
    topic-keyword additions. Manual participant lists still work for one-off
    cases.

    Args:
        question: The single sharp question to debate.
        participants: Optional explicit list of persona keys. If None or empty,
                      the resolver auto-composes the team from `process` (or
                      auto-classifies if process is also None).
        process: Process template key (e.g., 'dnc_post_mortem', 'wholesale_deal_review').
                 If None and participants is also None, the classifier picks one
                 from the question text.
        state: Optional 2-letter state code (MO, TN, GA, OH, AZ, TX, FL) to
               trigger state-pair injection. Auto-detected from question if not
               provided.
        severity: 'normal' | 'high' | 'critical' -- triggers escalation seats
                  (e.g., Vaughn Sterling for high-stakes calls).
        extras: Solomon's chair-discretion additions (always seated, bypass cap).
        excludes: Agents to recuse / exclude (conflict of interest).
        context: Optional context (deal sheet, market data, prior session refs).
        channel: Slack channel for the branded result card.
        publish: If False, skip Google Doc + Slack publish (archive still runs).
        smoke_test: Marks the run as a smoke test (title prefix).
        mock: Use canned responses instead of real Anthropic API calls.

    Returns:
        Dict with: question, participants, transcript, synthesis, disagreements,
        doc_url, slack_ts, archive_path, errors, routing (process + composition).

    Raises:
        RoundtableError: on compliance gate failure, missing persona, or
                         missing critical dependency.
    """
    # Auto-routing: if no explicit participants, run the classifier + resolver
    routing_info: dict[str, Any] = {}
    if not participants:
        try:
            from .participant_resolver import classify, resolve
        except ImportError:
            # Support running this file directly
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from roundtable.participant_resolver import classify, resolve  # type: ignore

        hints = {}
        if process: hints["process"] = process
        if state: hints["state"] = state
        if severity: hints["severity"] = severity

        picked_process, classified_hints = classify(question, hints)
        resolved = resolve(
            process=picked_process,
            state=classified_hints.get("state"),
            topics=classified_hints.get("topics", []),
            severity=classified_hints.get("severity", "normal"),
            extras=extras,
            excludes=excludes,
        )
        participants = resolved["participants"]
        routing_info = {
            "auto_routed": True,
            "process": picked_process,
            "detected_state": classified_hints.get("state"),
            "detected_topics": classified_hints.get("topics", []),
            "confidence": classified_hints.get("confidence"),
            "composition": resolved["composition"],
            "dropped": resolved["dropped"],
            "rationale": resolved["rationale"],
        }

    # Constitutional gate (HARD LAW: Streubel doctrine, fail-closed)
    _compliance_gate(question, context, participants)

    # Load Solomon's dossier (required)
    if not SOLOMON_DOSSIER_PATH.exists():
        raise RoundtableError(
            f"Solomon Vale dossier missing at {SOLOMON_DOSSIER_PATH}. "
            f"This roundtable cannot convene without its convener."
        )
    solomon_dossier = SOLOMON_DOSSIER_PATH.read_text()

    # Load every participant persona
    personas = [load_persona(p) for p in participants]
    if len(personas) < 2:
        raise RoundtableError(
            f"A roundtable requires at least 2 voices. Got {len(personas)}."
        )

    # Pick the speak function (real SDK vs mock)
    if mock:
        speak_fn = lambda client, p, prompt, ctx="", **kw: _mock_speak(p, prompt, ctx, **kw)
        client = None
    else:
        client = _get_client()
        speak_fn = _persona_speak

    # Canonical session logger
    run = None
    if hive_logger:
        try:
            run = hive_logger.start(
                agent="solomon_vale",
                task=f"roundtable-{_slug(question)}",
                inputs={
                    "question": question[:300],
                    "participants": participants,
                    "smoke_test": smoke_test,
                    "mock": mock,
                },
                tags=["#hive/session", "#hive/roundtable", "#hive/judiciary"],
            )
        except Exception:
            pass

    started_at = time.time()
    errors: list[str] = []

    # Phase 1: Open
    openings = _phase_open(speak_fn, client, question, context, personas)

    # Phase 2: Cross-fire
    cross_fire = _phase_cross_fire(speak_fn, client, question, openings, personas)

    # Phase 3: Probe
    probe = _phase_probe(speak_fn, client, question, openings, cross_fire, personas, solomon_dossier)

    # Phase 4: Synthesis
    synthesis = _phase_synthesis(speak_fn, client, question, openings, cross_fire, probe, solomon_dossier)

    result = {
        "question": question,
        "participants": [p["display_name"] for p in personas],
        "participant_keys": participants,
        "transcript": synthesis["transcript"],
        "synthesis": synthesis["synthesis"],
        "disagreements": synthesis["disagreements"],
        "smoke_test": smoke_test,
        "mock": mock,
        "elapsed_s": round(time.time() - started_at, 1),
        "errors": errors,
        "routing": routing_info or {"auto_routed": False, "manual_participants": True},
    }

    # Phase 5: Publish + always-archive
    if publish and not mock:
        try:
            publish_info = _publish_branded(result, channel=channel, smoke_test=smoke_test)
            result.update(publish_info)
        except Exception as e:
            result["publish_error"] = str(e)
            errors.append(f"publish: {e}")

    try:
        result["archive_path"] = _archive_transcript(result)
    except Exception as e:
        errors.append(f"archive: {e}")

    # Close the logger
    if run:
        try:
            run.finish(
                status="done" if not errors else "partial",
                summary=(
                    f"Roundtable: {len(personas)} voices, "
                    f"{len(synthesis['disagreements'])} unresolved. "
                    f"Errors: {len(errors)}."
                )[:500],
            )
        except Exception:
            pass

    return result


# --- CLI ---------------------------------------------------------------------
def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Hive Roundtable -- Solomon Vale's 5-phase persona orchestration",
    )
    parser.add_argument("question", help="The question to debate")
    parser.add_argument(
        "--participants", "-p", nargs="+",
        help="Explicit persona keys (skips auto-routing). e.g., piper_reeves marvin_cohen",
    )
    parser.add_argument(
        "--process",
        help="Process template key (e.g., dnc_post_mortem, wholesale_deal_review). Skips classifier.",
    )
    parser.add_argument(
        "--state", help="2-letter state code (MO, TN, GA, OH, AZ, TX, FL) for state-pair injection",
    )
    parser.add_argument(
        "--severity", default="normal", choices=["normal", "high", "critical"],
        help="Severity level -- triggers escalation seats (e.g., Vaughn Sterling at 'high')",
    )
    parser.add_argument(
        "--extras", "-x", nargs="*", help="Chair-discretion additions (always seated)",
    )
    parser.add_argument(
        "--excludes", "-e", nargs="*", help="Recusal / conflict-of-interest exclusions",
    )
    parser.add_argument("--context", "-c", default="", help="Optional context block")
    parser.add_argument("--channel", default="#war-room", help="Slack channel for result card")
    parser.add_argument("--no-publish", action="store_true", help="Skip Google Doc + Slack publish")
    parser.add_argument(
        "--smoke-test", action="store_true",
        help="Mark as smoke test (prefixes title, no real-stakes flag)",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use canned responses (orchestration validation only -- DO NOT use for real decisions)",
    )
    parser.add_argument(
        "--show-routing", action="store_true",
        help="Print the auto-routing decision and exit (no roundtable runs)",
    )
    parser.add_argument("--json", action="store_true", help="Print full result as JSON")
    args = parser.parse_args()

    # Quick routing preview (no LLM calls)
    if args.show_routing:
        try:
            from .participant_resolver import classify, resolve
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from roundtable.participant_resolver import classify, resolve  # type: ignore
        hints = {}
        if args.process: hints["process"] = args.process
        if args.state: hints["state"] = args.state
        if args.severity: hints["severity"] = args.severity
        try:
            picked, h = classify(args.question, hints)
            r = resolve(
                process=picked,
                state=h.get("state"),
                topics=h.get("topics", []),
                severity=h.get("severity", "normal"),
                extras=args.extras,
                excludes=args.excludes,
            )
            print(f"Process: {picked}")
            print(f"Confidence: {h.get('confidence')}")
            print(f"All scores: {h.get('all_scores')}")
            print()
            print(r["rationale"])
        except Exception as e:
            print(f"[routing] {e}", file=sys.stderr)
            return 2
        return 0

    try:
        result = roundtable(
            question=args.question,
            participants=args.participants,
            process=args.process,
            state=args.state,
            severity=args.severity,
            extras=args.extras,
            excludes=args.excludes,
            context=args.context,
            channel=args.channel,
            publish=not args.no_publish,
            smoke_test=args.smoke_test,
            mock=args.mock,
        )
    except RoundtableError as e:
        print(f"[roundtable] {e}", file=sys.stderr)
        return 2
    except EradicationViolation as e:
        print(f"[roundtable] ERADICATION VIOLATION: {e}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Question: {result['question']}")
        print(f"Participants: {', '.join(result['participants'])}")
        print(f"Elapsed: {result['elapsed_s']}s")
        print(f"Unresolved disagreements: {len(result['disagreements'])}")
        if result.get("doc_url"):
            print(f"Google Doc: {result['doc_url']}")
        if result.get("archive_path"):
            print(f"Archived to: {result['archive_path']}")
        if result.get("errors"):
            print(f"Errors: {result['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
