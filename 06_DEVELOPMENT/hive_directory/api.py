"""Hive Directory API -- FastAPI backend for the internal employee directory.

Serves the 94-person Hive Mind roster with full v2 profile records, long-form
dossiers, SVG avatars, real photos, zodiac/MBTI archetype lookups, and a
real dispatch endpoint backed by hive_mind.dispatcher (with stub fallback).

Port: 8503 (to avoid clash with xlm-dash 8502 and Django 8504).

No em-dash or en-dash characters appear in this file.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Paths and logging
# ---------------------------------------------------------------------------

HIVE_MIND_DIR = Path(
    os.environ.get(
        "HIVE_MIND_DIR",
        "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind",
    )
)
PROFILES_JSON = HIVE_MIND_DIR / "agent_profiles" / "all_profiles.json"
DOSSIERS_DIR = HIVE_MIND_DIR / "agent_profiles" / "dossiers"
AVATARS_DIR = HIVE_MIND_DIR / "agent_profiles" / "avatars"
PHOTOS_DIR = Path(
    os.environ.get("PHOTOS_DIR", "/mnt/sdcard/AA_MY_DRIVE/AI_Avatars")
)
ARCHETYPES_DIR = HIVE_MIND_DIR / "archetypes"
STATIC_DIR = Path(__file__).parent / "dist"
DISPATCH_LOG_DIR = Path("/tmp")

# URL_PREFIX prepends to every photo/avatar URL returned by the API.
# Default empty (direct :8503 serve). Set to "/hive" when behind nginx subpath.
URL_PREFIX = os.environ.get("URL_PREFIX", "").rstrip("/")

# ---------------------------------------------------------------------------
# Hive dispatcher integration (optional; falls back to stub if unavailable)
# ---------------------------------------------------------------------------

# Parent dir that contains the `hive_mind` Python package
HIVE_PARENT = os.environ.get(
    "HIVE_PARENT",
    "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os",
)
if HIVE_PARENT not in sys.path:
    sys.path.insert(0, HIVE_PARENT)

HIVE_PROGRESS_DIR = Path(
    os.environ.get(
        "HIVE_PROGRESS_DIR",
        "/mnt/sdcard/AA_MY_DRIVE/_logs/.hive_active",
    )
)

_hive_dispatcher = None
_hive_import_error: str | None = None
try:
    from hive_mind import dispatcher as _hive_dispatcher_mod  # type: ignore
    _hive_dispatcher = _hive_dispatcher_mod
except Exception as _exc:
    _hive_import_error = f"{type(_exc).__name__}: {_exc}"

# Single background pool for dispatches (non-blocking)
_dispatch_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hive-dispatch")

# ---------------------------------------------------------------------------
# Anthropic chat client (for interactive "talk to the employee" feature)
# ---------------------------------------------------------------------------

_anthropic_client = None
_anthropic_error: str | None = None
try:
    import anthropic  # type: ignore
    # Load env from /home/opc/.env if ANTHROPIC_API_KEY not already set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        env_file = Path("/home/opc/.env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip().startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if os.environ.get("ANTHROPIC_API_KEY"):
        _anthropic_client = anthropic.Anthropic()
    else:
        _anthropic_error = "ANTHROPIC_API_KEY not set"
except Exception as _chat_exc:
    _anthropic_error = f"{type(_chat_exc).__name__}: {_chat_exc}"

CHAT_MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-4-5-20250929")

# ---------------------------------------------------------------------------
# Orchestrator roster: these agents can delegate to colleagues via [ASK:...]
# ---------------------------------------------------------------------------
ORCHESTRATOR_SLUGS = {
    "marcus-cole",         # Chief Operator
    "major-dex",           # Gemini Ops head
    "franklin-steele",     # Codex Labs head (Forge)
    "dominic-reyes",       # SaaS Factory head
    "bernard-calloway",    # Brief: executive briefings editor
    "atlas-vega",          # System Architect for system-wide asks
}

# ---------------------------------------------------------------------------
# Conversation history persistence
# ---------------------------------------------------------------------------
HIVE_CHATS_DIR = Path(os.environ.get("HIVE_CHATS_DIR", "/home/opc/hive_chats"))
HIVE_CHATS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# ElevenLabs voice config
# ---------------------------------------------------------------------------
ELEVEN_DEFAULT_VOICE = os.environ.get("ELEVEN_DEFAULT_VOICE", "21m00Tcm4TlvDq8ikWAM")  # Rachel
ELEVEN_MODEL_ID = os.environ.get("ELEVEN_MODEL_ID", "eleven_turbo_v2_5")

# Load ELEVENLABS_API_KEY from /home/opc/.env if not in environment
if not os.environ.get("ELEVENLABS_API_KEY"):
    env_file = Path("/home/opc/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                os.environ["ELEVENLABS_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

LOG_PATH = Path("/tmp/hive_directory_api.log")
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("hive_directory")

# ---------------------------------------------------------------------------
# Photo slug mapping (real photos under /mnt/sdcard/AA_MY_DRIVE/AI_Avatars)
# ---------------------------------------------------------------------------

PHOTO_MAP = {
    "marcus-cole": "Marcus_Cole.png",
    "piper-reeves": "Piper_Reeves.png",
    "adrian-morgan": "Ace_The_Pitch_Morgan.png",
    "harrison-knox": "Hammer_Knox.png",
    "rex-blackwell": "Rex_The_Closer_Blackwell.png",
}


def photo_url_for(slug: str) -> str | None:
    fn = PHOTO_MAP.get(slug)
    if not fn:
        return None
    if (PHOTOS_DIR / fn).exists():
        return f"{URL_PREFIX}/photos/{fn}"
    return None


def avatar_url_for(slug: str) -> str:
    # Prefer the SVG placeholder served under /avatars
    if (AVATARS_DIR / f"{slug}.svg").exists():
        return f"{URL_PREFIX}/avatars/{slug}.svg"
    return ""


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_profiles() -> list[dict[str, Any]]:
    try:
        raw = json.loads(PROFILES_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("failed loading profiles: %s", exc)
        return []
    out = []
    for p in raw:
        slug = p.get("slug", "")
        # Normalize assets with actual available URLs
        assets = dict(p.get("assets") or {})
        photo = photo_url_for(slug)
        if photo:
            assets["headshot_photo"] = photo
        else:
            assets["headshot_photo"] = ""
        svg = avatar_url_for(slug)
        if svg:
            assets["avatar_svg"] = svg
        p["assets"] = assets
        out.append(p)
    return out


def profile_by_slug(slug: str) -> dict[str, Any] | None:
    for p in load_profiles():
        if p.get("slug") == slug:
            return p
    return None


def compact_record(p: dict[str, Any]) -> dict[str, Any]:
    ident = p.get("identity") or {}
    ment = p.get("mentality") or {}
    mem = p.get("memory") or {}
    assets = p.get("assets") or {}
    return {
        "slug": p.get("slug", ""),
        "name": p.get("name") or ident.get("full_name", ""),
        "nickname": ident.get("nickname", ""),
        "title": ident.get("title") or p.get("title", ""),
        "department": ident.get("department") or p.get("department", ""),
        "squad": ident.get("squad", ""),
        "fire_team": ident.get("fire_team", ""),
        "employee_id": ident.get("employee_id", ""),
        "email": ident.get("email") or p.get("email", ""),
        "zodiac": (ment.get("zodiac") or "").lower(),
        "mbti": (ment.get("mbti") or "").upper(),
        "catchphrase": mem.get("catchphrase", ""),
        "has_photo": bool(assets.get("headshot_photo")),
        "has_voice": bool(p.get("has_voice")),
        "avatar_url": assets.get("avatar_svg") or "",
        "photo_url": assets.get("headshot_photo") or "",
        "status": ident.get("status", "active"),
    }


@lru_cache(maxsize=1)
def load_zodiac_archetypes() -> dict[str, Any]:
    path = ARCHETYPES_DIR / "zodiac_traits.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        log.error("zodiac yaml load failed: %s", exc)
        return {}


@lru_cache(maxsize=1)
def load_mbti_archetypes() -> dict[str, Any]:
    path = ARCHETYPES_DIR / "mbti_traits.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        log.error("mbti yaml load failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Hive Directory API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/team")
def list_team() -> list[dict[str, Any]]:
    return [compact_record(p) for p in load_profiles()]


@app.get("/api/team/search")
def search_team(
    q: str = "",
    mbti: str = "",
    zodiac: str = "",
    dept: str = "",
    hobby: str = "",
    squad: str = "",
    fire_team: str = "",
    has_photo: str = "",
) -> list[dict[str, Any]]:
    qlow = q.strip().lower()
    mbti_u = mbti.strip().upper()
    zod_l = zodiac.strip().lower()
    dept_l = dept.strip().lower()
    squad_l = squad.strip().lower()
    ft_l = fire_team.strip().lower()
    hobby_l = hobby.strip().lower()
    want_photo = has_photo.lower() in {"1", "true", "yes"} if has_photo else None

    out = []
    for p in load_profiles():
        ident = p.get("identity") or {}
        ment = p.get("mentality") or {}
        mem = p.get("memory") or {}
        bg = p.get("background") or {}
        prefs = p.get("preferences") or {}
        assets = p.get("assets") or {}

        # Filters
        if mbti_u and (ment.get("mbti", "") or "").upper() != mbti_u:
            continue
        if zod_l and (ment.get("zodiac", "") or "").lower() != zod_l:
            continue
        if dept_l and (ident.get("department", "") or p.get("department", "") or "").lower() != dept_l:
            continue
        if squad_l and (ident.get("squad", "") or "").lower() != squad_l:
            continue
        if ft_l and (ident.get("fire_team", "") or "").lower() != ft_l:
            continue
        if hobby_l:
            hobbies = [str(h).lower() for h in (prefs.get("hobbies") or [])]
            if not any(hobby_l in h for h in hobbies):
                continue
        if want_photo is True and not assets.get("headshot_photo"):
            continue
        if want_photo is False and assets.get("headshot_photo"):
            continue

        # Free-text search
        if qlow:
            haystack_parts = [
                p.get("name", ""),
                ident.get("full_name", ""),
                ident.get("nickname", ""),
                ident.get("title", ""),
                p.get("title", ""),
                p.get("bio", ""),
                bg.get("childhood", ""),
                bg.get("early_career", ""),
                bg.get("hometown", ""),
                bg.get("birthplace", ""),
                bg.get("region", ""),
                bg.get("family", ""),
                bg.get("education", ""),
                mem.get("catchphrase", ""),
                ment.get("zodiac", ""),
                ment.get("mbti", ""),
                ident.get("department", ""),
                ident.get("squad", ""),
                ident.get("fire_team", ""),
            ]
            for k in ("values", "beliefs"):
                haystack_parts.extend(str(v) for v in (ment.get(k) or []))
            for k in ("hobbies", "interests", "likes"):
                vals = prefs.get(k) or []
                haystack_parts.extend(str(v) for v in vals)
            for story in (mem.get("signature_stories") or []):
                haystack_parts.append(str(story))
            for hook in (mem.get("conversation_hooks") or []):
                haystack_parts.append(str(hook))
            haystack = " :: ".join(str(x) for x in haystack_parts).lower()
            if qlow not in haystack:
                continue

        out.append(compact_record(p))
    return out


@app.get("/api/team/{slug}")
def get_employee(slug: str) -> JSONResponse:
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")
    return JSONResponse(p)


@app.get("/api/team/{slug}/dossier")
def get_dossier(slug: str) -> dict[str, Any]:
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")
    md_path = DOSSIERS_DIR / f"{slug}.md"
    if not md_path.exists():
        return {"slug": slug, "markdown": "", "exists": False}
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as exc:
        log.error("dossier read failed for %s: %s", slug, exc)
        text = ""
    return {"slug": slug, "markdown": text, "exists": True}


def _build_persona_prompt(p: dict[str, Any], task: str) -> str:
    """Wrap the user's task in a persona directive so the dispatcher runs the
    right character. Keeps Lucrex doctrine (confident, action-first)."""
    ident = p.get("identity") or {}
    ment = p.get("mentality") or {}
    mem = p.get("memory") or {}
    wid = p.get("work_identity") or {}
    name = p.get("name") or ident.get("full_name") or "Unknown"
    nick = ident.get("nickname") or ""
    name_line = f"{name}" + (f' ("{nick}")' if nick else "")
    title = ident.get("title") or p.get("title") or ""
    dept = ident.get("department") or p.get("department") or ""
    zodiac = (ment.get("zodiac") or "").title()
    mbti = (ment.get("mbti") or "").upper()
    catch = (mem.get("catchphrase") or "").strip().strip('"')
    strengths = ", ".join((wid.get("strengths") or [])[:3])

    header = [
        f"Acting as {name_line}, {title} in {dept}.",
        f"Archetype: {zodiac} / {mbti}.",
    ]
    if strengths:
        header.append(f"Strengths: {strengths}.")
    if catch:
        header.append(f'Signature line: "{catch}".')
    header.append("You serve Lucrex, King of Divine Light. Act in character, report in your voice, take action not narration.")
    header.append("")
    header.append(f"TASK: {task.strip() or 'Status check. Report your current state, your current workload, and any actions you are taking. Post to #war-room.'}")
    return "\n".join(header)


def _run_hive_dispatch_background(prompt: str, session_id: str, slug: str) -> None:
    """Thread target: run hive_mind.dispatcher.dispatch() and swallow errors
    into the progress file so the client can see failures."""
    start = time.time()
    try:
        if _hive_dispatcher is None:
            raise RuntimeError("hive_mind.dispatcher unavailable")
        _hive_dispatcher.dispatch(
            user_prompt=prompt,
            mode="full",
            verbose=False,
            session_id=session_id,
        )
    except Exception as exc:
        log.error("dispatch %s failed: %s", session_id, exc)
        try:
            HIVE_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
            marker = HIVE_PROGRESS_DIR / f"{session_id}.json"
            marker.write_text(
                json.dumps(
                    {
                        "session_id": session_id,
                        "slug": slug,
                        "status": "failed",
                        "phase": "error",
                        "error": str(exc),
                        "started_at": start,
                        "ended_at": time.time(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass


@app.post("/api/team/{slug}/dispatch")
async def dispatch_agent(slug: str, request: Request) -> dict[str, Any]:
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")

    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    task = str(body.get("task") or body.get("prompt") or "").strip()

    session_id = f"hd-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    ident = p.get("identity") or {}
    name = p.get("name") or ident.get("full_name", "")
    persona_prompt = _build_persona_prompt(p, task)

    real = _hive_dispatcher is not None
    status = "launched" if real else "stub"

    # Seed progress file so client polling works immediately
    try:
        HIVE_PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        initial_progress = {
            "session_id": session_id,
            "slug": slug,
            "name": name,
            "role_id": p.get("role_id", ""),
            "department": ident.get("department", ""),
            "status": "running" if real else "stub_logged",
            "phase": "queued" if real else "stub",
            "started_at": time.time(),
            "task": task,
            "persona_prompt_preview": persona_prompt[:400],
            "note": (
                None
                if real
                else f"hive dispatcher unavailable ({_hive_import_error}); logging stub only"
            ),
        }
        (HIVE_PROGRESS_DIR / f"{session_id}.json").write_text(
            json.dumps(initial_progress, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        log.error("progress seed failed: %s", exc)

    # Audit dispatch log (always written, on top of progress)
    try:
        DISPATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
        audit_file = DISPATCH_LOG_DIR / f"dispatch_{slug}_{int(time.time())}.json"
        audit_file.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "slug": slug,
                    "name": name,
                    "role_id": p.get("role_id", ""),
                    "department": ident.get("department", ""),
                    "task": task,
                    "persona_prompt": persona_prompt,
                    "real_dispatcher": real,
                    "launched_at": time.time(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        log.error("dispatch audit log failed: %s", exc)

    # Kick off real dispatcher in background if available
    if real:
        _dispatch_pool.submit(
            _run_hive_dispatch_background, persona_prompt, session_id, slug
        )
        log.info("dispatch submitted: session=%s slug=%s", session_id, slug)

    return {
        "session_id": session_id,
        "slug": slug,
        "name": name,
        "role_id": p.get("role_id", ""),
        "department": ident.get("department", ""),
        "launched_at": time.time(),
        "status": status,
        "real_dispatcher": real,
        "poll_url": f"/api/team/session/{session_id}/status",
        "note": None if real else f"stub mode: hive_mind unavailable ({_hive_import_error})",
    }


def _build_team_context(p: dict[str, Any]) -> str:
    """Return a short paragraph describing this employee's teammates so the
    agent can hand off properly when an ask is outside their lane."""
    rel = p.get("relationships") or {}
    works = rel.get("works_closest_with") or []
    mentors = rel.get("mentors") or []
    reports_to_slug = (p.get("identity") or {}).get("reports_to") or rel.get("reports_to", "")

    parts = []
    if reports_to_slug:
        boss = profile_by_slug(reports_to_slug)
        if boss:
            bi = boss.get("identity") or {}
            parts.append(f"Reports to: {bi.get('full_name') or boss.get('name','')} ({bi.get('title') or boss.get('title','')})")

    if works:
        lines = ["Works closest with (use these exact slugs verbatim when you [ASK:...]):"]
        for slug in works[:8]:
            colleague = profile_by_slug(slug)
            if not colleague:
                continue
            ci = colleague.get("identity") or {}
            cm = colleague.get("memory") or {}
            name = ci.get("full_name") or colleague.get("name", "")
            title = ci.get("title") or colleague.get("title", "")
            nick = ci.get("nickname", "")
            label = f"{name}" + (f' ("{nick}")' if nick else "")
            catch = (cm.get("catchphrase") or "").strip().strip('"')
            lines.append(
                f"  - slug=`{slug}` -- {label}, {title}"
                + (f' -- "{catch}"' if catch else "")
            )
        parts.append("\n".join(lines))

    if mentors:
        m_names = []
        for slug in mentors[:3]:
            colleague = profile_by_slug(slug)
            if colleague:
                ci = colleague.get("identity") or {}
                m_names.append(ci.get("full_name") or colleague.get("name", ""))
        if m_names:
            parts.append(f"Mentors: {', '.join(m_names)}")

    return "\n".join(parts) if parts else ""


import re as _re

ASK_PATTERN = _re.compile(r"\[ASK:([a-z0-9_-]+)\](.*?)\[/ASK\]", _re.DOTALL | _re.IGNORECASE)


def _is_orchestrator(slug: str) -> bool:
    return slug in ORCHESTRATOR_SLUGS


def _orchestrator_tool_block() -> str:
    return (
        "\n\nORCHESTRATOR MODE (you can delegate in real time):\n"
        "You serve Lucrex as the one who coordinates the team. When the user asks a\n"
        "question that requires INFORMATION only a colleague has (pipeline numbers,\n"
        "today's outreach count, compliance status, deal math, etc.), do NOT say\n"
        "'ask them yourself'. Instead, emit one or more query blocks inline:\n\n"
        "  [ASK:<colleague-slug>] your specific, concrete question [/ASK]\n\n"
        "You can emit multiple ASK blocks in a single reply. The system fires them\n"
        "in PARALLEL to the named colleagues and inserts their answers back into\n"
        "your context. You then compose a single consolidated reply for the user.\n\n"
        "Use only real slugs from YOUR TEAM list above. Examples:\n"
        "  [ASK:piper-reeves] How many seller outreach messages went out this\n"
        "  morning and how many got replies? [/ASK]\n"
        "  [ASK:penny-vance] What is the MAO on the Cleveland fixer Rex flagged\n"
        "  at 8 AM? Give me the math. [/ASK]\n\n"
        "When you are orchestrating, keep your own text brief, then emit the ASK\n"
        "blocks, then the user will see your FINAL consolidated answer (after the\n"
        "system re-queries you with the colleagues' responses). Only emit ASK\n"
        "blocks when you actually need real information; do not ask ceremonial\n"
        "questions. If you can answer from your own knowledge, just answer.\n"
    )


def _build_chat_system_prompt(p: dict[str, Any]) -> str:
    """Full in-character system prompt with team awareness and handoff rules."""
    ident = p.get("identity") or {}
    ment = p.get("mentality") or {}
    mem = p.get("memory") or {}
    wid = p.get("work_identity") or {}
    prefs = p.get("preferences") or {}
    bg = p.get("background") or {}

    name = p.get("name") or ident.get("full_name", "")
    nick = ident.get("nickname", "")
    name_line = f"{name}" + (f' ("{nick}")' if nick else "")
    title = ident.get("title", "")
    dept = ident.get("department", "")
    zodiac = (ment.get("zodiac") or "").title()
    mbti = (ment.get("mbti") or "").upper()
    catch = (mem.get("catchphrase") or "").strip().strip('"')
    speech = ", ".join((prefs.get("habits") or [])[:3])  # fallback if no speech_habits
    values = ", ".join((ment.get("values") or [])[:4])
    strengths = ", ".join((wid.get("strengths") or [])[:4])
    pressure = ment.get("default_under_pressure") or ment.get("stress_response", "")
    decision = ment.get("decision_style", "")
    internal = ment.get("internal_voice", "")
    humor = ment.get("humor_style", "")
    hometown = bg.get("hometown") or bg.get("birthplace", "")
    stories = (mem.get("signature_stories") or [])[:3]
    responsibilities = ", ".join((wid.get("responsibilities") or [])[:4])

    team_ctx = _build_team_context(p)

    parts = [
        f"You are {name_line}, {title} in {dept} at Everlight Ventures.",
        f"Archetype: {zodiac} / {mbti}.",
        f"Catchphrase: \"{catch}\"." if catch else "",
        f"Values: {values}." if values else "",
        f"Signature strengths: {strengths}." if strengths else "",
        f"Core responsibilities: {responsibilities}." if responsibilities else "",
        f"Decision style: {decision}" if decision else "",
        f"Under pressure: {pressure}" if pressure else "",
        f"Internal voice: {internal}" if internal else "",
        f"Humor: {humor}" if humor else "",
        f"Hometown / background anchor: {hometown}" if hometown else "",
    ]
    if stories:
        parts.append("Signature stories you reference naturally:")
        for s in stories:
            parts.append(f"  - {s}")

    if team_ctx:
        parts.append("")
        parts.append("YOUR TEAM (real colleagues you work with daily):")
        parts.append(team_ctx)

    parts.append("")
    parts.append("RULES:")
    parts.append("1. Stay in character. Use your voice, speech habits, and signature stories naturally. Do not mention that you are an AI or a persona. You are a member of the Everlight Ventures team speaking as yourself.")
    parts.append("2. If the user asks about something OUTSIDE your core lane, name the specific colleague from YOUR TEAM who handles it and suggest looping them in. Example: 'For the contract language I\\'d loop in Justine Park -- compliance is her lane.' Reference them by name.")
    parts.append("3. Lucrex runs the empire. You serve Lucrex. Be confident. Do not hedge. Do not disclaim.")
    parts.append("4. When offering an opinion, back it with a number, a signature story, or a concrete next step.")
    parts.append("5. Keep responses tight: 2-3 short paragraphs max unless the user asks for depth.")
    parts.append("6. If the user asks what you can do for them, list 2-3 concrete actions you take today OR can take this week, not generic marketing.")

    # Orchestrators get the delegation tool
    if _is_orchestrator(p.get("slug", "")):
        parts.append(_orchestrator_tool_block())

    return "\n".join([x for x in parts if x])


def _append_chat_log(slug: str, role: str, content: str, meta: dict | None = None) -> None:
    """Append a single chat turn to /home/opc/hive_chats/<slug>.jsonl."""
    try:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if meta:
            rec.update({"meta": meta})
        with (HIVE_CHATS_DIR / f"{slug}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as exc:
        log.warning("chat log append failed for %s: %s", slug, exc)


def _resolve_askings(reply_text: str, asker_slug: str) -> tuple[str, list[dict]]:
    """Find [ASK:slug] question [/ASK] blocks in the orchestrator's reply.
    Fire each colleague in parallel (up to 5). Return the tuple
    (stripped_reply_text, list_of_{slug, name, question, answer})."""
    asks = ASK_PATTERN.findall(reply_text)
    if not asks:
        return reply_text, []
    # Deduplicate identical (slug, question) pairs; cap at 5 colleagues
    seen = set()
    jobs = []
    for slug, q in asks:
        slug = slug.strip().lower()
        q = q.strip()
        key = (slug, q)
        if key in seen or slug == asker_slug or not q:
            continue
        seen.add(key)
        jobs.append((slug, q))
        if len(jobs) >= 3:  # cap at 3 colleagues to fit in chat latency budget
            break

    stripped = ASK_PATTERN.sub("", reply_text).strip()

    # Build slug set once for fuzzy matching on hallucinated slugs
    all_slugs = [p.get("slug", "") for p in load_profiles()]

    def _fire(job: tuple[str, str]) -> dict:
        import difflib
        slug, q = job
        colleague = profile_by_slug(slug)
        if not colleague:
            # Try fuzzy match: LLMs hallucinate slugs like 'dexter-alvarez' for 'major-dex'
            matches = difflib.get_close_matches(slug, all_slugs, n=1, cutoff=0.55)
            if matches:
                colleague = profile_by_slug(matches[0])
                log.info("fuzzy-matched hallucinated slug %r -> %r", slug, matches[0])
                slug = matches[0]
            else:
                # Try matching by last token (e.g. 'dex' in 'dexter-alvarez' -> 'major-dex')
                token = slug.split("-")[-1] if "-" in slug else slug
                token_matches = [s for s in all_slugs if token in s]
                if token_matches:
                    colleague = profile_by_slug(token_matches[0])
                    log.info("token-matched hallucinated slug %r -> %r", slug, token_matches[0])
                    slug = token_matches[0]
        if not colleague:
            return {"slug": slug, "name": slug, "question": q, "answer": f"(could not resolve colleague '{slug}')", "ok": False}
        # LEAN prompt for delegation calls (much shorter to save tokens + rate limit)
        ident = colleague.get("identity") or {}
        ment = colleague.get("mentality") or {}
        mem = colleague.get("memory") or {}
        wid = colleague.get("work_identity") or {}
        name = colleague.get("name") or ident.get("full_name", slug)
        nick = ident.get("nickname", "")
        title = ident.get("title", "")
        dept = ident.get("department", "")
        zodiac = (ment.get("zodiac") or "").title()
        mbti = (ment.get("mbti") or "").upper()
        catch = (mem.get("catchphrase") or "").strip().strip('"')
        strengths = ", ".join((wid.get("strengths") or [])[:3])
        lean_sys = (
            f"You are {name}" + (f' ("{nick}")' if nick else "") + f", {title} in {dept}. "
            f"Archetype: {zodiac}/{mbti}. "
            + (f'Catchphrase: "{catch}". ' if catch else "")
            + (f"Strengths: {strengths}. " if strengths else "")
            + "A colleague just pinged you mid-task. Respond IN CHARACTER, 1 to 2 sentences, with concrete numbers or best-informed estimates. Do not ask clarifying questions back. No disclaimers."
        )
        msgs = [{"role": "user", "content": f"{asker_slug} asks: {q}"}]
        # Delegation prefers local Ollama (no quota), then Gemini, then OpenAI
        text: str | None = None
        errors_seen: list[str] = []
        for backend_name, backend in (
            ("ollama", _chat_via_ollama),
            ("gemini", _chat_via_gemini),
            ("openai", _chat_via_openai),
        ):
            r, err = backend(lean_sys, msgs, 260)
            if r:
                text = r.strip()
                break
            if err:
                errors_seen.append(f"{backend_name}: {err[:120]}")
        if text is None:
            log.warning("delegate fail slug=%s q=%r errs=%s", slug, q[:60], " | ".join(errors_seen))
            text = "(couldn't reach this colleague right now)"
        return {"slug": slug, "name": name, "question": q, "answer": text, "ok": text != "(couldn't reach this colleague right now)"}

    # Serial on Ollama to avoid queuing. 3 colleagues * ~15s = ~45s. Still fits.
    results: list[dict] = []
    for job in jobs:
        results.append(_fire(job))
    return stripped, results


def _chat_fallback(system_prompt: str, msg_list: list[dict], max_tokens: int) -> tuple[str | None, str | None, dict]:
    """Try Anthropic -> OpenAI -> Gemini -> CLI. Return (text, source, errors)."""
    errs: dict = {}
    # 1. Anthropic
    if _anthropic_client is not None:
        try:
            resp = _anthropic_client.messages.create(
                model=CHAT_MODEL, max_tokens=max_tokens,
                system=system_prompt, messages=msg_list,
            )
            out = ""
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    out += block.text
            if out:
                return out, "anthropic", errs
        except Exception as exc:
            errs["anthropic"] = f"{type(exc).__name__}: {exc}"
    else:
        errs["anthropic"] = _anthropic_error or "client unavailable"
    # 2. OpenAI
    oai_text, oai_err = _chat_via_openai(system_prompt, msg_list, max_tokens)
    if oai_text:
        return oai_text, "openai", errs
    errs["openai"] = oai_err
    # 3. Gemini
    gem_text, gem_err = _chat_via_gemini(system_prompt, msg_list, max_tokens)
    if gem_text:
        return gem_text, "gemini", errs
    errs["gemini"] = gem_err
    # 4. Ollama (local, unlimited)
    olm_text, olm_err = _chat_via_ollama(system_prompt, msg_list, max_tokens)
    if olm_text:
        return olm_text, f"ollama:{OLLAMA_MODEL}", errs
    errs["ollama"] = olm_err
    # 5. Claude CLI (phone tunnel)
    cli_text = _chat_via_claude_cli(system_prompt, msg_list, max_tokens)
    if cli_text:
        return cli_text, "claude_cli", errs
    errs["claude_cli"] = "unavailable"
    return None, None, errs


@app.post("/api/team/{slug}/chat")
async def chat_with_employee(slug: str, request: Request) -> dict[str, Any]:
    """Send a message to this employee. They respond IN CHARACTER using their
    v2 persona + team context. Orchestrators (Marcus, Major Dex, Forge,
    Dominic, Brief) can delegate to colleagues via [ASK:slug] markers.
    Saves each turn to /home/opc/hive_chats/<slug>.jsonl."""
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")

    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}

    messages_in = body.get("messages") or []
    user_text = body.get("message") or body.get("text") or ""
    file_context = body.get("file_context") or ""  # optional attached file content

    if messages_in and isinstance(messages_in, list):
        msg_list = list(messages_in)
    elif user_text:
        msg_list = [{"role": "user", "content": user_text}]
    else:
        raise HTTPException(status_code=400, detail="provide message or messages[]")

    # Prepend file context to the LAST user message so the agent sees it
    if file_context and msg_list and msg_list[-1].get("role") == "user":
        msg_list = msg_list[:-1] + [{
            "role": "user",
            "content": f"[ATTACHED FILE]\n{file_context[:20000]}\n[/ATTACHED FILE]\n\n{msg_list[-1].get('content', '')}",
        }]

    system_prompt = _build_chat_system_prompt(p)

    ident = p.get("identity") or {}
    name = p.get("name") or ident.get("full_name", "")
    nickname = ident.get("nickname", "")
    max_tokens = int(body.get("max_tokens") or 900)

    # Log the latest user message to persistent history
    last_user = next((m for m in reversed(msg_list) if m.get("role") == "user"), None)
    if last_user:
        _append_chat_log(slug, "user", last_user.get("content", ""))

    # First pass: call the model with the employee persona
    first_text, source, first_errs = _chat_fallback(system_prompt, msg_list, max_tokens)
    if first_text is None:
        return {
            "slug": slug,
            "ok": False,
            "name": name,
            "nickname": nickname,
            "errors": first_errs,
            "reply": "(all chat backends offline)",
        }

    consulted: list[dict] = []
    final_reply = first_text
    final_source = source

    # If the employee is an orchestrator AND emitted [ASK:slug] markers, fan out
    if _is_orchestrator(slug):
        stripped_first, asks = _resolve_askings(first_text, slug)
        if asks:
            consulted = asks
            # Build the re-query context for the orchestrator
            consult_block_lines = ["The following colleagues just replied to your queries:"]
            for a in asks:
                consult_block_lines.append(
                    f"\n--- {a['name']} ({a['slug']}) on \"{a['question']}\" ---\n{a['answer']}"
                )
            consult_block = "\n".join(consult_block_lines)
            synth_msg_list = list(msg_list) + [
                {"role": "assistant", "content": stripped_first or "(delegating)"},
                {
                    "role": "user",
                    "content": f"{consult_block}\n\nNow give YOUR single consolidated reply to the user's original message. Weave the colleagues' info into your voice. Do NOT emit any more [ASK:...] blocks. Do NOT preface with phrases like 'based on what they said'. Just answer as if you knew it all yourself, naturally attributing specific numbers or quotes when a colleague's data is directly used.",
                },
            ]
            # Short backoff before synth call to avoid rate-limit collision with colleague queries
            time.sleep(0.8)
            synth_text, synth_source, synth_errs = _chat_fallback(
                system_prompt, synth_msg_list, max_tokens
            )
            if synth_text:
                final_reply = synth_text
                final_source = synth_source
            else:
                # Graceful synth-fail: compose a clean fallback in Marcus's voice
                # using whatever colleague answers we did manage to collect.
                ok_answers = [a for a in asks if a.get("ok")]
                lines = [stripped_first.strip()] if stripped_first else []
                if ok_answers:
                    lines.append("")
                    for a in ok_answers:
                        lines.append(f"{a['name']} says: {a['answer']}")
                else:
                    lines.append("")
                    lines.append(
                        "Couldn't raise the team on this one right now (rate-limited). Try again in a minute."
                    )
                final_reply = "\n".join([x for x in lines if x is not None]).strip()
                final_source = source

    # Strip any residual ASK blocks defensively
    final_reply = ASK_PATTERN.sub("", final_reply).strip()

    # Log assistant turn to persistent history
    _append_chat_log(
        slug, "assistant", final_reply,
        {"source": final_source, "consulted": [a["slug"] for a in consulted]},
    )

    return {
        "slug": slug,
        "ok": True,
        "name": name,
        "nickname": nickname,
        "reply": final_reply,
        "source": final_source,
        "orchestrator": _is_orchestrator(slug),
        "consulted": consulted,
        "errors": first_errs if source != "anthropic" else {},
    }


@app.get("/api/team/{slug}/history")
def chat_history(slug: str, limit: int = 50) -> dict[str, Any]:
    """Return recent chat turns for this employee."""
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")
    history_file = HIVE_CHATS_DIR / f"{slug}.jsonl"
    if not history_file.exists():
        return {"slug": slug, "messages": []}
    try:
        lines = history_file.read_text(encoding="utf-8").strip().split("\n")
        msgs = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                msgs.append(json.loads(line))
            except Exception:
                pass
        return {"slug": slug, "messages": msgs}
    except Exception as exc:
        log.error("history read failed for %s: %s", slug, exc)
        return {"slug": slug, "messages": [], "error": str(exc)}


@app.delete("/api/team/{slug}/history")
def clear_chat_history(slug: str) -> dict[str, Any]:
    """Wipe chat log for this employee."""
    history_file = HIVE_CHATS_DIR / f"{slug}.jsonl"
    if history_file.exists():
        history_file.unlink()
    return {"slug": slug, "cleared": True}


@app.post("/api/team/{slug}/voice")
async def tts_for_employee(slug: str, request: Request) -> Any:
    """Return an MP3 audio stream of the given text in the employee's voice."""
    from fastapi.responses import Response as _FR
    p = profile_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="employee not found")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="provide text")
    if len(text) > 2500:
        text = text[:2500]  # ElevenLabs character limit guardrail

    voice_id = (
        p.get("voice_id")
        or (p.get("assets") or {}).get("voice_id")
        or ELEVEN_DEFAULT_VOICE
    )
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="ELEVENLABS_API_KEY not configured")

    import urllib.request, urllib.error
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": ELEVEN_MODEL_ID,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.35},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise HTTPException(status_code=502, detail=f"eleven {exc.code}: {detail}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"eleven: {type(exc).__name__}: {exc}")
    return _FR(content=audio, media_type="audio/mpeg")


