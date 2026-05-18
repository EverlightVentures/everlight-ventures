"""sheets_ai_helpers.py - ChatGPT-for-Excel patterns applied to our wholesale workbooks.

Built from 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/08_Spreadsheets_and_Ops/ transcripts. Ports the
"ChatGPT + Excel 7 ways" and "ChatGPT for Excel" patterns into reusable Python
helpers that Penny and Filter Banks can call from workbook_logger.py.

Design principles:
- Every helper uses Claude Haiku (cheap, fast). Never Opus for sheet work.
- Every helper returns a structured dict with a `confidence` field so Filter
  can decide whether to auto-accept or flag for human review.
- Helpers are stateless and cache-friendly (same input returns same output within
  a run, reducing re-scoring cost on retry).
- Max batch of 20 rows per LLM call to keep latency under 4 seconds per batch.

Usage:
    from sheets_ai_helpers import score_lead, estimate_arv, clean_contact

    score = score_lead({
        "address": "123 Main St",
        "city": "Atlanta", "state": "GA",
        "owner_tags": ["vacant", "pre_foreclosure"],
        "estimated_equity": 75000,
    })
    # -> {"score": 82, "tier": "A", "reasoning": "...", "confidence": 0.91}
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 400
API_URL = "https://api.anthropic.com/v1/messages"


# ---------------------------------------------------------------------------
# Env loader (stays consistent with workbook_logger.py)
# ---------------------------------------------------------------------------

_env_loaded = False
_api_key = ""


def _load_env() -> None:
    global _env_loaded, _api_key
    if _env_loaded:
        return
    _api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not _api_key:
        env_path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    _api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    _env_loaded = True


def _haiku_call(prompt: str) -> str:
    """Raw Claude Haiku call. Returns the text content or empty string on error."""
    _load_env()
    if not _api_key:
        return ""
    body = json.dumps(
        {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "x-api-key": _api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""
    content = data.get("content", [])
    return content[0].get("text", "") if content else ""


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of Haiku's response."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Helper 1: score_lead -- Filter Banks AI lead scoring
# ---------------------------------------------------------------------------

def score_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Score a wholesale lead 0-100. Returns {score, tier, reasoning, confidence}.

    Tiers: A (>=80, pitch immediately), B (60-79, second wave),
           C (40-59, nurture), D (<40, drop).

    Factors considered:
    - Distress signals (vacant, pre_foreclosure, tax_lien, divorce, probate)
    - Equity % (calculated from price + mortgage if available)
    - Ownership type (absentee > local; LLC > individual for speed)
    - Condition flags (fire, flood, major repair)
    - Market heat (days on Zillow, comparable sales velocity)
    """
    key_fields = {
        "address": lead.get("address", ""),
        "city": lead.get("city", ""),
        "state": lead.get("state", ""),
        "owner_tags": lead.get("owner_tags", []),
        "estimated_equity": lead.get("estimated_equity"),
        "absentee": lead.get("absentee", False),
        "property_condition": lead.get("property_condition", ""),
        "days_listed": lead.get("days_listed"),
        "owner_type": lead.get("owner_type", ""),
    }
    prompt = (
        "You are Filter Banks, a wholesale real-estate lead scorer. "
        "Score this lead 0-100 using these rules:\n"
        "- distress tags (vacant, pre_foreclosure, tax_lien, divorce, probate): +15 each (cap +40)\n"
        "- equity percent >= 40: +20; 20-39: +10; <20: 0\n"
        "- absentee owner: +10\n"
        "- LLC owner (faster decision): +5\n"
        "- fire/flood/major-repair: +10 (deeper discount possible)\n"
        "- days_listed > 60: +10 (motivated)\n\n"
        f"Lead:\n{json.dumps(key_fields, indent=2)}\n\n"
        'Respond ONLY as JSON: {"score": <int 0-100>, "tier": "<A|B|C|D>", '
        '"reasoning": "<2 sentences>", "confidence": <0.0-1.0>}'
    )
    raw = _haiku_call(prompt)
    data = _extract_json(raw)
    if not data:
        return {"score": 0, "tier": "D", "reasoning": "LLM error or empty response", "confidence": 0.0}
    try:
        score = max(0, min(100, int(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    tier = data.get("tier", "D")
    if tier not in {"A", "B", "C", "D"}:
        tier = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
    return {
        "score": score,
        "tier": tier,
        "reasoning": str(data.get("reasoning", ""))[:300],
        "confidence": float(data.get("confidence", 0.5)),
    }


# ---------------------------------------------------------------------------
# Helper 2: estimate_arv -- after-repair value from comps
# ---------------------------------------------------------------------------

def estimate_arv(subject: dict[str, Any], comps: list[dict[str, Any]]) -> dict[str, Any]:
    """Estimate After-Repair Value from comparable sales.

    Args:
        subject: {address, beds, baths, sqft, year_built, lot_size}
        comps: list of up to 10 dicts with {address, sold_price, sold_date, beds, baths, sqft, year_built, dist_miles}

    Returns:
        {arv, confidence, adjustments, notes}
    """
    if not comps:
        return {"arv": 0, "confidence": 0.0, "adjustments": [], "notes": "no comps provided"}
    trimmed_comps = comps[:10]
    prompt = (
        "You are Penny Sharpe, running ARV analysis for a wholesale deal. "
        "Estimate the After-Repair Value (ARV) for the subject. "
        "Use industry standard adjustments: $35/sqft delta, $15K/bed, $10K/bath, "
        "time adjustment +0.4% per month since sale, distance penalty -5% at 1mi, -15% at 3mi.\n\n"
        f"Subject: {json.dumps(subject)}\n\n"
        f"Comps (up to 10): {json.dumps(trimmed_comps)}\n\n"
        'Respond ONLY as JSON: {"arv": <int, final ARV estimate>, "confidence": <0.0-1.0>, '
        '"adjustments": [<list of 3-5 one-line adjustment notes>], "notes": "<1-2 sentence summary>"}'
    )
    raw = _haiku_call(prompt)
    data = _extract_json(raw)
    if not data:
        # Fallback: simple average of comps
        total = sum(c.get("sold_price", 0) for c in trimmed_comps)
        avg = int(total / len(trimmed_comps)) if trimmed_comps else 0
        return {"arv": avg, "confidence": 0.3, "adjustments": [], "notes": "LLM fail, used simple avg"}
    try:
        arv = int(data.get("arv", 0))
    except (TypeError, ValueError):
        arv = 0
    return {
        "arv": arv,
        "confidence": float(data.get("confidence", 0.5)),
        "adjustments": list(data.get("adjustments", []))[:8],
        "notes": str(data.get("notes", ""))[:400],
    }


# ---------------------------------------------------------------------------
# Helper 3: clean_contact -- normalize messy skip-trace output
# ---------------------------------------------------------------------------

def clean_contact(
    raw_name: str = "", raw_phone: str = "", raw_email: str = ""
) -> dict[str, Any]:
    """Take messy skip-trace output and return clean fields.

    Returns: {first_name, last_name, phone_e164, phone_is_mobile, email, confidence, issues}
    """
    raw_name = (raw_name or "").strip()
    raw_phone = (raw_phone or "").strip()
    raw_email = (raw_email or "").strip()
    prompt = (
        "You are cleaning a wholesale skip-trace record. Given messy input, return normalized fields. "
        "Rules:\n"
        "- Split raw_name into first/last; if comma-separated like 'Smith, John' infer correctly\n"
        "- Format phone as +1XXXXXXXXXX if US 10 digits; leave blank if invalid\n"
        "- Flag phone_is_mobile true if starts with US mobile area-code signal, false if clearly landline, null if unknown\n"
        "- Validate email: must have @ and TLD\n"
        "- List any issues (e.g., 'missing_last_name', 'invalid_phone_length')\n\n"
        f"raw_name: {raw_name!r}\nraw_phone: {raw_phone!r}\nraw_email: {raw_email!r}\n\n"
        'Respond ONLY as JSON: {"first_name": "", "last_name": "", "phone_e164": "", '
        '"phone_is_mobile": true|false|null, "email": "", "confidence": <0.0-1.0>, "issues": []}'
    )
    raw = _haiku_call(prompt)
    data = _extract_json(raw)
    if not data:
        return {
            "first_name": raw_name.split()[0] if raw_name else "",
            "last_name": raw_name.split()[-1] if len(raw_name.split()) > 1 else "",
            "phone_e164": "",
            "phone_is_mobile": None,
            "email": raw_email,
            "confidence": 0.2,
            "issues": ["llm_fail_fallback"],
        }
    return {
        "first_name": str(data.get("first_name", ""))[:60],
        "last_name": str(data.get("last_name", ""))[:60],
        "phone_e164": str(data.get("phone_e164", ""))[:16],
        "phone_is_mobile": data.get("phone_is_mobile"),
        "email": str(data.get("email", ""))[:120],
        "confidence": float(data.get("confidence", 0.5)),
        "issues": list(data.get("issues", []))[:8],
    }


# ---------------------------------------------------------------------------
# Helper 4: generate_slack_headline -- one-line summary for pipeline posts
# ---------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _cached_headline(lead_tuple: tuple) -> str:
    return _haiku_call(
        "Write ONE Slack-style headline for this wholesale lead. Max 140 chars. "
        "Include city + distress type + score if in data. No hashtags. No emoji.\n\n"
        f"Lead: {dict(lead_tuple)}\n\nHeadline:"
    ).strip()


def generate_slack_headline(lead: dict[str, Any]) -> str:
    """Deterministic Slack-style one-liner for a lead."""
    fields = ("address", "city", "state", "owner_tags", "estimated_equity", "score", "tier")
    tup = tuple((k, repr(lead.get(k))) for k in fields)
    result = _cached_headline(tup)
    return (result or f"{lead.get('city','?')} lead at {lead.get('address','?')}")[:140]


# ---------------------------------------------------------------------------
# Helper 5: analyze_disposition_funnel -- drop-off analysis across deal stages
# ---------------------------------------------------------------------------

def analyze_disposition_funnel(deals: list[dict[str, Any]]) -> dict[str, Any]:
    """Given a list of deal records with stage + outcome, identify drop-off patterns.

    Returns: {biggest_drop_stage, biggest_drop_pct, hypothesis, recommended_action, confidence}
    """
    if not deals:
        return {"biggest_drop_stage": "", "biggest_drop_pct": 0, "hypothesis": "no data", "confidence": 0.0}
    stages = ["scouted", "qualified", "contacted", "offered", "under_contract", "assigned", "funded"]
    counts = {s: 0 for s in stages}
    for d in deals:
        s = d.get("stage", "")
        if s in counts:
            counts[s] += 1
    # Compute funnel drops
    drops = []
    for i, s in enumerate(stages[:-1]):
        nxt = stages[i + 1]
        if counts[s] > 0:
            pct = int(100 * (1 - counts[nxt] / counts[s]))
            drops.append({"stage": s, "next_stage": nxt, "drop_pct": pct, "count": counts[s]})
    biggest = max(drops, key=lambda d: d["drop_pct"], default={"stage": "", "drop_pct": 0})

    prompt = (
        "You are Chart Dawson. Given this wholesale funnel drop-off data, propose the ONE hypothesis "
        "most likely explaining the biggest drop + ONE recommended action. Be specific and concrete.\n\n"
        f"Funnel counts: {counts}\n\n"
        f"Biggest drop: {biggest}\n\n"
        'Respond ONLY as JSON: {"hypothesis": "<1 sentence>", "recommended_action": "<1 sentence>", '
        '"confidence": <0.0-1.0>}'
    )
    raw = _haiku_call(prompt)
    data = _extract_json(raw) or {}
    return {
        "biggest_drop_stage": biggest["stage"],
        "biggest_drop_pct": biggest["drop_pct"],
        "funnel_counts": counts,
        "hypothesis": str(data.get("hypothesis", "insufficient data"))[:300],
        "recommended_action": str(data.get("recommended_action", ""))[:300],
        "confidence": float(data.get("confidence", 0.5)),
    }


# ---------------------------------------------------------------------------
# Batch helpers: call multiple items in one prompt for cost efficiency
# ---------------------------------------------------------------------------

def score_leads_batch(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score up to 20 leads in a single Haiku call. ~20x cheaper than per-lead."""
    if not leads:
        return []
    trimmed = leads[:20]
    key_fields = [
        {
            "idx": i,
            "address": l.get("address", ""),
            "owner_tags": l.get("owner_tags", []),
            "equity": l.get("estimated_equity"),
            "absentee": l.get("absentee", False),
            "condition": l.get("property_condition", ""),
            "days_listed": l.get("days_listed"),
        }
        for i, l in enumerate(trimmed)
    ]
    prompt = (
        "Score each wholesale lead 0-100 using the scoring rules "
        "(distress +15 per tag cap 40, equity%>=40 +20 or 20-39 +10, absentee +10, LLC +5, "
        "fire/flood +10, days_listed>60 +10). Return one row per input idx.\n\n"
        f"Leads: {json.dumps(key_fields)}\n\n"
        'Respond ONLY as JSON: {"results": [{"idx": <int>, "score": <int>, "tier": "<A|B|C|D>", '
        '"reasoning": "<brief>"}, ...]}'
    )
    raw = _haiku_call(prompt)
    data = _extract_json(raw) or {}
    results_by_idx = {r["idx"]: r for r in data.get("results", []) if isinstance(r, dict) and "idx" in r}
    out = []
    for i in range(len(trimmed)):
        r = results_by_idx.get(i, {})
        try:
            score = max(0, min(100, int(r.get("score", 0))))
        except (TypeError, ValueError):
            score = 0
        tier = r.get("tier") or ("A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D")
        out.append({"score": score, "tier": tier, "reasoning": r.get("reasoning", "")[:200]})
    return out


# ---------------------------------------------------------------------------
# Self-test when invoked directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo = {
        "address": "123 Oak St",
        "city": "Atlanta",
        "state": "GA",
        "owner_tags": ["vacant", "pre_foreclosure"],
        "estimated_equity": 80000,
        "absentee": True,
        "property_condition": "major_repair",
        "days_listed": 92,
        "owner_type": "individual",
    }
    print("score_lead:", json.dumps(score_lead(demo), indent=2))
    print("\nheadline:", generate_slack_headline(demo))

    funnel = [
        {"stage": "scouted"} for _ in range(100)
    ] + [{"stage": "qualified"} for _ in range(40)] + [
        {"stage": "contacted"} for _ in range(25)
    ] + [{"stage": "offered"} for _ in range(5)] + [{"stage": "under_contract"} for _ in range(2)]
    print("\nfunnel:", json.dumps(analyze_disposition_funnel(funnel), indent=2))
