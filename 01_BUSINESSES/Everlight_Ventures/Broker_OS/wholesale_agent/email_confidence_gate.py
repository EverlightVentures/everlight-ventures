"""
email_confidence_gate.py -- Tier OSINT candidate emails for the wholesale pipeline.

Pure functions, no network, fully testable.

Tiers
-----
TIER_AUTO       (score >= 75)  : agents send automatically
TIER_REVIEW     (55 <= score < 75) : human reviews before send
TIER_DIRECTMAIL (score < 55)   : no email outreach; route to direct mail or deepen OSINT

Score formula
-------------
The score answers: "How confident are we that THIS email reaches THIS homeowner?"

Two independent questions must both be high for the score to be high:
  1. Is this the right person?  --> identity_score (0-100) from osint_api profile_depth
  2. Is this email valid?       --> email_confidence (0-100) from email_discovery candidate

Base blend (70/30 weighted toward identity match because a perfect email for the
wrong person is worthless):
    base = (identity_score * 0.70) + (candidate["confidence"] or 0) * 0.30

Caps and penalties:
  - If candidate is NOT verified deliverable (verified=False): cap at 60
    Rationale: even a strong identity match is useless if the mailbox may bounce.
  - If candidate has no confidence value (confidence is None): treat as 0 and
    apply a -10 penalty (unknown signal is worse than a low-confidence signal).
  - Final score is clamped to [0, 100].

Example:
  identity_score=90, confidence=80, verified=True
    -> base = (90*0.70) + (80*0.30) = 63 + 24 = 87  -> TIER_AUTO
  identity_score=90, confidence=80, verified=False
    -> raw = 87, cap to 60                            -> TIER_REVIEW
  identity_score=60, confidence=50, verified=True
    -> base = (60*0.70) + (50*0.30) = 42 + 15 = 57   -> TIER_REVIEW
  identity_score=60, confidence=None, verified=False
    -> base = (60*0.70) + 0 - 10 = 42 - 10 = 32, cap 60 -> TIER_DIRECTMAIL
"""
from __future__ import annotations

TIER_AUTO = "auto_email"
TIER_REVIEW = "review"
TIER_DIRECTMAIL = "directmail"

_UNVERIFIED_CAP = 60
_NO_CONFIDENCE_PENALTY = 10
_BLEND_IDENTITY = 0.70
_BLEND_EMAIL = 0.30


def email_score(candidate: dict, identity_score: int) -> int:
    """
    Blend the identity match score with the email candidate's own confidence.

    Parameters
    ----------
    candidate : dict
        Shape: {"email": str, "confidence": int(0-100)|None,
                "verified": bool, "sources": list}
        "confidence" is the email-deliverability confidence from email_discovery.
        "verified" signals the email was confirmed deliverable by at least one
        signal (EmailRep deliverable=True or HIBP existence).
    identity_score : int
        0-100 score from profile_depth.score()["overall_score"] representing how
        confident osint_api is that the results belong to the correct homeowner.

    Returns
    -------
    int
        Blended confidence score, 0-100.
    """
    identity_score = max(0, min(100, int(identity_score)))
    confidence = candidate.get("confidence")
    verified = bool(candidate.get("verified", False))

    if confidence is None:
        email_conf = 0
        penalty = _NO_CONFIDENCE_PENALTY
    else:
        email_conf = max(0, min(100, int(confidence)))
        penalty = 0

    base = (identity_score * _BLEND_IDENTITY) + (email_conf * _BLEND_EMAIL) - penalty

    if not verified:
        base = min(base, _UNVERIFIED_CAP)

    return max(0, min(100, round(base)))


def tier_for(score: int) -> str:
    """Map a blended score to a TIER_* constant."""
    if score >= 75:
        return TIER_AUTO
    if score >= 55:
        return TIER_REVIEW
    return TIER_DIRECTMAIL


def categorize(candidates: list[dict], identity_score: int) -> dict:
    """
    Score every candidate, pick the best, and return a routing decision.

    Parameters
    ----------
    candidates : list[dict]
        Each item: {"email": str, "confidence": int|None,
                    "verified": bool, "sources": list}
    identity_score : int
        Overall identity confidence from osint_api.

    Returns
    -------
    dict
        {
          "tier": str,         -- TIER_* constant for routing
          "best_email": str|None,
          "score": int,        -- score of the best candidate
          "reason": str,       -- plain-English explanation
          "ranked": [          -- all candidates, sorted best-first
              {"email": str, "score": int, "tier": str},
              ...
          ]
        }
    """
    if not candidates:
        return {
            "tier": TIER_DIRECTMAIL,
            "best_email": None,
            "score": 0,
            "reason": "No email candidates found by OSINT -- route to direct mail.",
            "ranked": [],
        }

    ranked = []
    for c in candidates:
        s = email_score(c, identity_score)
        ranked.append({
            "email": c.get("email", ""),
            "score": s,
            "tier": tier_for(s),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    best = ranked[0]

    if best["score"] >= 75:
        reason = (
            f"Top candidate {best['email']} scored {best['score']}/100 "
            f"(identity_score={identity_score}). Verified deliverable with high "
            "identity confidence -- cleared for automated send."
        )
    elif best["score"] >= 55:
        reason = (
            f"Top candidate {best['email']} scored {best['score']}/100 "
            f"(identity_score={identity_score}). Moderate confidence -- "
            "recommend human review before send."
        )
    else:
        reason = (
            f"Best candidate {best['email']} scored {best['score']}/100 "
            f"(identity_score={identity_score}). Insufficient confidence for "
            "email outreach -- route to direct mail or deepen OSINT."
        )

    return {
        "tier": best["tier"],
        "best_email": best["email"] or None,
        "score": best["score"],
        "reason": reason,
        "ranked": ranked,
    }