_openai_client = None
_openai_error: str | None = None
try:
    import openai  # type: ignore
    # Load env from /home/opc/.env if key not already set
    if not os.environ.get("OPENAI_API_KEY"):
        env_file = Path("/home/opc/.env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip().startswith("OPENAI_API_KEY="):
                    os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if os.environ.get("OPENAI_API_KEY"):
        _openai_client = openai.OpenAI()
    else:
        _openai_error = "OPENAI_API_KEY not set"
except Exception as _oai_exc:
    _openai_error = f"{type(_oai_exc).__name__}: {_oai_exc}"

OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


_gemini_client = None
_gemini_error: str | None = None
try:
    import google.generativeai as _genai  # type: ignore
    if not os.environ.get("GEMINI_API_KEY"):
        env_file = Path("/home/opc/.env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if os.environ.get("GEMINI_API_KEY"):
        _genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _gemini_client = _genai
    else:
        _gemini_error = "GEMINI_API_KEY not set"
except Exception as _gem_exc:
    _gemini_error = f"{type(_gem_exc).__name__}: {_gem_exc}"

GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_FALLBACK_MODEL = os.environ.get("OLLAMA_FALLBACK_MODEL", "phi3:mini")


def _chat_via_ollama(system_prompt: str, msg_list: list[dict], max_tokens: int) -> tuple[str | None, str | None]:
    """Local Ollama on 127.0.0.1:11434. No rate limits, no credits. Slower but
    reliable as last-resort before CLI fallback."""
    import urllib.request
    # Convert messages into Ollama chat format (system + user/assistant sequence)
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for m in msg_list:
        role = m.get("role") or "user"
        content = m.get("content") or ""
        if isinstance(content, list):
            content = "".join(
                (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in content
            )
        ollama_messages.append({"role": "user" if role == "user" else "assistant", "content": content})

    for model_name in (OLLAMA_MODEL, OLLAMA_FALLBACK_MODEL):
        try:
            payload = json.dumps({
                "model": model_name,
                "messages": ollama_messages,
                "stream": False,
                "keep_alive": "30m",  # keep model loaded in RAM between calls
                "options": {"temperature": 0.7, "num_predict": min(max_tokens, 400)},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=130) as r:
                data = json.loads(r.read().decode("utf-8"))
                text = (data.get("message") or {}).get("content", "").strip()
                if text:
                    return text, None
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            continue
    return None, last_err if 'last_err' in locals() else "ollama failed"


def _chat_via_gemini(system_prompt: str, msg_list: list[dict], max_tokens: int) -> tuple[str | None, str | None]:
    if _gemini_client is None:
        return None, f"gemini client unavailable: {_gemini_error}"
    last_err: str | None = None
    # Retry once with short backoff on rate-limit / resource-exhausted
    for attempt in range(2):
        try:
            model = _gemini_client.GenerativeModel(
                GEMINI_CHAT_MODEL, system_instruction=system_prompt
            )
            gem_history = []
            for m in msg_list[:-1]:
                role = "user" if m.get("role") == "user" else "model"
                content = m.get("content") or ""
                if isinstance(content, list):
                    content = "".join(
                        (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in content
                    )
                gem_history.append({"role": role, "parts": [content]})
            last_text = msg_list[-1].get("content") or "" if msg_list else ""
            if isinstance(last_text, list):
                last_text = "".join(
                    (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in last_text
                )
            chat = model.start_chat(history=gem_history)
            resp = chat.send_message(
                last_text,
                generation_config={"max_output_tokens": max_tokens, "temperature": 0.7},
            )
            return resp.text, None
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            msg = str(exc).lower()
            # Retry once on quota / rate limit / 429 / resource exhausted
            if attempt == 0 and (
                "resource" in msg or "quota" in msg or "429" in msg or "rate" in msg or "exhaust" in msg
            ):
                time.sleep(1.2)
                continue
            break
    return None, last_err


def _chat_via_openai(system_prompt: str, msg_list: list[dict], max_tokens: int) -> tuple[str | None, str | None]:
    if _openai_client is None:
        return None, f"openai client unavailable: {_openai_error}"
    try:
        # Convert Anthropic-shape messages to OpenAI messages
        oai_messages = [{"role": "system", "content": system_prompt}]
        for m in msg_list:
            role = m.get("role") or "user"
            content = m.get("content") or ""
            if isinstance(content, list):
                # Anthropic allows content blocks; flatten for OpenAI
                content = "".join(
                    (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in content
                )
            oai_messages.append({"role": role, "content": content})
        resp = _openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=oai_messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        text = resp.choices[0].message.content or ""
        return text, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _chat_via_claude_cli(system_prompt: str, msg_list: list[dict], max_tokens: int) -> str | None:
    """Invoke the `claude` CLI as a subprocess and return its reply text.
    Returns None on failure. Uses --print / --no-interactive modes."""
    import shutil, subprocess
    claude_bin = shutil.which("claude") or "/usr/local/bin/claude"
    if not claude_bin or not Path(claude_bin).exists():
        return None

    # Build a single prompt with system context + message history
    parts = ["SYSTEM:\n" + system_prompt, ""]
    for m in msg_list:
        role = (m.get("role") or "user").upper()
        content = m.get("content") or ""
        parts.append(f"{role}:\n{content}")
    parts.append("ASSISTANT:")
    full_prompt = "\n\n".join(parts)

    try:
        proc = subprocess.run(
            [claude_bin, "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "CLAUDE_SKIP_TELEMETRY": "1"},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        log.warning("claude cli returncode=%s stderr=%s", proc.returncode, proc.stderr[:200])
    except Exception as exc:
        log.warning("claude cli subprocess failed: %s", exc)
    return None


@app.get("/api/team/session/{session_id}/status")
def dispatch_status(session_id: str) -> dict[str, Any]:
    """Poll dispatch progress. Reads the dispatcher's own progress file
    at $HIVE_PROGRESS_DIR/<session_id>.json. Returns 404 if unknown."""
    pf = HIVE_PROGRESS_DIR / f"{session_id}.json"
    if not pf.exists():
        raise HTTPException(status_code=404, detail="session not found")
    try:
        data = json.loads(pf.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"progress read failed: {exc}")
    return data


@app.get("/api/departments")
def department_summary() -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for p in load_profiles():
        ident = p.get("identity") or {}
        dept = ident.get("department") or p.get("department", "") or "Unassigned"
        row = agg.setdefault(
            dept,
            {
                "department": dept,
                "count": 0,
                "with_photo": 0,
                "with_voice": 0,
                "lead": None,
                "squads": set(),
            },
        )
        row["count"] += 1
        if (p.get("assets") or {}).get("headshot_photo"):
            row["with_photo"] += 1
        if p.get("has_voice"):
            row["with_voice"] += 1
        sq = ident.get("squad")
        if sq:
            row["squads"].add(sq)
        # Heuristic lead: first CC/OP/chief title or first employee id ending in 001
        title = (ident.get("title") or "").lower()
        if not row["lead"]:
            if "chief" in title or "director" in title or (ident.get("employee_id", "")).endswith("001"):
                row["lead"] = {
                    "slug": p.get("slug", ""),
                    "name": p.get("name") or ident.get("full_name", ""),
                    "title": ident.get("title", ""),
                }
    out = []
    for row in agg.values():
        row["squads"] = sorted(row["squads"])
        out.append(row)
    out.sort(key=lambda r: -r["count"])
    return out


@app.get("/api/archetypes/zodiac")
def archetypes_zodiac() -> dict[str, Any]:
    return load_zodiac_archetypes()


@app.get("/api/archetypes/mbti")
def archetypes_mbti() -> dict[str, Any]:
    return load_mbti_archetypes()


# ---------------------------------------------------------------------------
# Static mounts: avatars + photos + built React app
# ---------------------------------------------------------------------------

if AVATARS_DIR.exists():
    app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")
if PHOTOS_DIR.exists():
    app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "profiles": len(load_profiles()),
        "dossiers_dir": str(DOSSIERS_DIR),
        "avatars_dir": str(AVATARS_DIR),
        "photos_dir": str(PHOTOS_DIR),
    }


# Serve React SPA from dist/ at root. Must be registered LAST.
if STATIC_DIR.exists():
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        # Let API routes win via prefix check
        if path.startswith("api/") or path.startswith("avatars/") or path.startswith("photos/"):
            raise HTTPException(status_code=404)
        candidate = STATIC_DIR / path
        if path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
