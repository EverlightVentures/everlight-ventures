"""state_reply_router -- route inbound seller replies to per-state queues.

Single seam between the global mail/IMAP fetchers (broker_gmail_monitor.py,
rex_negotiator.py) and the per-state agents (Marvin TN, Daria TX, Atlas GA,
Jasper FL, Stella MO, Cleo OH, Phin AZ).

The router does NOT respond to the seller. It deposits a reply envelope as
JSON in /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/state_routing/
queues/{STATE}/inbound/, then posts a Slack tag to the designated agent so
the per-state inbox loop picks it up.

Address detection order:
  1. explicit `state_code` arg (caller already knows)
  2. property dict {state, zip} fields
  3. ZIP -> state via metro_zips lookup in state_agents.json
  4. address regex (US 2-letter state token)
  5. fallback to "marcus_cole" / Marcus inbox

Any reply with no detected state lands in the fallback queue and triggers
a Slack ping in #war-room for human triage. Nothing is dropped silently.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/state_routing")
REGISTRY_PATH = ROOT / "state_agents.json"
QUEUES_ROOT = ROOT / "queues"
FALLBACK_QUEUE = ROOT / "queues" / "_fallback" / "inbound"

US_STATE_RE = re.compile(r"\b([A-Z]{2})\b\s*(\d{5})?")
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")

log = logging.getLogger("state_reply_router")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


_REGISTRY_CACHE: dict[str, Any] | None = None
_ZIP_INDEX: dict[str, str] | None = None


def _load_registry() -> dict[str, Any]:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            _REGISTRY_CACHE = json.load(f)
    return _REGISTRY_CACHE


def _load_zip_index() -> dict[str, str]:
    """Build {zip_prefix_5 -> state_code} from the registry once."""
    global _ZIP_INDEX
    if _ZIP_INDEX is None:
        idx: dict[str, str] = {}
        for state, cfg in _load_registry().get("states", {}).items():
            for z in cfg.get("metro_zips", []):
                idx[z] = state
        _ZIP_INDEX = idx
    return _ZIP_INDEX


def _detect_state(reply: dict[str, Any]) -> tuple[str | None, str]:
    """Return (state_code, detection_method). state_code may be None."""
    explicit = reply.get("state_code")
    if explicit:
        return explicit.upper(), "explicit"

    prop = reply.get("property") or {}
    if isinstance(prop, dict) and prop.get("state"):
        return str(prop["state"]).upper(), "property.state"
    if isinstance(prop, dict) and prop.get("zip"):
        zip_idx = _load_zip_index()
        z5 = str(prop["zip"])[:5]
        if z5 in zip_idx:
            return zip_idx[z5], "property.zip"

    blob = " ".join(
        str(reply.get(k, "")) for k in ("subject", "snippet", "body", "address")
    )
    z_match = ZIP_RE.search(blob)
    if z_match:
        zip_idx = _load_zip_index()
        z5 = z_match.group(1)
        if z5 in zip_idx:
            return zip_idx[z5], "regex.zip"

    s_match = US_STATE_RE.search(blob)
    if s_match:
        candidate = s_match.group(1)
        if candidate in _load_registry().get("states", {}):
            return candidate, "regex.state"

    return None, "fallback"


def _agent_for(state_code: str | None) -> dict[str, Any]:
    reg = _load_registry()
    if state_code and state_code in reg.get("states", {}):
        cfg = reg["states"][state_code]
        return {
            "agent": cfg.get("agent"),
            "agent_id": cfg.get("agent_id"),
            "agent_email": cfg.get("agent_email"),
            "agent_slack": cfg.get("agent_slack"),
            "status": cfg.get("status"),
            "compliance_flags": cfg.get("compliance_flags", []),
        }
    return {
        "agent": reg["fallback"]["agent"],
        "agent_id": reg["fallback"]["agent_id"],
        "agent_email": reg["fallback"]["agent_email"],
        "agent_slack": "#war-room",
        "status": "fallback",
        "compliance_flags": [],
    }


def _queue_path_for(state_code: str | None) -> Path:
    if state_code and state_code in _load_registry().get("states", {}):
        path = QUEUES_ROOT / state_code / "inbound"
    else:
        path = FALLBACK_QUEUE
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_envelope(reply: dict[str, Any], state: str | None, agent: dict[str, Any], detection: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    msg_id = reply.get("msg_id") or reply.get("id") or "noid"
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(msg_id))[:40]
    fname = f"{ts}_{safe_id}.json"
    queue = _queue_path_for(state)
    envelope = {
        "_router_version": 1,
        "_routed_at": datetime.now(timezone.utc).isoformat(),
        "_routed_state": state,
        "_routed_method": detection,
        "_routed_agent": agent,
        "reply": reply,
    }
    out = queue / fname
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    log.info("Routed reply to %s queue: %s (state=%s, method=%s)", state or "FALLBACK", fname, state, detection)
    return out


def _slack_notify(envelope_path: Path, state: str | None, agent: dict[str, Any], reply: dict[str, Any]) -> None:
    """Best-effort Slack tag. Uses branded_slack if importable, else logs only."""
    try:
        sys.path.insert(0, "/AA_MY_DRIVE")
        from content_tools.branded_slack import post_branded_slack  # type: ignore

        title = f"Inbound reply -> {agent.get('agent_id', 'fallback')}"
        body_lines = [
            f"From: {reply.get('from', 'unknown')}",
            f"Subject: {reply.get('subject', '(no subject)')}",
            f"State: {state or 'UNDETECTED'}",
            f"Queue: {envelope_path}",
        ]
        if state and agent.get("compliance_flags"):
            body_lines.append("Gates: " + ", ".join(agent["compliance_flags"]))
        body = "\n".join(body_lines)
        channel = "#wholesale-deals" if state else "#war-room"
        post_branded_slack(
            channel=channel,
            title=title,
            body=body,
            category="deal" if state else "alert",
            agent=agent.get("agent_id", "state_reply_router"),
        )
    except Exception as e:  # pragma: no cover - best effort
        log.warning("Slack notify skipped (%s)", e)


def route_reply(reply: dict[str, Any]) -> dict[str, Any]:
    """Public entry point. `reply` is a dict with at least:
      from, subject, snippet, msg_id  (keys may be missing; router handles it)
    Optional hints:
      state_code, property.state, property.zip, address

    Returns a summary dict the caller can log:
      { state, method, agent_id, queue_path }
    """
    state, method = _detect_state(reply)
    agent = _agent_for(state)
    envelope = _write_envelope(reply, state, agent, method)
    _slack_notify(envelope, state, agent, reply)
    return {
        "state": state,
        "method": method,
        "agent_id": agent.get("agent_id"),
        "queue_path": str(envelope),
    }


def route_replies(replies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in replies:
        try:
            out.append(route_reply(r))
        except Exception as e:
            log.exception("Failed to route reply: %s", e)
            out.append({"error": str(e), "from": r.get("from")})
    return out


# ---------------------------------------------------------------------------
# CLI
#   echo '{"from":"...", "subject":"...", "address":"... TN 38106"}' \
#     | python3 state_reply_router.py
# ---------------------------------------------------------------------------

def _main_cli() -> int:
    if sys.stdin.isatty():
        print(
            "state_reply_router: pipe a JSON reply dict (or list) on stdin. "
            "See module docstring for fields.",
            file=sys.stderr,
        )
        return 2
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON on stdin: {e}", file=sys.stderr)
        return 2
    if isinstance(payload, dict):
        result = route_reply(payload)
    elif isinstance(payload, list):
        result = route_replies(payload)
    else:
        print("Expected JSON object or list", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
