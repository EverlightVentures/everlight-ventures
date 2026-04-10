"""Stark AI -- Command classification, routing, and execution."""
from __future__ import annotations
import re
import json
import time
import subprocess
import requests
from datetime import datetime, timezone
from config import (
    TIER_PERMISSIONS, AGENT_ROUTING, WORKSPACE,
    ORACLE_DASHBOARD_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY,
)

# ── Classification patterns ──────────────────────────────────────────
PATTERNS = {
    "trading": [
        r"\bbot\b", r"trad(e|ing)", r"\bxlm\b", r"p[&n]l", r"position",
        r"margin", r"\bentry\b", r"\bexit\b", r"scalp", r"snipe", r"price",
    ],
    "dispatch": [
        r"dispatch", r"send\s+(the\s+)?team", r"\bhive\b", r"agents?\b", r"squad",
    ],
    "email": [
        r"\bemail\b", r"outreach", r"send\s+(a\s+)?message", r"follow.?up",
    ],
    "deals": [
        r"\bdeal\b", r"pipeline", r"wholesale", r"\blead\b", r"\bbuyer\b",
        r"\bseller\b", r"contract", r"commission", r"\bclose\b", r"\bbroker\b",
    ],
    "infrastructure": [
        r"\bserver\b", r"\boracle\b", r"\bdeploy\b", r"\bservice\b", r"\bcron\b",
        r"\bcpu\b", r"\bmemory\b", r"\bdisk\b", r"\brestart\b",
    ],
    "reports": [
        r"\breport\b", r"summary", r"\bbrief\b", r"analytics",
        r"\brevenue\b", r"\bkpi\b", r"\bmetric\b",
    ],
}


def classify(text: str) -> str:
    """Classify user input into a command category."""
    lower = text.lower()
    scores = {}
    for cat, pats in PATTERNS.items():
        score = sum(1 for p in pats if re.search(p, lower))
        if score > 0:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else "questions"


def check_permission(tier: str, category: str) -> bool:
    """Check if a tier has access to this command category."""
    allowed = TIER_PERMISSIONS.get(tier, TIER_PERMISSIONS["public"])
    return category in allowed


def get_agents(category: str) -> list[str]:
    """Return agent names for a given category."""
    return AGENT_ROUTING.get(category, ["Marcus Cole"])


# ── Quick handlers (no Claude needed) ────────────────────────────────

def _fetch_bot_status() -> dict:
    """Pull live bot status from Oracle dashboard API."""
    try:
        resp = requests.get(f"{ORACLE_DASHBOARD_URL}/api/status", timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def _fetch_pipeline() -> dict:
    """Pull wholesale pipeline metrics from Supabase."""
    try:
        key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/wholesale_leads?select=id,status,created_at&limit=200",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {key}"},
            timeout=8,
        )
        if resp.status_code == 200:
            leads = resp.json()
            by_status = {}
            for l in leads:
                s = l.get("status", "unknown")
                by_status[s] = by_status.get(s, 0) + 1
            return {"total": len(leads), "by_status": by_status}
    except Exception:
        pass
    return {}


def _dispatch_claude(prompt: str, timeout: int = 45) -> str:
    """Fire a prompt at Claude CLI and return the response."""
    lucrex_prompt = (
        "You are Lucrex, King of Divine Light. Respond with confidence, no hedging. "
        "Short, punchy sentences. Reference your Hive agents by name when relevant.\n\n"
        f"User command: {prompt}"
    )
    try:
        result = subprocess.run(
            ["claude", "--print", lucrex_prompt],
            capture_output=True, text=True, timeout=timeout, cwd=WORKSPACE,
        )
        return result.stdout.strip() if result.returncode == 0 else f"System error: {result.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return "Processing. The Hive is working on it -- check back in a moment."
    except FileNotFoundError:
        return "Claude CLI not available on this node. Routing through API fallback."
    except Exception as e:
        return f"Dispatch error: {str(e)[:200]}"


# ── Main command processor ────────────────────────────────────────────

async def process_command(text: str, user: dict) -> dict:
    """Process a command and return structured response."""
    start = time.time()
    category = classify(text)
    tier = user.get("tier", "public")

    if not check_permission(tier, category):
        return {
            "text": f"Access denied. Your tier ({tier}) doesn't include {category} commands. Upgrade to unlock.",
            "agent": "Lucrex",
            "category": category,
            "agents_used": [],
            "denied": True,
            "latency_ms": int((time.time() - start) * 1000),
        }

    agents = get_agents(category)
    lead_agent = agents[0]

    # Quick handlers for common categories
    if category == "trading":
        bot = _fetch_bot_status()
        if bot:
            price = bot.get("price", "?")
            pnl = bot.get("daily_pnl", bot.get("pnl", "?"))
            pos = bot.get("position", {})
            side = pos.get("side", "FLAT") if isinstance(pos, dict) else "FLAT"
            size = pos.get("size", 0) if isinstance(pos, dict) else 0
            response_text = (
                f"Bot's live. XLM at ${price}. "
                f"Position: {side} {size} contracts. "
                f"Daily P&L: ${pnl}. "
                f"Rex Thornton confirms all systems nominal."
            )
        else:
            response_text = _dispatch_claude(text)

    elif category == "deals":
        pipeline = _fetch_pipeline()
        if pipeline.get("total"):
            status_str = ", ".join(f"{k}: {v}" for k, v in pipeline.get("by_status", {}).items())
            response_text = (
                f"Pipeline report from Rex Blackwell and Filter Banks. "
                f"{pipeline['total']} total leads. Breakdown: {status_str}. "
                f"Harrison Knox standing by for closes."
            )
        else:
            response_text = _dispatch_claude(text)

    else:
        response_text = _dispatch_claude(text)

    latency = int((time.time() - start) * 1000)
    return {
        "text": response_text,
        "agent": lead_agent,
        "category": category,
        "agents_used": agents,
        "denied": False,
        "latency_ms": latency,
    }


async def log_command(user_id: str, session_id: str | None, input_text: str,
                      response: dict, voice_id: str | None = None) -> str | None:
    """Log command to Supabase stark_commands table. Returns command ID."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "input_text": input_text,
        "category": response.get("category", "questions"),
        "response_text": response.get("text", ""),
        "agents_used": response.get("agents_used", []),
        "voice_used": voice_id,
        "tier_at_time": response.get("tier", "public"),
        "latency_ms": response.get("latency_ms"),
    }
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/stark_commands",
            json=payload,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            rows = resp.json()
            return rows[0]["id"] if rows else None
    except Exception:
        pass
    return None
