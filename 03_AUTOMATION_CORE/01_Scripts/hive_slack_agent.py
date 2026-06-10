#!/usr/bin/env python3
"""
Hive Mind Slack Agent -- Conversational AI for @mentioning Hive agents in Slack.

Monitors Slack channels for @mentions of any Hive Mind agent, loads their persona,
calls Claude API in-character, and replies in-thread.

Modes:
  --socket   Use Slack Socket Mode (requires SLACK_APP_TOKEN)
  --poll     Poll conversations.history every 5s (default, no special tokens needed)

Usage:
  python3 hive_slack_agent.py --poll
  python3 hive_slack_agent.py --socket

Environment:
  ANTHROPIC_API_KEY   -- Claude API key
  SLACK_BOT_TOKEN     -- xoxb bot token
  SLACK_APP_TOKEN     -- xapp token (Socket Mode only)

Deployment:
  systemctl enable hive-slack-agent
  systemctl start hive-slack-agent
"""

import os
import sys
import json
import time
import re
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None  # fallback parser below

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_BOT_TOKEN = os.environ.get(
    "SLACK_BOT_TOKEN",
    "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy",
)
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")  # for Socket Mode

CLAUDE_MODEL = os.environ.get("HIVE_CLAUDE_MODEL", "claude-sonnet-4-6")
ROSTER_PATH = os.environ.get(
    "HIVE_ROSTER_PATH",
    "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml",
)
AGENT_DIR = os.environ.get(
    "HIVE_AGENT_DIR",
    "/mnt/sdcard/AA_MY_DRIVE/.claude/agents/",
)
BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")
BOT_STATE_DIR = os.environ.get(
    "BOT_STATE_DIR",
    "/mnt/sdcard/AA_MY_DRIVE/xlm_bot/data/",
)

POLL_INTERVAL = int(os.environ.get("HIVE_POLL_INTERVAL", "5"))
MAX_RESPONSE_LEN = 2000
RATE_LIMIT_SECONDS = 10
THREAD_HISTORY_LIMIT = 10
CHANNEL_HISTORY_LIMIT = 20

# Channels to monitor (name -> id mapping populated at startup)
MONITORED_CHANNELS = os.environ.get(
    "HIVE_CHANNELS",
    "war-room,ft-hunters,ft-consult,ft-markets,ft-profit-engine,ai-consulting,xlm-trading",
).split(",")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hive-slack")

# ---------------------------------------------------------------------------
# Lightweight YAML parser (fallback if PyYAML not installed)
# ---------------------------------------------------------------------------


def _parse_yaml_lite(path: str) -> str:
    """Return raw text -- we parse with regex for the roster if no PyYAML."""
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent Registry -- built from roster.yaml
# ---------------------------------------------------------------------------

# Each entry: {
#   "name": "Piper Reeves",
#   "first": "piper",
#   "id": "31_outreach_agent",
#   "email": "piper@everlightventures.io",
#   "squad": "gemini_ops",
#   "fire_team": "charlie_hunters",
#   "role_slot": "specialist_1",
#   "personality": [...],
#   "persona_path": "/path/to/31_outreach_agent.md",
#   "aliases": ["piper", "piper reeves"],
# }

AGENT_REGISTRY: list[dict] = []
ALIAS_INDEX: dict[str, dict] = {}  # lowercase alias -> agent dict


