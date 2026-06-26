"""Token Economics OS - Key Registry core.

Agent-readable catalog of every API key. METADATA ONLY. Never the secret value.
Secret values live in secrets_vault.py / Proton; this stores only a pointer in
`value_location` (vault:NAME, proton:NAME, env:NAME, file:PATH).

The validate_registry() guard is the load-bearing safety control: it refuses any
entry that smuggles a real secret-shaped string into the catalog, so the catalog
stays safe to commit and safe for any agent to read.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

DEFAULT_PATH = str(Path(__file__).parent / "registry" / "key_registry.json")


@dataclass
class KeyEntry:
    key_name: str
    project: str
    sub_avenue: str
    provider: str
    owner: str
    created: str
    expires: str | None
    refresh_cadence: str
    monthly_cost_usd: float
    status: str
    value_location: str
    notes: str = ""


def load_registry(path: str = DEFAULT_PATH) -> list[KeyEntry]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        raw = json.load(f)
    return [KeyEntry(**row) for row in raw]


def save_registry(entries: list[KeyEntry], path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)


# ----- metadata-only secret guard -----

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{16,}",
    r"sbp_[A-Za-z0-9_\-]{16,}",
    r"cfat_[A-Za-z0-9_\-]{16,}",
    r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    r"re_[A-Za-z0-9_\-]{16,}",
    r"eyJ[A-Za-z0-9_\-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"AIza[A-Za-z0-9_\-]{30,}",
    r"\b[0-9a-fA-F]{40,}\b",
]
_ALLOWED_PREFIXES = ("vault:", "proton:", "env:", "file:")


def looks_like_secret(value: str) -> bool:
    return any(re.search(p, value or "") for p in SECRET_PATTERNS)


def scan_object_for_secrets(obj, parent_key: str = "root") -> set[str]:
    """Walk any parsed JSON object and return labels of fields holding a secret.

    Catches secrets in dict values AND bare strings inside lists (e.g. a token
    passed as a positional CLI arg), which a values-only walk would miss.
    """
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and looks_like_secret(v):
                found.add(k)
            else:
                found |= scan_object_for_secrets(v, k)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, str) and looks_like_secret(v):
                found.add(f"{parent_key}[]")
            else:
                found |= scan_object_for_secrets(v, parent_key)
    return found


def validate_registry(entries: list[KeyEntry]) -> list[str]:
    out: list[str] = []
    for e in entries:
        vl = e.value_location or ""
        if not vl.startswith(_ALLOWED_PREFIXES):
            out.append(
                f"{e.key_name}: value_location must be a pointer "
                f"({', '.join(_ALLOWED_PREFIXES)}), got '{vl[:12]}...'"
            )
        for fname in ("value_location", "notes", "key_name"):
            if looks_like_secret(getattr(e, fname)):
                out.append(
                    f"{e.key_name}: field '{fname}' holds a secret-shaped string; "
                    "store the value in the vault, keep only a pointer"
                )
    return out


# ----- query + cost rollup -----

def by_project(entries: list[KeyEntry]) -> dict[str, list[KeyEntry]]:
    d: dict[str, list[KeyEntry]] = defaultdict(list)
    for e in entries:
        d[e.project].append(e)
    return dict(d)


def monthly_cost_by_project(entries: list[KeyEntry]) -> dict[str, float]:
    d: dict[str, float] = defaultdict(float)
    for e in entries:
        d[e.project] += float(e.monthly_cost_usd or 0)
    return dict(d)


def expiring_within(entries: list[KeyEntry], days: int, today: str) -> list[KeyEntry]:
    t = date.fromisoformat(today)
    out = []
    for e in entries:
        if not e.expires:
            continue
        if 0 <= (date.fromisoformat(e.expires) - t).days <= days:
            out.append(e)
    return out


if __name__ == "__main__":
    import sys

    entries = load_registry()
    violations = validate_registry(entries)
    if violations:
        print("REGISTRY VIOLATIONS:")
        for v in violations:
            print("  -", v)
        sys.exit(1)
    print(f"Registry OK: {len(entries)} keys across {len(by_project(entries))} projects")
    for proj, cost in sorted(monthly_cost_by_project(entries).items()):
        print(f"  {proj}: ${cost:.2f}/mo")
