"""
email_confidence_gate.py -- Tier OSINT candidate emails for the wholesale pipeline.

Pure functions, no network, fully testable.

Tiers
-----
TIER_SEND = "send"  -- deliverability verified (HIBP or EmailRep deliverable).
                       Best signal -- highest priority send.
TIER_TRY  = "try"   -- mx_ok and no disqualifying flags (catch-all, disposable,
                       role, duplicate). We send anyway per operator policy.
TIER_SKIP = "skip"  -- would bounce (no MX) OR disqualifying flag. Don't send.

Operator policy (2026-05-27): deliverability-verified is the new bar, not
identity-verified. No direct-mail tier. Send to anything we can deliver.

email_score(candidate, identity_score) formula
----------------------------------------------
Answer: "How deliverable + trustworthy is this email address?"

Base from deliverability:
  +50 if candidate.verified is True (HIBP OR EmailRep deliverable)
  +30 if any source contains "mx_check", "mx_ok", or "mx" (MX exists)
  +0  otherwise

Identity bonus (raises priority, does not gate):
  + min(20, identity_score // 5)     max +20

Email-discovery confidence roll-in:
  + min(20, (candidate.get("confidence") or 0) // 5)   max +20

Penalties (look at sources list; treat any source string containing
"catch", "disposable", "role", "free-tier-suspicious" as a disqualifier):
  -40 if catch-all / disposable / role detected (clamped once per candidate)
  -25 if candidate email appears in the caller-supplied duplicate_emails set
       (same address already enriched on a different lead)

Final score clamped to [0, 100].

tier_for(score, candidate) boundaries
--------------------------------------
  no "mx" in sources at all          -> TIER_SKIP
  candidate.verified is True         -> TIER_SEND
  mx_ok AND score >= 35              -> TIER_TRY
  else                               -> TIER_SKIP
"""
from __future__ import annotations

from typing import Optional

TIER_SEND = "send"
TIER_TRY = "try"
TIER_SKIP = "skip"

_MX_TOKENS = ("mx_check", "mx_ok", "mx")
_DISQUALIFY_TOKENS = ("catch", "disposable", "role", "free-tier-suspicious")


def _has_mx(candidate: dict) -> bool:
    """Return True if any source string on the candidate contains an MX token."""
    sources = candidate.get("sources") or []
    for src in sources:
        src_lower = str(src).lower()
        for tok in _MX_TOKENS:
            if tok in src_lower:
                return True
    return False


def _has_disqualifier(candidate: dict) -> bool:
    """Return True if any source string on the candidate is a disqualifying flag."""
    sources = candidate.get("sources") or []
    for src in sources:
        src_lower = str(src).lower()
        for tok in _DISQUALIFY_TOKENS:
            if tok in src_lower:
                return True
    return False


def email_score(
    candidate: dict,
    identity_score: int,
    duplicate_emails: Optional[set] = None,
) -> int:
    """
    Score a single email candidate.

    Parameters
    ----------
    candidate : dict
        Shape: {"email": str, "confidence": int(0-100)|None,
                "verified": bool, "sources": list[str]}
        "confidence" is from email_discovery (format + MX + breach corroboration).
        "verified" is True when EmailRep reports deliverable OR HIBP has seen it.
    identity_score : int
        0-100 from osint_api profile_depth (raises priority, does not gate).
    duplicate_emails : set[str] | None
        Optional set of email addresses already enriched on other leads. Matching
        candidates receive a -25 penalty.

    Returns
    -------
    int
        Composite score in [0, 100].
    """
    identity_score = max(0, min(100, int(identity_score)))
    verified = bool(candidate.get("verified", False))
    raw_conf = candidate.get("confidence") or 0
    disc_conf = max(0, min(100, int(raw_conf)))

    # Base from deliverability
    if verified:
        base = 50
    elif _has_mx(candidate):
        base = 30
    else:
        base = 0

    # Identity bonus -- max +20
    base += min(20, identity_score // 5)

    # Email-discovery confidence roll-in -- max +20
    base += min(20, disc_conf // 5)

    # Penalties
    if _has_disqualifier(candidate):
        base -= 40

    email_addr = str(candidate.get("email") or "").strip().lower()
    if duplicate_emails and email_addr in {e.strip().lower() for e in duplicate_emails}:
        base -= 25

    return max(0, min(100, base))


def tier_for(score: int, candidate: dict) -> str:
    """
    Map a score + candidate signals to a TIER_* constant.

    Rules (checked in order):
      1. No MX in sources -> TIER_SKIP (would bounce)
      2. candidate.verified is True -> TIER_SEND
      3. MX ok AND score >= 35 -> TIER_TRY
      4. else -> TIER_SKIP
    """
    if not _has_mx(candidate):
        return TIER_SKIP
    if bool(candidate.get("verified", False)):
        return TIER_SEND
    if score >= 35:
        return TIER_TRY
    return TIER_SKIP


def categorize(
    candidates: list[dict],
    identity_score: int,
    duplicate_emails: Optional[set] = None,
) -> dict:
    """
    Score every candidate, pick the best, and return a routing decision.

    Parameters
    ----------
    candidates : list[dict]
        Each item: {"email": str, "confidence": int|None,
                    "verified": bool, "sources": list[str]}
    identity_score : int
        Overall identity confidence from osint_api.
    duplicate_emails : set[str] | None
        Email addresses already enriched on other leads (passed through to
        email_score for the -25 duplicate penalty).

    Returns
    -------
    dict
        {
          "tier": str,          -- TIER_SEND | TIER_TRY | TIER_SKIP
          "best_email": str|None,
          "score": int,         -- score of the best sendable candidate (or 0)
          "reason": str,        -- plain-English explanation
          "ranked": [           -- all candidates, sorted best-first
              {"email": str, "score": int, "tier": str, "verified": bool},
              ...
          ]
        }
    """
    if not candidates:
        return {
            "tier": TIER_SKIP,
            "best_email": None,
            "score": 0,
            "reason": "No email candidates found by OSINT -- nothing to send.",
            "ranked": [],
        }

    ranked = []
    for c in candidates:
        s = email_score(c, identity_score, duplicate_emails=duplicate_emails)
        t = tier_for(s, c)
        ranked.append({
            "email": c.get("email", ""),
            "score": s,
            "tier": t,
            "verified": bool(c.get("verified", False)),
        })

    # Sort: score desc, then verified candidates win ties (True > False)
    ranked.sort(key=lambda x: (x["score"], x["verified"]), reverse=True)

    # Best = highest-scoring non-SKIP candidate
    sendable = [r for r in ranked if r["tier"] != TIER_SKIP]
    if not sendable:
        return {
            "tier": TIER_SKIP,
            "best_email": None,
            "score": 0,
            "reason": (
                f"All {len(candidates)} candidate(s) scored below send threshold "
                f"(no MX or score < 35 on unverified, identity_score={identity_score})."
            ),
            "ranked": ranked,
        }

    best = sendable[0]

    if best["tier"] == TIER_SEND:
        reason = (
            f"Top candidate {best['email']} scored {best['score']}/100 "
            f"(identity_score={identity_score}). Deliverability verified -- "
            "cleared for send."
        )
    else:
        reason = (
            f"Top candidate {best['email']} scored {best['score']}/100 "
            f"(identity_score={identity_score}). MX ok, no disqualifying flags -- "
            "sending per operator deliverability policy."
        )

    return {
        "tier": best["tier"],
        "best_email": best["email"] or None,
        "score": best["score"],
        "reason": reason,
        "ranked": ranked,
    }