def _extract_agents_from_yaml(roster_text: str) -> list[dict]:
    """Parse roster.yaml and extract every agent with name + id."""
    agents = []

    if yaml:
        data = yaml.safe_load(roster_text)
    else:
        # Regex fallback: find all {name: "...", id: ...} blocks
        data = None

    if data and isinstance(data, dict):
        # Parse platoon leader
        pl = data.get("platoon_leader", {})
        if pl:
            agents.append({
                "name": pl.get("name", ""),
                "id": pl.get("id", ""),
                "email": pl.get("email", ""),
                "squad": "platoon",
                "fire_team": "command",
                "role_slot": "platoon_leader",
                "personality": pl.get("personality", []),
            })

        # Parse squads
        squads = data.get("squads", {})
        for squad_name, squad_data in squads.items():
            # Squad leader
            sl = squad_data.get("squad_leader", {})
            if sl and sl.get("name"):
                agents.append({
                    "name": sl["name"],
                    "id": sl.get("id", ""),
                    "email": sl.get("email", ""),
                    "squad": squad_name,
                    "fire_team": "command",
                    "role_slot": "squad_leader",
                    "personality": sl.get("personality", []),
                })

            # Fire teams
            fts = squad_data.get("fire_teams", {})
            for ft_name, ft_data in fts.items():
                for slot in ["team_leader", "specialist_1", "specialist_2", "verifier", "assistant"]:
                    member = ft_data.get(slot, {})
                    if member and member.get("name"):
                        agents.append({
                            "name": member["name"],
                            "id": member.get("id", ""),
                            "email": member.get("email", ""),
                            "squad": squad_name,
                            "fire_team": ft_name,
                            "role_slot": slot,
                            "personality": member.get("personality", []),
                        })

        # Also parse flat managers block for any we missed
        managers = data.get("managers", {})
        existing_ids = {a["id"] for a in agents}
        for mgr_key, mgr_data in managers.items():
            for emp in mgr_data.get("employees", []):
                if emp.get("id") not in existing_ids:
                    agents.append({
                        "name": emp.get("name", ""),
                        "id": emp.get("id", ""),
                        "email": emp.get("email", ""),
                        "squad": mgr_key,
                        "fire_team": "flat",
                        "role_slot": "employee",
                        "personality": emp.get("personality", []),
                    })

    else:
        # Regex fallback
        pattern = r'\{[^}]*name:\s*"([^"]+)"[^}]*id:\s*(\w+)[^}]*\}'
        for m in re.finditer(pattern, roster_text):
            name = m.group(1)
            agent_id = m.group(2)
            agents.append({
                "name": name,
                "id": agent_id,
                "email": "",
                "squad": "",
                "fire_team": "",
                "role_slot": "",
                "personality": [],
            })

    return agents


