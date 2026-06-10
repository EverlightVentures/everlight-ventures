"""recipient_register.py -- system-wide voice register classifier.

Per HARD LAW feedback_voice_register_by_recipient (2026-05-15):
voice scales to the reader, not the sender. Every outbound email
across every pipeline (wholesale seller + buyer, AI Consulting,
Onyx POS, Hive Mind SaaS, vendor, regulator, press) routes through
this classifier to pick the right register before send.

The classifier reads the recipient's profile and returns one of:
    operator | warm | peer | consultative | professional_direct

The returned register is fed to the persona renderer, which picks
the right variant of the persona's voice (warm Piper vs operator
Piper, etc.). The persona identity stays; the texture changes.

Source of truth for the registers themselves:
    /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/knowledge/brand_voice.md

Used by:
    content_tools/branded_mailer.py (auto-classify if not passed)
    wholesale_agent/rex_*.py (explicit classify per lead)
    consulting/outreach.py (when AI Consulting outbound goes live)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Register = Literal["operator", "warm", "peer", "consultative", "professional_direct"]

VALID_REGISTERS: tuple[Register, ...] = (
    "operator", "warm", "peer", "consultative", "professional_direct",
)


@dataclass(frozen=True)
class RecipientProfile:
    """Anything we know about the recipient at send time. All fields optional.

    The classifier degrades gracefully: with zero signals, it falls back to
    the pipeline default. Each known signal sharpens the choice.
    """
    email: str
    pipeline: str = "wholesale_seller"           # routing key, see brand_voice.md table
    deed_count: Optional[int] = None             # wholesale: multi-deed -> operator
    has_court_filings: bool = False              # wholesale: chancery history -> operator
    is_llc_owner: bool = False                   # wholesale: LLC -> peer or operator
    is_long_term_owner: Optional[bool] = None    # wholesale: warm/operator split signal
    is_first_time_seller: Optional[bool] = None  # wholesale: warm signal
    is_inheritance: bool = False                 # wholesale: warm signal
    domain_class: Optional[str] = None           # "corporate" | "nonprofit" | "gov" | "edu" | "personal"
    role_title: Optional[str] = None             # if known: "Founder", "GP", "Partner", etc.
    is_existing_buyer: bool = False              # Chris @ Mid-South etc.
    prior_engagement: Optional[str] = None       # "none" | "replied" | "negotiating" | "closed"
    explicit_register: Optional[Register] = None # operator override on the lead record
    signals: list[str] = field(default_factory=list)  # free-form extras


PIPELINE_DEFAULTS: dict[str, Register] = {
    "wholesale_seller":          "warm",
    "wholesale_seller_investor": "operator",
    "wholesale_buyer":           "peer",
    "ai_consulting":             "consultative",
    "onyx_pos":                  "consultative",
    "hive_mind_saas":            "consultative",
    "publishing":                "warm",
    "vendor":                    "professional_direct",
    "regulator":                 "professional_direct",
    "press":                     "professional_direct",
}


def classify(profile: RecipientProfile) -> Register:
    """Return the register to use for this recipient.

    Decision order:
        1. Explicit override on the lead record (operator's intent wins).
        2. Vendor / regulator / press pipelines -> professional_direct, no overrides.
        3. Wholesale-seller pipeline: investor signals -> operator; warm signals -> warm.
        4. Wholesale-buyer pipeline: always peer.
        5. AI Consulting / SaaS / POS: senior signals -> operator/peer; else consultative.
        6. Fallback: pipeline default from PIPELINE_DEFAULTS.
    """
    # 1. Explicit override wins.
    if profile.explicit_register in VALID_REGISTERS:
        return profile.explicit_register  # type: ignore[return-value]

    pipeline = profile.pipeline

    # 2. Hard pipelines.
    if pipeline in {"vendor", "regulator", "press"}:
        return "professional_direct"

    # 3. Wholesale seller: investor vs distressed split.
    if pipeline.startswith("wholesale_seller"):
        # Investor signals -> operator register.
        if (profile.deed_count or 0) >= 4:
            return "operator"
        if profile.has_court_filings:
            return "operator"
        if profile.is_llc_owner:
            return "operator"
        if "investor_multi_deed" in profile.signals:
            return "operator"

        # Warm-leaning signals.
        if profile.is_first_time_seller or profile.is_inheritance:
            return "warm"
        if profile.is_long_term_owner is True and (profile.deed_count or 0) <= 1:
            return "warm"

        return PIPELINE_DEFAULTS.get(pipeline, "warm")

    # 4. Wholesale buyer relationships are peer-to-peer.
    if pipeline == "wholesale_buyer":
        return "peer"

    # 5. Consulting / SaaS / POS escalations.
    if pipeline in {"ai_consulting", "onyx_pos", "hive_mind_saas"}:
        senior_titles = {"founder", "ceo", "cto", "gp", "partner", "principal", "managing director"}
        if profile.role_title and any(t in profile.role_title.lower() for t in senior_titles):
            return "operator"
        if profile.is_existing_buyer:
            return "peer"
        return "consultative"

    # 6. Fallback.
    return PIPELINE_DEFAULTS.get(pipeline, "warm")


def justify(profile: RecipientProfile, register: Optional[Register] = None) -> str:
    """Return a one-line justification for the chosen register, for audit log."""
    register = register or classify(profile)
    reasons: list[str] = []

    if profile.explicit_register == register:
        return f"register={register}: explicit_override on lead record"

    if profile.pipeline in {"vendor", "regulator", "press"}:
        return f"register={register}: pipeline={profile.pipeline} is always {register}"

    if profile.pipeline.startswith("wholesale_seller"):
        if (profile.deed_count or 0) >= 4:
            reasons.append(f"deed_count={profile.deed_count}>=4")
        if profile.has_court_filings:
            reasons.append("court_filings=yes")
        if profile.is_llc_owner:
            reasons.append("llc_owner=yes")
        if profile.is_first_time_seller:
            reasons.append("first_time_seller=yes")
        if profile.is_inheritance:
            reasons.append("inheritance=yes")

    if profile.pipeline == "wholesale_buyer":
        reasons.append("buyer_pipeline=peer_default")

    if profile.pipeline in {"ai_consulting", "onyx_pos", "hive_mind_saas"}:
        if profile.role_title:
            senior_titles = {"founder", "ceo", "cto", "gp", "partner", "principal", "managing director"}
            if any(t in profile.role_title.lower() for t in senior_titles):
                reasons.append(f"role_title={profile.role_title!r} matches senior list")
        if profile.is_existing_buyer:
            reasons.append("existing_buyer=yes")

    if not reasons:
        reasons.append(f"pipeline_default={PIPELINE_DEFAULTS.get(profile.pipeline, 'warm')}")

    return f"register={register}: {', '.join(reasons)}"


# ----------------------------------------------------------------------------
# Self-test (run directly): verify the Mikal classification matches doctrine.
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    mikal = RecipientProfile(
        email="mhakeem@timemphis.org",
        pipeline="wholesale_seller",
        deed_count=12,
        has_court_filings=True,
        is_long_term_owner=True,
        domain_class="nonprofit",
        signals=["investor_multi_deed", "back_tax_4yr"],
    )
    assert classify(mikal) == "operator", f"Mikal must be operator, got {classify(mikal)}"
    print(f"PASS  Mikal: {justify(mikal)}")

    frayser_inherit = RecipientProfile(
        email="seller@example.com",
        pipeline="wholesale_seller",
        deed_count=1,
        is_first_time_seller=True,
        is_inheritance=True,
    )
    assert classify(frayser_inherit) == "warm"
    print(f"PASS  Frayser inheritance: {justify(frayser_inherit)}")

    chris = RecipientProfile(
        email="chris@midsouthhomebuyers.com",
        pipeline="wholesale_buyer",
        is_existing_buyer=True,
    )
    assert classify(chris) == "peer"
    print(f"PASS  Chris @ Mid-South: {justify(chris)}")

    title_firm = RecipientProfile(
        email="escrow@midsouthtitle.com",
        pipeline="vendor",
    )
    assert classify(title_firm) == "professional_direct"
    print(f"PASS  Mid-South Title: {justify(title_firm)}")

    saas_founder = RecipientProfile(
        email="alex@startup.io",
        pipeline="ai_consulting",
        role_title="Founder & CEO",
    )
    assert classify(saas_founder) == "operator"
    print(f"PASS  SaaS founder: {justify(saas_founder)}")

    smb_eval = RecipientProfile(
        email="owner@cafe.com",
        pipeline="onyx_pos",
    )
    assert classify(smb_eval) == "consultative"
    print(f"PASS  SMB evaluating POS: {justify(smb_eval)}")

    print("\nAll register classifications pass doctrine.")
