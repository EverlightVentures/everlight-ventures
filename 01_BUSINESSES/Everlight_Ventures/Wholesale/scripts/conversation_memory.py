#!/usr/bin/env python3
"""
conversation_memory.py -- the RELATIONSHIP BRAIN. Remembers every conversation so we
have intelligent, stateful back-and-forth, not canned monitoring.

Phase memory (pipeline_phase_manager) says WHERE a lead is. THIS says WHAT WAS SAID:
every message in/out, the facts they told us, the questions still open on both sides,
the commitments made, the objections raised, and the next concrete move. The responder
generates FROM this so replies reference history, answer open questions, never repeat,
and advance the relationship. Every contact is a brain note (Blinko, local-first) so the
record is permanent + cross-referenceable -- a real portfolio.

One ledger per contact: _state/conversations/<email-hash>.json
  contact{email,name,role,phase}  messages[]  state{facts, their_open_qs, our_open_qs,
  commitments{ours,theirs}, objections}  rapport{}  next_action  updated_at

Usage:
  python3 conversation_memory.py --show EMAIL        # the full relationship record
  python3 conversation_memory.py --context EMAIL     # the context pack a reply is built from
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
CONV = ROOT / "_state" / "conversations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(email: str) -> Path:
    h = hashlib.md5((email or "").strip().lower().encode()).hexdigest()[:14]
    return CONV / f"{h}.json"


def load(email: str) -> dict:
    p = _path(email)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"contact": {"email": (email or "").lower(), "name": "", "role": "", "phase": ""},
            "messages": [], "state": {"facts": [], "their_open_qs": [], "our_open_qs": [],
            "commitments": {"ours": [], "theirs": []}, "objections": [], "personas_seen": []},
            "rapport": {"sentiment": "neutral", "notes": []}, "next_action": "", "updated_at": _now()}


def _save(email: str, rec: dict) -> None:
    CONV.mkdir(parents=True, exist_ok=True)
    rec["updated_at"] = _now()
    _path(email).write_text(json.dumps(rec, indent=2))


# --- lightweight extraction (heuristic now; swap to LLM when a key lands) ---
_Q = re.compile(r"[^.!?\n]*\?")
_FACT_HINT = re.compile(r"\b(criteria|buy box|budget|cash|timeline|behind on|vacant|tenant|"
                        r"repairs?|condition|inherited|probate|asap|by (the )?\w+|max|min|"
                        r"zip|door|proof of funds|arv|as-is|need to|want to|looking for)\b", re.I)
_COMMIT = re.compile(r"\b(i'?ll|we'?ll|i will|we will|i can|we can|let me|i'?ve|sending|send you|"
                     r"get you|set up|schedule|follow up)\b", re.I)
_OBJECTION = re.compile(r"\b(too low|not enough|no thanks|not interested|already (have|sold)|"
                        r"scam|who are you|how did you|not selling|low ?ball)\b", re.I)


def _sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text or "") if s.strip()]


def record(email: str, direction: str, body: str, *, persona: str = "", name: str = "",
           subject: str = "", role: str = "", phase: str = "") -> dict:
    """Append a message and re-derive conversation state. direction = 'in' | 'out'."""
    rec = load(email)
    c = rec["contact"]
    if name and not c.get("name"): c["name"] = name
    if role: c["role"] = role
    if phase: c["phase"] = phase
    rec["messages"].append({"dir": direction, "ts": _now(), "persona": persona,
                            "subject": subject, "body": (body or "")[:2000]})
    st = rec["state"]
    qs = [q.strip() for q in _Q.findall(body or "") if len(q.strip()) > 8][:6]
    if direction == "in":
        # their questions become OUR to-answer; their facts get logged; close our open Qs
        for q in qs:
            if q not in st["their_open_qs"]:
                st["their_open_qs"].append(q)
        for s in _sentences(body):
            if _FACT_HINT.search(s) and s not in st["facts"]:
                st["facts"].append(s[:200])
            if _OBJECTION.search(s) and s not in st["objections"]:
                st["objections"].append(s[:160])
        st["our_open_qs"] = []  # they replied -> assume our prior asks are addressed; re-ask only if needed
        rec["rapport"]["sentiment"] = "negative" if st["objections"] else "engaged"
    else:  # out
        if persona and persona not in st.setdefault("personas_seen", []):
            st["personas_seen"].append(persona)   # this persona has now introduced
        for q in qs:
            if q not in st["our_open_qs"]:
                st["our_open_qs"].append(q)
        for s in _sentences(body):
            if _COMMIT.search(s) and s not in st["commitments"]["ours"]:
                st["commitments"]["ours"].append(s[:160])
        st["their_open_qs"] = []  # we answered them this send
    rec["next_action"] = _next_action(rec)
    _save(email, rec)
    _feed_brain(rec)
    return rec


def _next_action(rec: dict) -> str:
    st = rec["state"]
    if st["their_open_qs"]:
        return f"ANSWER their open question: {st['their_open_qs'][0][:80]}"
    last = rec["messages"][-1]["dir"] if rec["messages"] else None
    if last == "in":
        return "RESPOND: they replied and are waiting on us"
    if st["our_open_qs"]:
        return f"AWAIT their answer to: {st['our_open_qs'][0][:80]}"
    return "follow-up cadence (no open threads)"


def context_pack(email: str) -> dict:
    """Everything a reply should be built from: who, what we know, what's OPEN, what NOT
    to repeat, the next move. This is how the conversation stays intelligent."""
    rec = load(email)
    st = rec["state"]
    outbound = [m for m in rec["messages"] if m["dir"] == "out"]
    return {
        "to": rec["contact"]["email"], "name": rec["contact"].get("name"),
        "role": rec["contact"].get("role"), "phase": rec["contact"].get("phase"),
        "message_count": len(rec["messages"]),
        "personas_already_introduced": st.get("personas_seen", []),  # don't re-introduce
        "must_answer": st["their_open_qs"],            # their questions -> answer these
        "we_already_asked": st["our_open_qs"],         # don't re-ask verbatim
        "facts_we_know": st["facts"],                  # reference for rapport
        "our_commitments": st["commitments"]["ours"],  # honor these
        "objections": st["objections"],
        "do_not_repeat": [m.get("subject", "") for m in outbound][-3:],
        "rapport": rec["rapport"]["sentiment"],
        "next_action": rec["next_action"],
    }


def _feed_brain(rec: dict) -> None:
    """Each relationship is a brain note (local-first), cross-referenceable. The portfolio."""
    try:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
        import rex_master_pipeline as r
        c = rec["contact"]; st = rec["state"]
        who = c.get("name") or c.get("email")
        r.log_blinko(
            f"Relationship: {who} ({c.get('role') or 'contact'}, {len(rec['messages'])} msgs)",
            f"Phase {c.get('phase')}. Next: {rec['next_action']}. "
            f"Facts: {' | '.join(st['facts'][:3])}. Open(theirs): {' | '.join(st['their_open_qs'][:2])}. "
            f"Our commitments: {' | '.join(st['commitments']['ours'][:2])}. "
            f"#hive/relationship #hive/wholesale")
    except Exception:
        pass


if __name__ == "__main__":
    if "--show" in sys.argv:
        i = sys.argv.index("--show"); em = sys.argv[i+1] if i+1 < len(sys.argv) else ""
        print(json.dumps(load(em), indent=2))
    elif "--context" in sys.argv:
        i = sys.argv.index("--context"); em = sys.argv[i+1] if i+1 < len(sys.argv) else ""
        print(json.dumps(context_pack(em), indent=2))
    else:
        print(__doc__)
