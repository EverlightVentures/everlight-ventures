"""two_line_dispatch -- route compliance/audit calls to a separate API key.

Three Lines of Defense API-key routing per HIVE_GOVERNANCE_V2.md Section 2.2.
Reads agent role (1L operator / 2L compliance / 3L audit) from agent_id and
returns the correct ANTHROPIC_API_KEY env var name. Until Rich provisions the
second key, both 2L and 3L fall back to the primary key with a warning log
(once per process per tier, to avoid log spam).

Public API
----------
    api_key_for_agent(agent_id) -> tuple[str, str]
        Returns (api_key_value, key_source_name).
        key_source_name is one of:
          - "ANTHROPIC_API_KEY" (1L or fallback)
          - "ANTHROPIC_API_KEY_COMPLIANCE" (2L provisioned)
          - "ANTHROPIC_API_KEY_AUDIT" (3L provisioned)
          - "ANTHROPIC_API_KEY:fallback_for_2L" (2L falling back)
          - "ANTHROPIC_API_KEY:fallback_for_3L" (3L falling back)

    log_destination_for_agent(agent_id) -> str
        Filesystem path template for that tier's log sink. Caller substitutes
        {date}, {timestamp}, {action} themselves -- this returns the template.

    tier_for_agent(agent_id) -> str
        Returns "1L" / "2L" / "3L". Used by audit_log.write_envelope to tag
        the envelope with its source tier.

    reload_classification(path=None) -> None
        Forces re-read of role_classification.json. Used by tests.

Design notes
------------
- Pure stdlib. Single source of truth is role_classification.json next to this
  module. Schema is documented in that file's _doc field.
- Defensive: if the JSON is missing, malformed, or any agent_id is unknown,
  classify as the fallback_tier (default 1L). Never raises.
- The "fallback warning" is rate-limited to one log line per process per tier,
  so a busy 2L/3L workload doesn't generate thousands of identical lines.
- Module-level cache loads once. Tests can call reload_classification().
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Optional

log = logging.getLogger("two_line_dispatch")

_THIS = Path(__file__).resolve()
_DEFAULT_CLASSIFICATION_PATHS = [
    _THIS.parent / "role_classification.json",
    Path("/home/opc/hive_mind/role_classification.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/role_classification.json"),
]

# Module-level state (guarded by _lock)
_lock = threading.Lock()
_classification_cache: Optional[dict] = None
_agent_to_tier_cache: Optional[dict[str, str]] = None
_fallback_warned: set[str] = set()  # tier names we've already warned about


def _load_classification(force: bool = False) -> dict:
    """Load role_classification.json from the first existing path.

    Returns a defensive default classification if no file is readable.
    Cached at module level until reload_classification() is called.
    """
    global _classification_cache, _agent_to_tier_cache
    with _lock:
        if _classification_cache is not None and not force:
            return _classification_cache

        loaded: Optional[dict] = None
        for p in _DEFAULT_CLASSIFICATION_PATHS:
            try:
                if p.exists():
                    with p.open("r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    log.debug("loaded role classification from %s", p)
                    break
            except Exception as exc:
                log.warning("could not read %s: %s", p, exc)

        if loaded is None:
            log.warning(
                "role_classification.json not found on any known path; "
                "falling back to all-1L (no separation)."
            )
            loaded = {
                "tiers": {
                    "1L": {
                        "api_key_env": "ANTHROPIC_API_KEY",
                        "log_destination": "_audit/1L/{agent_id}/{date}/{timestamp}_{action}.json",
                        "agent_ids": [],
                    },
                },
                "fallback_tier": "1L",
            }

        # Build agent_id -> tier index. If an agent_id appears in multiple tiers,
        # the highest tier wins (3L > 2L > 1L) per the doctrine: separation is a
        # privilege boundary; an agent that audits AND operates loses the operator
        # rights for the duration of the audit context.
        idx: dict[str, str] = {}
        for tier_name in ("1L", "2L", "3L"):
            tier = (loaded.get("tiers") or {}).get(tier_name, {})
            for aid in tier.get("agent_ids", []) or []:
                if not isinstance(aid, str) or not aid.strip():
                    continue
                # 3L beats 2L beats 1L
                if aid in idx and _tier_rank(idx[aid]) >= _tier_rank(tier_name):
                    continue
                idx[aid] = tier_name

        _classification_cache = loaded
        _agent_to_tier_cache = idx
        return loaded


def _tier_rank(tier: str) -> int:
    return {"1L": 1, "2L": 2, "3L": 3}.get(tier, 0)


def reload_classification(path: Optional[str] = None) -> None:
    """Force re-read of the classification file. For tests."""
    global _DEFAULT_CLASSIFICATION_PATHS, _classification_cache, _agent_to_tier_cache, _fallback_warned
    with _lock:
        if path:
            _DEFAULT_CLASSIFICATION_PATHS = [Path(path)] + _DEFAULT_CLASSIFICATION_PATHS
        _classification_cache = None
        _agent_to_tier_cache = None
        _fallback_warned = set()
    _load_classification(force=True)


def tier_for_agent(agent_id: str) -> str:
    """Return '1L' / '2L' / '3L' for the given agent_id.

    Unknown agents fall back to fallback_tier (default '1L').
    """
    if not agent_id or not isinstance(agent_id, str):
        return _load_classification().get("fallback_tier", "1L")
    _load_classification()
    idx = _agent_to_tier_cache or {}
    if agent_id in idx:
        return idx[agent_id]
    return _classification_cache.get("fallback_tier", "1L") if _classification_cache else "1L"


def _warn_fallback_once(tier: str) -> None:
    """Log the 'falling back to primary key' warning at most once per tier per process."""
    with _lock:
        if tier in _fallback_warned:
            return
        _fallback_warned.add(tier)
    log.warning(
        "%s API key not provisioned -- falling back to ANTHROPIC_API_KEY. "
        "Provision the dedicated key to activate Three-Lines-of-Defense separation. "
        "See HIVE_GOVERNANCE_V2.md Section 2.2.",
        tier,
    )


def api_key_for_agent(agent_id: str) -> tuple[str, str]:
    """Return (api_key_value, key_source_name) for the given agent_id.

    The key_source_name is the env var the value came from, with a ':fallback_for_X'
    suffix when 2L/3L is falling back to the primary key.

    If even the primary key is missing, returns ('', 'NONE') -- caller should
    handle this gracefully (no Claude call possible).
    """
    classification = _load_classification()
    tier = tier_for_agent(agent_id)
    tier_cfg = (classification.get("tiers") or {}).get(tier, {}) or {}
    desired_env = tier_cfg.get("api_key_env", "ANTHROPIC_API_KEY")

    desired_value = os.environ.get(desired_env, "").strip()
    if desired_value:
        return desired_value, desired_env

    # Fallback path -- 2L or 3L without a dedicated key
    primary = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if tier in ("2L", "3L"):
        _warn_fallback_once(tier)
        if primary:
            return primary, f"ANTHROPIC_API_KEY:fallback_for_{tier}"
        return "", "NONE"

    # 1L: just return primary (or empty)
    if primary:
        return primary, "ANTHROPIC_API_KEY"
    return "", "NONE"


def log_destination_for_agent(agent_id: str) -> str:
    """Return the filesystem path template for that tier's audit log.

    The template contains {agent_id}, {date}, {timestamp}, {action} placeholders.
    The caller (audit_log.write_envelope) substitutes them.
    """
    classification = _load_classification()
    tier = tier_for_agent(agent_id)
    tier_cfg = (classification.get("tiers") or {}).get(tier, {}) or {}
    template = tier_cfg.get(
        "log_destination",
        "_audit/" + tier + "/{agent_id}/{date}/{timestamp}_{action}.json",
    )
    # Substitute agent_id eagerly; caller handles the rest
    try:
        return template.replace("{agent_id}", agent_id)
    except Exception:
        return template


def describe_routing(agent_id: str) -> dict:
    """Diagnostic: returns the full routing picture for one agent.

    Useful in restart_harness and halt_check for visibility.
    Never raises.
    """
    try:
        tier = tier_for_agent(agent_id)
        _key, src = api_key_for_agent(agent_id)
        dest = log_destination_for_agent(agent_id)
        provisioned = (
            src not in ("NONE", "")
            and not src.startswith("ANTHROPIC_API_KEY:fallback_for_")
        )
        return {
            "agent_id": agent_id,
            "tier": tier,
            "api_key_source": src,
            "api_key_provisioned": provisioned,
            "log_destination_template": dest,
        }
    except Exception as exc:
        return {"agent_id": agent_id, "error": f"describe_routing_failed:{exc}"}


# CLI for ops verification: `python3 two_line_dispatch.py <agent_id>`
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) < 2:
        print("usage: python3 two_line_dispatch.py <agent_id> [<agent_id> ...]")
        sys.exit(2)
    for aid in sys.argv[1:]:
        info = describe_routing(aid)
        print(json.dumps(info, indent=2))
