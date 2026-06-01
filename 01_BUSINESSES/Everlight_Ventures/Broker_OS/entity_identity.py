"""
Canonical legal-entity identity for Everlight Ventures Broker OS.

SINGLE SOURCE OF TRUTH for the contracting party named in every contract,
addendum, and outbound sender identity.

Human source of truth:
    01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/BUSINESS_ENTITY_STATUS.md
This module is the MACHINE MIRROR of that document. They must agree.

THE SINGLE FLIP POINT
---------------------
While the California LLC is in reinstatement-pending status, the business is a
sole proprietorship and every contract is signed by Richard Gee personally.
When the LLC is reinstated, flip ENTITY_STATUS to "llc" below and update the
reinstatement date in BUSINESS_ENTITY_STATUS.md -- every contract, the generator,
and the sender identity follow automatically from this one change. Do NOT
re-edit individual contracts to switch entities; that is exactly the drift that
the 2026-06-01 stress test (Kill List #1) flagged as a FATAL, deal-sinking bug.

Enforced by entity_guard.py (fail-closed): no contract template, the generator,
or the sender-identity config may name a contracting party other than the one
this module declares current.
"""

# === THE FLIP POINT =========================================================
ENTITY_STATUS = "sole_prop"   # "sole_prop" | "llc"
# ============================================================================

TRADE_NAME = "Everlight Ventures"   # brand / d/b/a -- always allowed, never a party on its own

# --- Sole proprietorship (CURRENT posture) ---------------------------------
SOLE_PROP_LEGAL_NAME = "Richard Gee, an individual, doing business as Everlight Ventures"
SOLE_PROP_INLINE     = "Richard Gee d/b/a Everlight Ventures"

# --- Future entity (post-reformation; NOT yet formed) ----------------------
# Per operator (2026-06-01): the entity will be reformed in NEVADA and named
# "Everlight Ventures" -- a HOLDING COMPANY over the other ventures (reformed
# from the current "Everlight Logistics"). IMPORTANT: a holding company should
# NOT sign operating contracts itself (liability segregation). If kept as a true
# holding co, the wholesale OPERATING party should be a subsidiary LLC under it,
# not the holding company. Confirm the operating entity with counsel BEFORE
# flipping ENTITY_STATUS to "llc" and update LLC_LEGAL_NAME accordingly.
LLC_LEGAL_NAME = "Everlight Ventures LLC, a Nevada limited liability company"
LLC_INLINE     = "Everlight Ventures LLC"

if ENTITY_STATUS == "sole_prop":
    ENTITY_LEGAL_NAME = SOLE_PROP_LEGAL_NAME
    ENTITY_INLINE     = SOLE_PROP_INLINE
    ENTITY_IS_LLC     = False
elif ENTITY_STATUS == "llc":
    ENTITY_LEGAL_NAME = LLC_LEGAL_NAME
    ENTITY_INLINE     = LLC_INLINE
    ENTITY_IS_LLC     = True
else:
    raise ValueError("entity_identity: ENTITY_STATUS must be 'sole_prop' or 'llc', got %r" % ENTITY_STATUS)

# Forbidden contracting-party strings, by posture. These are the drift variants
# the stress test catalogued. The guard fails closed if any appears in a
# signable artifact while the given posture is current.
_FORBIDDEN_WHILE_SOLE_PROP = [
    "Everlight Logistics LLC",
    "Everlight Ventures, LLC",
    "Everlight Ventures LLC",
    "Everlight Ventures Wholesale Acquisitions, LLC",
    "Everlight Ventures Wholesale Acquisitions LLC",
    "Marquise Smith",
]
_FORBIDDEN_WHILE_LLC = [
    "Everlight Logistics LLC",
    "Everlight Ventures Wholesale Acquisitions, LLC",
    "Marquise Smith",
    # While the LLC is the party, the sole-prop signing form is the wrong party:
    "Richard Gee, an individual",
]

FORBIDDEN_ENTITY_STRINGS = (
    _FORBIDDEN_WHILE_SOLE_PROP if not ENTITY_IS_LLC else _FORBIDDEN_WHILE_LLC
)


def signatory_block(role: str = "BUYER") -> str:
    """Canonical signature block for a contract party (ASSIGNOR / FINDER / BUYER)."""
    return (
        "%s -- %s\n"
        "By: ____________________________\n"
        "Name: Richard Gee%s\n"
        "Date: __________"
    ) % (role.upper(), ENTITY_LEGAL_NAME, "" if not ENTITY_IS_LLC else ", Managing Member")


if __name__ == "__main__":
    print("ENTITY_STATUS     :", ENTITY_STATUS)
    print("ENTITY_LEGAL_NAME :", ENTITY_LEGAL_NAME)
    print("ENTITY_INLINE     :", ENTITY_INLINE)
    print("FORBIDDEN         :", FORBIDDEN_ENTITY_STRINGS)
