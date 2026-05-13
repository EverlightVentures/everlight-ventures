"""
template_lint.py -- startup-time guard against forbidden phrases in pitch templates.

Run on FastAPI app startup. Walks the marketing_pipeline.POSITIONING_ANGLES dict
and pitch_narrative.BODY_TEMPLATES dict, flattens every string, and asserts that
no string contains any phrase from pre_send_phrase_scrub._DEFAULT_BASELINE.

If a violation is found, raises RuntimeError with a clear message naming the
template path + offending phrase. FastAPI startup aborts -- forces the operator
to fix the template before the API can serve traffic.

This is the cheap fix for the "phrase_scrub trip word lurking in a template"
class of bug -- catch it at app boot, not at send time when an operator is
already waiting on a real send.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Make sure content_tools is importable
_CT = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
if str(_CT) not in sys.path:
    sys.path.insert(0, str(_CT))


def _baseline() -> list[str]:
    try:
        from pre_send_phrase_scrub import _DEFAULT_BASELINE  # type: ignore
        return list(_DEFAULT_BASELINE)
    except Exception:
        # Fallback: hardcoded copy. If import fails we still want to scan.
        return [
            "list", "listing", "represent", "your agent", "your broker",
            "commission", "REALTOR", "MLS", "fiduciary", "act on your behalf",
        ]


def _walk(obj, path: str = "") -> list[tuple[str, str]]:
    """Yield (path, string) for every str leaf in a nested dict/list."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_walk(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(_walk(v, f"{path}[{i}]"))
    return out


def _violations(text: str, baseline: list[str]) -> list[str]:
    """Return the list of trip phrases found in `text` (case-insensitive, word-boundary)."""
    found: list[str] = []
    lower = text.lower()
    for phrase in baseline:
        p = phrase.lower()
        # Use word-boundary for single-word phrases so "list" doesn't fire on "listening"
        if " " in p or "'" in p:
            if p in lower:
                found.append(phrase)
        else:
            if re.search(rf"\b{re.escape(p)}\b", lower):
                found.append(phrase)
    return found


def assert_clean() -> None:
    """Walk known template dicts; raise RuntimeError on first violation."""
    baseline = _baseline()
    targets: list[tuple[str, dict]] = []

    try:
        from .marketing_pipeline import POSITIONING_ANGLES
        targets.append(("marketing_pipeline.POSITIONING_ANGLES", POSITIONING_ANGLES))
    except Exception as e:
        print(f"[template_lint] WARN: could not import POSITIONING_ANGLES: {e}",
              file=sys.stderr)

    try:
        from .pitch_narrative import BODY_TEMPLATES
        targets.append(("pitch_narrative.BODY_TEMPLATES", BODY_TEMPLATES))
    except Exception as e:
        print(f"[template_lint] WARN: could not import BODY_TEMPLATES: {e}",
              file=sys.stderr)

    failures: list[str] = []
    for prefix, dct in targets:
        for path, text in _walk(dct, prefix):
            hits = _violations(text, baseline)
            if hits:
                failures.append(f"{path}: {hits}  -- text: {text[:120]!r}")

    if failures:
        msg = (
            "template_lint.assert_clean() FAILED -- "
            f"{len(failures)} forbidden-phrase violation(s) found:\n  "
            + "\n  ".join(failures)
            + "\nFix the offending templates before the API can start. "
            "Baseline lives at content_tools/pre_send_phrase_scrub._DEFAULT_BASELINE."
        )
        raise RuntimeError(msg)

    print(f"[template_lint] OK -- scanned {sum(1 for _ in targets)} template "
          f"sources against {len(baseline)} baseline phrases; no violations.")


if __name__ == "__main__":
    # Allow running standalone: python -m osint_api.template_lint
    assert_clean()
