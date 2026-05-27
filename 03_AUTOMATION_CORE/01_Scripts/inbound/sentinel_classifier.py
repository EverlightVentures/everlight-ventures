"""Categorize a stranger email + enrich it + flag opsec exposure.

classify(msg) -> {
  category: sales_pitch|partnership|investor|press|recon_probe|job|other,
  intent: float (-1..1),  high_stakes: bool,
  referenced_assets: [str],  opsec_flag: bool,
}
Keyword-first (deterministic + testable). An optional LLM second pass can be
added later behind OPENROUTER_API_KEY without changing this contract.
"""
from __future__ import annotations

import re

# Public Everlight asset names a stranger should not be probing without notice.
_OPSEC_TERMS = ["everlight-ventures", "proxy-broker", "broker_os", "xlm_bot", "hive_mind"]

_CATEGORY_RULES = [
    ("recon_probe",  [r"how important", r"is that live", r"part of the build", r"what.s your stack", r"do you use"]),
    ("investor",     [r"\binvest", r"\bfunding", r"raise", r"cap table", r"\bvc\b", r"check size"]),
    ("partnership",  [r"partner", r"collaborat", r"integrat", r"work together", r"reseller", r"affiliate"]),
    ("press",        [r"journalist", r"reporter", r"writing a (story|piece)", r"press", r"interview", r"podcast"]),
    ("job",          [r"\bresume\b", r"\bcv\b", r"hiring", r"job opening", r"apply", r"looking for work"]),
    ("sales_pitch",  [r"\bdemo\b", r"\bpricing\b", r"our (product|platform|service|tool)", r"book a call", r"@ \w+$"]),
]

_HIGH_STAKES = {"partnership", "investor", "press", "recon_probe", "job"}


def referenced_assets(text: str) -> list[str]:
    """Return public Everlight asset names the email mentions."""
    low = text.lower()
    hits = [t for t in _OPSEC_TERMS if t.replace("_", "-") in low or t in low]
    # also catch Org/repo paths like EverlightVentures/everlight-ventures
    for m in re.finditer(r"[A-Za-z0-9_-]+/([A-Za-z0-9_-]+)", text):
        repo = m.group(1).lower()
        if "everlight" in repo and repo not in hits:
            hits.append(repo)
    return hits


def _category(text: str) -> str:
    low = text.lower()
    for category, patterns in _CATEGORY_RULES:
        if any(re.search(p, low) for p in patterns):
            return category
    return "other"


def _intent(msg: dict) -> float:
    """Best-effort sentiment via the existing NLP engine; 0.0 if unavailable."""
    try:
        import sys
        from pathlib import Path as _P
        for d in ("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os",
                  str(_P(__file__).resolve().parents[3] / "06_DEVELOPMENT" / "everlight_os")):
            if d not in sys.path:
                sys.path.insert(0, d)
        from neuromorphic.nlp_engine import analyze_email_reply
        return float(analyze_email_reply(f"{msg.get('subject','')}\n{msg.get('body','')}").get("reply_sentiment", 0.0))
    except Exception:
        return 0.0


def classify(msg: dict) -> dict:
    blob = f"{msg.get('subject','')}\n{msg.get('body','')}"
    assets = referenced_assets(blob)
    category = _category(blob)
    # If they name our infra AND ask how it works, it is a probe regardless of wording.
    if assets and re.search(r"how important|is that live|part of the build|do you use", blob.lower()):
        category = "recon_probe"
    return {
        "category": category,
        "intent": _intent(msg),
        "high_stakes": category in _HIGH_STAKES,
        "referenced_assets": assets,
        "opsec_flag": bool(assets),
    }
