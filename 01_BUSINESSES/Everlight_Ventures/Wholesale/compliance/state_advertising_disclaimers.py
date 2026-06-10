"""state_advertising_disclaimers -- per-state required language for marketing.

Imported by pitch_generator and branded_mailer when a piece of outbound
marketing is destined for a specific state. The disclaimer block goes in
the email footer + the SMS opt-out language.

Sources cited per state in DISCLAIMER_NOTES.
"""

DISCLAIMERS = {
    "GA": (
        "Everlight Ventures is a real estate investment firm, not a licensed "
        "real estate broker. We do not represent buyers or sellers in this "
        "transaction. Closings handled by a Georgia real estate attorney."
    ),
    "FL": (
        "Everlight Ventures is a real estate investment firm. We are not a "
        "licensed real estate broker and do not represent you in this "
        "transaction. Florida title and doc-stamp fees disclosed at closing."
    ),
    "TX": (
        "Notice required by Texas Property Code Section 5.008: "
        "Seller will receive a Seller's Disclosure Notice before signing. "
        "Everlight Ventures is a real estate investor, not a licensed broker. "
        "We may assign this contract to a third-party investor before closing."
    ),
    "AZ": (
        "Per Arizona Revised Statutes Section 33-422: applicable disclosures "
        "will be provided. Everlight Ventures is a real estate investment firm, "
        "not a licensed broker."
    ),
    "CA": (
        "Everlight Ventures is a real estate investment firm. NOT a licensed "
        "broker. We do not represent you. California Civil Code Section 2945 "
        "limits our pre-foreclosure outreach (we do not contact CA "
        "pre-foreclosure homeowners)."
    ),
    "MO": (
        "Everlight Ventures is a real estate investment firm, not a licensed "
        "Missouri real estate broker. We may assign this contract to a "
        "third-party investor before closing."
    ),
    "NC": (
        "BLOCKED: NC HB 797 requires real estate brokerage license to "
        "wholesale repeatedly. Everlight Ventures does not currently operate "
        "in North Carolina. This disclaimer should never appear in a real "
        "outbound message; if it does, halt the send."
    ),
    "TN": (
        "Everlight Ventures is a real estate investment firm. Not a licensed "
        "broker. Closings handled by a Tennessee title company. Required "
        "Tennessee disclosures provided before signing."
    ),
}

DISCLAIMER_NOTES = {
    "GA": "GA OCGA Section 43-40 (broker licensing); attorney closing required",
    "FL": "FL Statute 475 (broker licensing); FL doc stamp tax",
    "TX": "Texas Property Code Section 5.008 (seller disclosure); SB 140 (cold SMS blocked)",
    "AZ": "ARS Section 33-422 (affidavit of disclosure)",
    "CA": "CA Civil Code Section 2945 (pre-foreclosure consultant law)",
    "MO": "MO Statute 339 (broker licensing)",
    "NC": "NC HB 797 (wholesale licensing requirement)",
    "TN": "TN Code Title 62 Chapter 13 (broker licensing)",
}


def disclaimer_for(state: str) -> str:
    """Return the disclaimer text for a given state. Empty string if unknown."""
    return DISCLAIMERS.get((state or "").upper().strip(), "")


def disclaimer_html(state: str) -> str:
    """Return HTML-formatted disclaimer block for email footers."""
    text = disclaimer_for(state)
    if not text:
        return ""
    return (
        f"<p style='font-size:11px;color:#888;margin-top:24px;line-height:1.5;'>"
        f"<strong>Required state disclosure ({state.upper()}):</strong> {text}"
        f"</p>"
    )


if __name__ == "__main__":
    import json
    print(json.dumps({s: DISCLAIMERS[s] for s in DISCLAIMERS}, indent=2))