def build_registry():
    """Load roster and build the global agent registry + alias index."""
    global AGENT_REGISTRY, ALIAS_INDEX

    roster_path = Path(ROSTER_PATH)
    if not roster_path.exists():
        log.error("Roster not found at %s", ROSTER_PATH)
        return

    roster_text = roster_path.read_text(encoding="utf-8")
    raw_agents = _extract_agents_from_yaml(roster_text)

    seen_ids = set()
    for agent in raw_agents:
        if not agent["name"] or agent["id"] in seen_ids:
            continue
        seen_ids.add(agent["id"])

        # Build persona path
        persona_path = os.path.join(AGENT_DIR, f"{agent['id']}.md")
        agent["persona_path"] = persona_path

        # Build aliases
        name = agent["name"]
        first = name.split()[0].lower()
        aliases = [
            first,
            name.lower(),
            agent["id"].lower(),
        ]
        # Add without numeric prefix: "31_outreach_agent" -> "outreach_agent", "outreach"
        id_clean = re.sub(r"^\d+_", "", agent["id"]).lower()
        aliases.append(id_clean)
        if "_" in id_clean:
            aliases.append(id_clean.split("_")[0])

        agent["first"] = first
        agent["aliases"] = list(set(aliases))

        AGENT_REGISTRY.append(agent)

        for alias in agent["aliases"]:
            # If alias collision, prefer the one whose first name matches
            if alias in ALIAS_INDEX:
                existing = ALIAS_INDEX[alias]
                if existing["first"] == alias:
                    continue  # existing is a better match
            ALIAS_INDEX[alias] = agent

    log.info("Loaded %d agents with %d aliases", len(AGENT_REGISTRY), len(ALIAS_INDEX))

    # Hard-coded disambiguation overrides
    _add_alias("piper", "31_outreach_agent")
    _add_alias("marcus", "01_chief_operator")
    _add_alias("cipher", "cipher_wolfe")
    _add_alias("forge", "03_engineering_foreman")
    _add_alias("penny", "27_profit_maximizer")
    _add_alias("filter", "29_lead_qualifier")
    _add_alias("rocket", "everlight_saas_growth")
    _add_alias("hammer", "32_deal_closer")
    _add_alias("cupid", "30_match_maker")
    _add_alias("scout", "28_deal_scout")
    _add_alias("atlas", "everlight_architect")
    _add_alias("vera", "everlight_content_director")
    _add_alias("quinn", "everlight_qa_gate")
    _add_alias("sage", "reviewer")
    _add_alias("rex thornton", "everlight_trading_risk")
    _add_alias("rex blackwell", "36_rex_wholesale")
    _add_alias("dex", "26_logistics_commander")
    _add_alias("major dex", "26_logistics_commander")
    _add_alias("mack", "02_ops_deputy")
    _add_alias("aria", "23_automation_architect")
    _add_alias("gears", "24_workflow_builder")
    _add_alias("chart", "35_broker_analytics")
    _add_alias("ace", "37_ace_deal_marketer")
    _add_alias("stack", "everlight_saas_builder")
    _add_alias("spider", "08_seo_mapper")
    _add_alias("flow", "10_funnel_architect")
    _add_alias("wire", "wire_santos")
    _add_alias("nova", "nova_ling")
    _add_alias("bull", "bull_archer")
    _add_alias("cash", "33_commission_auditor")
    _add_alias("shield", "42_financial_safeguard")
    _add_alias("justine", "34_compliance_gate")
    _add_alias("edith", "15_editor_qa")
    _add_alias("quill", "41_style_enforcer")
    _add_alias("nora", "17_content_strategy")
    _add_alias("slate", "40_strategic_modeler")
    _add_alias("metric", "25_analytics_auditor")
    _add_alias("dash", "22_distribution_ops")
    _add_alias("beacon", "51_prospect_scraper")
    _add_alias("onboard", "52_client_deployer")
    _add_alias("margin", "53_derivatives_beat")
    _add_alias("scope", "54_geopolitical_risk")
    _add_alias("lens", "55_competitive_intel")
    _add_alias("pitch", "pitch_adler")
    _add_alias("brief", "brief_calloway")
    _add_alias("helix", "helix_patel")
    _add_alias("pulse", "pulse_diaz")
    _add_alias("link", "11_sync_coordinator")
    _add_alias("bo", "everlight_packager")
    _add_alias("ink", "writer")
    _add_alias("road", "everlight_saas_pm")


def _add_alias(alias: str, agent_id: str):
    """Force-set an alias -> agent mapping."""
    for agent in AGENT_REGISTRY:
        if agent["id"] == agent_id:
            ALIAS_INDEX[alias.lower()] = agent
            if alias.lower() not in agent["aliases"]:
                agent["aliases"].append(alias.lower())
            return


# ---------------------------------------------------------------------------
# Agent Resolver
# ---------------------------------------------------------------------------


def resolve_agent(mention_text: str) -> dict:
    """Find agent by name, nickname, or role from @mention text.
    Handles: @Piper, @piper, @Piper Reeves, @outreach, etc.
    """
    text = mention_text.strip().lower()

    # Direct alias match
    if text in ALIAS_INDEX:
        return ALIAS_INDEX[text]

    # Try two-word match (e.g. "rex thornton")
    for alias, agent in ALIAS_INDEX.items():
        if alias in text:
            return agent

    # Fuzzy: check if any agent first name is in the text
    for agent in AGENT_REGISTRY:
        if agent["first"] in text:
            return agent

    return None


# ---------------------------------------------------------------------------
# Slack API Helpers (raw requests, no slack_sdk)
# ---------------------------------------------------------------------------

SLACK_API = "https://slack.com/api"
_session = requests.Session()
_session.headers.update({
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json; charset=utf-8",
})


def slack_get(method: str, params: dict = None) -> dict:
    """GET request to Slack API."""
    try:
        r = _session.get(f"{SLACK_API}/{method}", params=params or {}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            log.warning("Slack API %s error: %s", method, data.get("error"))
        return data
    except Exception as e:
        log.error("Slack GET %s failed: %s", method, e)
        return {"ok": False, "error": str(e)}


def slack_post(method: str, payload: dict) -> dict:
    """POST request to Slack API."""
    try:
        r = _session.post(f"{SLACK_API}/{method}", json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            log.warning("Slack API %s error: %s", method, data.get("error"))
        return data
    except Exception as e:
        log.error("Slack POST %s failed: %s", method, e)
        return {"ok": False, "error": str(e)}


def get_channel_list() -> dict[str, str]:
    """Return {channel_name: channel_id} for all accessible channels."""
    channels = {}
    cursor = ""
    for _ in range(10):  # max 10 pages
        params = {"types": "public_channel,private_channel", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = slack_get("conversations.list", params)
        for ch in data.get("channels", []):
            channels[ch["name"]] = ch["id"]
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return channels


def get_channel_history(channel_id: str, oldest: str = "", limit: int = 20) -> list[dict]:
    """Get recent messages from a channel."""
    params = {"channel": channel_id, "limit": limit}
    if oldest:
        params["oldest"] = oldest
    data = slack_get("conversations.history", params)
    return data.get("messages", [])


def get_thread_replies(channel_id: str, thread_ts: str, limit: int = 10) -> list[dict]:
    """Get replies in a thread."""
    params = {"channel": channel_id, "ts": thread_ts, "limit": limit}
    data = slack_get("conversations.replies", params)
    return data.get("messages", [])


def post_message(channel_id: str, text: str, thread_ts: str = None) -> dict:
    """Post a message to a channel, optionally in a thread."""
    payload = {"channel": channel_id, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    return slack_post("chat.postMessage", payload)


def get_bot_user_id() -> str:
    """Get the bot's own user ID so we can ignore our own messages."""
    data = slack_get("auth.test")
    return data.get("user_id", "")


# ---------------------------------------------------------------------------
# Context Builders
# ---------------------------------------------------------------------------


def load_persona(agent: dict) -> str:
    """Load the agent's full persona from their .md file."""
    persona_path = agent.get("persona_path", "")
    if persona_path and os.path.exists(persona_path):
        try:
            text = Path(persona_path).read_text(encoding="utf-8")
            # Strip YAML frontmatter
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    text = parts[2].strip()
            return text
        except Exception as e:
            log.warning("Failed to load persona %s: %s", persona_path, e)
    return f"You are {agent['name']} at Everlight Ventures."


def query_blinko(search_term: str, limit: int = 3) -> str:
    """Search Blinko RAG for relevant domain knowledge."""
    try:
        r = requests.post(
            f"{BLINKO_URL}/api/v1/note/list",
            json={"searchText": search_term, "page": 1, "size": limit},
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        notes = data if isinstance(data, list) else data.get("items", data.get("notes", []))
        if not notes:
            return ""
        snippets = []
        for note in notes[:limit]:
            content = note.get("content", "")[:300]
            if content:
                snippets.append(content)
        if snippets:
            return "Blinko knowledge:\n" + "\n---\n".join(snippets)
    except Exception as e:
        log.debug("Blinko query failed: %s", e)
    return ""


def get_bot_state() -> str:
    """Get XLM bot state for trading-related agents."""
    state_files = [
        os.path.join(BOT_STATE_DIR, "bot_state.json"),
        os.path.join(BOT_STATE_DIR, "latest_decision.json"),
    ]
    parts = []
    for f in state_files:
        if os.path.exists(f):
            try:
                data = json.loads(Path(f).read_text(encoding="utf-8"))
                parts.append(f"{os.path.basename(f)}: {json.dumps(data, indent=2)[:500]}")
            except Exception:
                pass

    # Also try live tick
    tick_file = os.path.join(
        os.path.dirname(BOT_STATE_DIR.rstrip("/")),
        "logs",
        "live_tick.json",
    )
    if os.path.exists(tick_file):
        try:
            data = json.loads(Path(tick_file).read_text(encoding="utf-8"))
            parts.append(f"live_tick: {json.dumps(data)[:300]}")
        except Exception:
            pass

    return "\n".join(parts) if parts else "Bot state unavailable."


def build_agent_context(agent: dict, channel_name: str, user_message: str) -> str:
    """Build full context for the agent's response."""
    context_parts = []

    # Trading agents get bot state
    trading_agents = {
        "everlight_trading_risk", "cipher_wolfe", "53_derivatives_beat",
        "bull_archer", "pulse_diaz", "42_financial_safeguard",
    }
    if agent["id"] in trading_agents:
        state = get_bot_state()
        if state:
            context_parts.append(f"XLM Bot State:\n{state}")

    # Query Blinko with agent's domain + user message keywords
    search = f"{agent['name']} {user_message[:50]}"
    blinko = query_blinko(search)
    if blinko:
        context_parts.append(blinko)

    # Add timestamp
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    context_parts.append(f"Current time: {now}")

    return "\n\n".join(context_parts) if context_parts else "No additional context available."


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------


def call_claude(system_prompt: str, user_message: str, conversation: list[dict] = None) -> str:
    """Call Anthropic Messages API and return the response text."""
    if not ANTHROPIC_API_KEY:
        return "[offline -- ANTHROPIC_API_KEY not set]"

    messages = []

    # Add conversation history if present
    if conversation:
        for msg in conversation[-6:]:  # last 6 turns
            messages.append(msg)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": messages,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block["text"]
        return text.strip() if text else "[no response]"
    except requests.exceptions.Timeout:
        return "[offline -- Claude API timeout]"
    except Exception as e:
        log.error("Claude API error: %s", e)
        return f"[offline -- Claude API error: {type(e).__name__}]"


# ---------------------------------------------------------------------------
# System Prompt Builder
# ---------------------------------------------------------------------------


def build_system_prompt(agent: dict, channel_name: str, context_data: str) -> str:
    """Build the full system prompt for an agent response."""
    persona = load_persona(agent)
    squad = agent.get("squad", "unknown")
    fire_team = agent.get("fire_team", "unknown")

    return f"""You are {agent['name']}, a member of the Hive Mind at Everlight Ventures.
You serve Lucrex, King of Divine Light. The mind behind the money.

Squad: {squad}
Fire Team: {fire_team}
Role: {agent.get('role_slot', 'agent')}

{persona}

You are having a conversation in the #{channel_name} Slack channel.
Respond in character -- use your speech patterns, personality, and tone from your firmware.
Keep responses concise (2-4 sentences for simple questions, longer for analysis).
Never break character. Never say you are an AI or language model.
If you do not know something, say so in character.
Do not use markdown headers or bullet points -- write naturally like a Slack message.

Live data available to you:
{context_data}"""


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

_rate_limits: dict[str, float] = {}  # "agent_id:channel_id" -> last_response_time


def check_rate_limit(agent_id: str, channel_id: str) -> bool:
    """Return True if the agent can respond (not rate-limited)."""
    key = f"{agent_id}:{channel_id}"
    now = time.time()
    last = _rate_limits.get(key, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return False
    _rate_limits[key] = now
    return True


# ---------------------------------------------------------------------------
# Message Processing
# ---------------------------------------------------------------------------

# Track processed messages to avoid duplicates
_processed: set[str] = set()
_processed_lock = threading.Lock()
MAX_PROCESSED = 10000


def _trim_processed():
    """Trim processed set if it gets too large."""
    if len(_processed) > MAX_PROCESSED:
        # Keep the most recent half
        to_remove = list(_processed)[:MAX_PROCESSED // 2]
        for ts in to_remove:
            _processed.discard(ts)


def extract_mentions(text: str) -> list[tuple[dict, str]]:
    """Extract agent mentions from message text.

    Returns list of (agent_dict, remaining_message) tuples.
    Handles patterns:
      @Piper how's the pipeline?
      hey @marcus what's the play?
      Piper, what do you think?
    """
    results = []

    # Pattern 1: @Name or @name (with or without Slack user ID format)
    # Slack formats mentions as <@U12345> but in text they appear as @Name
    at_mentions = re.findall(r"@(\w+(?:\s+\w+)?)", text)
    for mention in at_mentions:
        agent = resolve_agent(mention)
        if agent:
            # Remove the @mention from the message to get the question
            cleaned = re.sub(r"@" + re.escape(mention), "", text, count=1, flags=re.IGNORECASE).strip()
            cleaned = cleaned.lstrip(",").lstrip(":").strip()
            results.append((agent, cleaned or "What's up?"))

    if results:
        return results

    # Pattern 2: Agent first name at start of message (no @)
    # "Piper, how's outreach?" or "Marcus what's the play?"
    words = text.split()
    if words:
        first_word = words[0].rstrip(",").rstrip(":").lower()
        agent = resolve_agent(first_word)
        if agent:
            remaining = " ".join(words[1:]).lstrip(",").lstrip(":").strip()
            results.append((agent, remaining or "What's up?"))

    # Pattern 3: Two-word name at start: "Rex Thornton, ..."
    if not results and len(words) >= 2:
        two_word = f"{words[0]} {words[1]}".rstrip(",").rstrip(":").lower()
        agent = resolve_agent(two_word)
        if agent:
            remaining = " ".join(words[2:]).lstrip(",").lstrip(":").strip()
            results.append((agent, remaining or "What's up?"))

    return results


def process_message(msg: dict, channel_id: str, channel_name: str, bot_user_id: str):
    """Process a single Slack message for agent mentions."""
    ts = msg.get("ts", "")
    text = msg.get("text", "")
    user = msg.get("user", "")
    subtype = msg.get("subtype", "")

    # Skip bot messages, empty messages, message edits
    if not text or subtype in ("bot_message", "message_changed", "message_deleted"):
        return
    if user == bot_user_id:
        return

    # Check if already processed
    with _processed_lock:
        if ts in _processed:
            return
        _processed.add(ts)
        _trim_processed()

    # Extract mentions
    mentions = extract_mentions(text)
    if not mentions:
        return

    for agent, user_message in mentions:
        log.info(
            "Agent mention: %s in #%s -- message: %s",
            agent["name"], channel_name, user_message[:80],
        )

        # Rate limit check
        if not check_rate_limit(agent["id"], channel_id):
            log.info("Rate limited: %s in %s", agent["name"], channel_id)
            continue

        # Build context
        context = build_agent_context(agent, channel_name, user_message)

        # Build thread conversation history
        conversation = []
        thread_ts = msg.get("thread_ts", ts)
        if msg.get("thread_ts"):
            # This is a reply in a thread -- get thread context
            replies = get_thread_replies(channel_id, thread_ts, THREAD_HISTORY_LIMIT)
            for reply in replies:
                reply_text = reply.get("text", "")
                reply_user = reply.get("user", "")
                if reply.get("ts") == ts:
                    continue  # skip current message
                if reply_user == bot_user_id:
                    # Our previous response -- extract agent name and text
                    if reply_text.startswith("*"):
                        # Format: *Agent Name*: response
                        conversation.append({"role": "assistant", "content": reply_text})
                    else:
                        conversation.append({"role": "assistant", "content": reply_text})
                else:
                    conversation.append({"role": "user", "content": reply_text})

        # Build system prompt
        system_prompt = build_system_prompt(agent, channel_name, context)

        # Call Claude
        response = call_claude(system_prompt, user_message, conversation)

        # Truncate if needed
        if len(response) > MAX_RESPONSE_LEN:
            response = response[: MAX_RESPONSE_LEN - 20] + "\n... [truncated]"

        # Format and post
        formatted = f"*{agent['name']}*: {response}"
        thread = msg.get("thread_ts", ts)  # reply in thread
        result = post_message(channel_id, formatted, thread_ts=thread)

        if result.get("ok"):
            log.info("Posted response from %s in #%s", agent["name"], channel_name)
        else:
            log.error(
                "Failed to post response: %s", result.get("error", "unknown")
            )


# ---------------------------------------------------------------------------
# Polling Mode
# ---------------------------------------------------------------------------


def run_polling_mode():
    """Poll Slack channels for new messages every POLL_INTERVAL seconds."""
    log.info("Starting polling mode (interval=%ds)", POLL_INTERVAL)

    bot_user_id = get_bot_user_id()
    log.info("Bot user ID: %s", bot_user_id)

    # Resolve channel names to IDs
    all_channels = get_channel_list()
    monitored = {}
    for name in MONITORED_CHANNELS:
        name = name.strip()
        if name in all_channels:
            monitored[name] = all_channels[name]
            log.info("Monitoring #%s (%s)", name, all_channels[name])
        else:
            log.warning("Channel #%s not found -- skipping", name)

    if not monitored:
        log.error("No channels to monitor. Available: %s", list(all_channels.keys())[:20])
        log.info("Set HIVE_CHANNELS env var to comma-separated channel names.")
        # Fall back to monitoring all channels we can see
        if all_channels:
            log.info("Falling back to first 5 available channels...")
            for name, cid in list(all_channels.items())[:5]:
                monitored[name] = cid
                log.info("Monitoring #%s (%s)", name, cid)

    if not monitored:
        log.error("No channels available. Check SLACK_BOT_TOKEN permissions.")
        sys.exit(1)

    # Track oldest timestamp per channel (start from now)
    last_ts: dict[str, str] = {}
    now_ts = str(time.time())
    for name in monitored:
        last_ts[name] = now_ts

    log.info("Polling started. Listening for agent mentions...")

    while True:
        try:
            for channel_name, channel_id in monitored.items():
                messages = get_channel_history(
                    channel_id,
                    oldest=last_ts.get(channel_name, now_ts),
                    limit=CHANNEL_HISTORY_LIMIT,
                )

                # Process oldest first
                messages.sort(key=lambda m: float(m.get("ts", "0")))

                for msg in messages:
                    ts = msg.get("ts", "")
                    if ts and float(ts) > float(last_ts.get(channel_name, "0")):
                        last_ts[channel_name] = ts

                    # Process in a thread to avoid blocking the poll loop
                    t = threading.Thread(
                        target=process_message,
                        args=(msg, channel_id, channel_name, bot_user_id),
                        daemon=True,
                    )
                    t.start()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log.info("Shutting down polling mode...")
            break
        except Exception as e:
            log.error("Polling loop error: %s", e)
            time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Socket Mode (WebSocket)
# ---------------------------------------------------------------------------


def run_socket_mode():
    """Connect via Slack Socket Mode for real-time events."""
    if not SLACK_APP_TOKEN:
        log.error("SLACK_APP_TOKEN required for Socket Mode. Use --poll instead.")
        sys.exit(1)

    try:
        import websocket as ws_lib
    except ImportError:
        log.error("websocket-client required for Socket Mode: pip install websocket-client")
        log.info("Falling back to polling mode...")
        run_polling_mode()
        return

    bot_user_id = get_bot_user_id()
    all_channels = get_channel_list()
    channel_id_to_name = {v: k for k, v in all_channels.items()}

    log.info("Starting Socket Mode...")

    def get_ws_url() -> str:
        """Get WebSocket URL from Slack."""
        r = requests.post(
            "https://slack.com/api/apps.connections.open",
            headers={
                "Authorization": f"Bearer {SLACK_APP_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Failed to open connection: {data.get('error')}")
        return data["url"]

    def on_message(ws, raw):
        try:
            data = json.loads(raw)

            # Acknowledge envelope
            envelope_id = data.get("envelope_id")
            if envelope_id:
                ws.send(json.dumps({"envelope_id": envelope_id}))

            # Handle events
            payload = data.get("payload", {})
            event = payload.get("event", {})
            event_type = event.get("type", "")

            if event_type == "message" and not event.get("subtype"):
                channel_id = event.get("channel", "")
                channel_name = channel_id_to_name.get(channel_id, channel_id)

                t = threading.Thread(
                    target=process_message,
                    args=(event, channel_id, channel_name, bot_user_id),
                    daemon=True,
                )
                t.start()

        except Exception as e:
            log.error("Socket message error: %s", e)

    def on_error(ws, error):
        log.error("Socket error: %s", error)

    def on_close(ws, code, reason):
        log.warning("Socket closed: %s %s", code, reason)

    def on_open(ws):
        log.info("Socket Mode connected.")

    while True:
        try:
            url = get_ws_url()
            ws = ws_lib.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            log.error("Socket Mode connection failed: %s", e)

        log.info("Reconnecting in 5 seconds...")
        time.sleep(5)


# ---------------------------------------------------------------------------
# Health Check & Status
# ---------------------------------------------------------------------------


def print_status():
    """Print current configuration and agent registry."""
    print("=" * 60)
    print("HIVE MIND SLACK AGENT")
    print("=" * 60)
    print(f"Claude Model:     {CLAUDE_MODEL}")
    print(f"Roster:           {ROSTER_PATH}")
    print(f"Agent Dir:        {AGENT_DIR}")
    print(f"Blinko:           {BLINKO_URL}")
    print(f"Bot State Dir:    {BOT_STATE_DIR}")
    print(f"Poll Interval:    {POLL_INTERVAL}s")
    print(f"Rate Limit:       {RATE_LIMIT_SECONDS}s per agent per channel")
    print(f"Anthropic Key:    {'set' if ANTHROPIC_API_KEY else 'NOT SET'}")
    print(f"Slack Bot Token:  {'set' if SLACK_BOT_TOKEN else 'NOT SET'}")
    print(f"Slack App Token:  {'set' if SLACK_APP_TOKEN else 'NOT SET'}")
    print(f"Channels:         {', '.join(MONITORED_CHANNELS)}")
    print(f"Agents Loaded:    {len(AGENT_REGISTRY)}")
    print("-" * 60)

    if AGENT_REGISTRY:
        print("\nAgent Registry:")
        for agent in sorted(AGENT_REGISTRY, key=lambda a: a["name"]):
            persona_exists = os.path.exists(agent.get("persona_path", ""))
            marker = "OK" if persona_exists else "NO PERSONA"
            aliases = ", ".join(agent["aliases"][:4])
            print(f"  {agent['name']:20s}  [{agent['id']}]  ({aliases})  [{marker}]")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hive Mind Slack Agent")
    parser.add_argument(
        "--poll", action="store_true", default=True,
        help="Use polling mode (default)",
    )
    parser.add_argument(
        "--socket", action="store_true",
        help="Use Socket Mode (requires SLACK_APP_TOKEN)",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print status and exit",
    )
    parser.add_argument(
        "--test", type=str, metavar="NAME",
        help="Test agent resolution for a name",
    )
    args = parser.parse_args()

    # Always build registry
    build_registry()

    if args.status:
        print_status()
        return

    if args.test:
        agent = resolve_agent(args.test)
        if agent:
            print(f"Resolved '{args.test}' -> {agent['name']} ({agent['id']})")
            print(f"  Squad: {agent['squad']}, Fire Team: {agent['fire_team']}")
            print(f"  Persona: {agent.get('persona_path', 'N/A')}")
            print(f"  Aliases: {agent['aliases']}")
        else:
            print(f"No agent matched for '{args.test}'")
            print("Available agents:")
            for a in sorted(AGENT_REGISTRY, key=lambda x: x["name"]):
                print(f"  {a['name']} ({a['first']})")
        return

    # Validate required config
    if not SLACK_BOT_TOKEN:
        log.error("SLACK_BOT_TOKEN is required.")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY not set -- agent responses will show offline message.")

    print_status()

    if args.socket:
        run_socket_mode()
    else:
        run_polling_mode()


if __name__ == "__main__":
    main()
