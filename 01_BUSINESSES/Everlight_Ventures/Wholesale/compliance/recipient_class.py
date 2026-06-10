"""recipient_class -- classify a recipient email + name + lead context.

This is IRON 1 of the Streubel-4435 backstop suite. The Streubel send went to
dave@municipalfirm.com -- a domain that screamed "law firm / municipal" but our
mailer had no domain-class gate. This module is that gate.

Returns one of:
  - "consumer_residential"  -> ALLOW cold (homeowner consumer email matches lead)
  - "consumer_with_warning" -> ALLOW with extra logging
  - "business_unverified"   -> SOFT BLOCK on cold; ALLOW on warm-reply
  - "attorney_blocked"      -> HARD BLOCK on cold (Streubel class)
  - "government_blocked"    -> HARD BLOCK always
  - "internal_blocked"      -> HARD BLOCK (own-domain recipient)
  - "role_address_blocked"  -> HARD BLOCK on cold (info@, admin@, etc)

Public API:
  classify_recipient(email, name=None, lead_record=None) -> RecipientClass

Design notes
------------
- Pure stdlib. No deps. Runs on phone, Oracle, PC.
- Token data lives in blocked_domain_tokens.json (sibling file). Loaded once,
  re-loadable via reload_tokens() for tests.
- Defensive: if the JSON is missing or malformed, classify everything except
  consumer providers as "business_unverified" (safe default). Never raises.
- Block reasons are plain English so a human can audit a JSONL block log and
  immediately understand why a send was refused.

Audit trail
-----------
Callers should pipe blocks to log_block() which appends a JSON line to
phrase_scrub_blocks.jsonl. The mailer wrapper does this automatically.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("recipient_class")

_THIS = Path(__file__).resolve()
TOKENS_PATHS = [
    _THIS.parent / "blocked_domain_tokens.json",
    Path("/home/opc/wholesale/compliance/blocked_domain_tokens.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/blocked_domain_tokens.json"),
]

PHRASE_SCRUB_PATHS = [
    _THIS.parent / "phrase_scrub_blocks.jsonl",
    Path("/home/opc/wholesale/compliance/phrase_scrub_blocks.jsonl"),
]


# ── Data shapes ────────────────────────────────────────────────────

@dataclass
class RecipientClass:
    """Result of classifying one recipient.

    Attributes:
        class_name:    one of the 7 enum values listed in the module docstring.
        allowed_for:   tuple of budget categories this recipient may receive.
                       Categories are: bulk, nurture, vip_reply, system.
        reason:        plain-English explanation of the classification.
        matched_token: the specific token string that triggered the result
                       (empty for consumer_residential).
        is_hard_block: True for *_blocked classes; False for soft/allowed.
    """
    class_name: str
    allowed_for: tuple[str, ...]
    reason: str
    matched_token: str = ""
    is_hard_block: bool = False
    domain: str = ""
    local_part: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_name": self.class_name,
            "allowed_for": list(self.allowed_for),
            "reason": self.reason,
            "matched_token": self.matched_token,
            "is_hard_block": self.is_hard_block,
            "domain": self.domain,
            "local_part": self.local_part,
        }


# ── Token loader ───────────────────────────────────────────────────

_TOKENS: dict[str, Any] = {}
_TOKENS_LOADED_FROM: str = ""


def _load_tokens() -> dict[str, Any]:
    """Load blocked_domain_tokens.json from the first existing path.

    Returns an empty dict on total failure -- callers must handle the
    empty case (defaults to business_unverified).
    """
    global _TOKENS_LOADED_FROM
    for p in TOKENS_PATHS:
        try:
            if p.exists():
                data = json.loads(p.read_text())
                if isinstance(data, dict):
                    _TOKENS_LOADED_FROM = str(p)
                    return data
        except Exception as exc:
            log.warning("could not parse %s: %s", p, exc)
    log.warning("blocked_domain_tokens.json not found in any known path")
    return {}


def reload_tokens() -> dict[str, Any]:
    """Force-reload the token JSON. Useful in tests and after config edits."""
    global _TOKENS
    _TOKENS = _load_tokens()
    return _TOKENS


_TOKENS = _load_tokens()


def _t(key: str) -> list[str]:
    """Safe getter for a token list. Returns [] when missing."""
    raw = _TOKENS.get(key, [])
    if not isinstance(raw, list):
        return []
    return [str(x).lower() for x in raw if x]


# ── Email parsing ──────────────────────────────────────────────────

def _split_email(email: str) -> tuple[str, str]:
    """Lowercased (local_part, domain). Returns ('', '') on bad input."""
    if not email or "@" not in email:
        return "", ""
    e = email.strip().lower()
    # Strip "Name <addr>" if present
    if "<" in e and ">" in e:
        e = e.split("<", 1)[1].rsplit(">", 1)[0]
    local, _, domain = e.partition("@")
    return local.strip(), domain.strip()


def _domain_matches_pattern(domain: str, pattern: str) -> bool:
    """Match a domain against a pattern token.

    Patterns supported:
      - "*.gov"        -> suffix match on ".gov"
      - ".mil"         -> domain ends with ".mil"
      - ".state."      -> domain contains ".state."
      - "stlouis-mo.gov" -> exact substring within domain
      - "law"          -> raw token; the caller decides containment vs label match
    """
    if not domain or not pattern:
        return False
    p = pattern.strip().lower()
    if p.startswith("*."):
        return domain.endswith(p[1:])  # *.gov -> endswith ".gov"
    if p.startswith("."):
        return domain.endswith(p) or p in domain
    return p in domain


# ── Token classifiers ─────────────────────────────────────────────

def _check_internal(domain: str) -> Optional[str]:
    for tok in _t("internal_block"):
        if domain == tok or domain.endswith("." + tok):
            return tok
    return None


def _check_government(domain: str) -> Optional[str]:
    for tok in _t("hard_block_government"):
        if _domain_matches_pattern(domain, tok):
            return tok
    for tok in _t("hard_block_government_state_local"):
        if _domain_matches_pattern(domain, tok):
            return tok
    return None


def _domain_label_tokens(domain: str) -> list[str]:
    """Return the labels of the domain (e.g. 'foo.bar.law.com' -> ['foo','bar','law','com'])."""
    return [t for t in domain.split(".") if t]


def _check_attorney(domain: str) -> Optional[str]:
    """Block if any DOMAIN LABEL contains an attorney token, OR if the
    full domain contains a known firm token. We match on label-substring
    so 'municipalfirm.com' (Streubel case -- 'municipal' label) trips
    on 'municipal' even though it isn't its own label.
    """
    labels = _domain_label_tokens(domain)
    for tok in _t("hard_block_attorney_tokens_in_domain"):
        for lab in labels:
            if tok in lab:
                return tok
    for tok in _t("hard_block_known_firm_tokens"):
        if tok in domain:
            return tok
    return None


def _check_role_address(local: str) -> Optional[str]:
    """Match a role address token like 'info@' against the local part.
    The token in JSON has a trailing '@' -- we strip it for the prefix check.
    """
    for tok in _t("hard_block_role_addresses"):
        prefix = tok.rstrip("@").lower()
        if not prefix:
            continue
        if local == prefix or local.startswith(prefix + ".") or local.startswith(prefix + "+"):
            return tok
    return None


def _is_consumer_provider(domain: str) -> bool:
    return domain in _t("consumer_email_providers_allow")


def _check_business_signals(local: str, domain: str) -> Optional[str]:
    """Soft signals -- the local part or non-consumer domain hints at a business."""
    for tok in _t("soft_block_business_signals_in_local"):
        if tok in local:
            return tok
    # Non-consumer domain with a generic TLD = unverified business
    if not _is_consumer_provider(domain):
        labels = _domain_label_tokens(domain)
        for tok in _t("soft_block_business_signals_in_local"):
            for lab in labels:
                if tok in lab:
                    return tok
    return None


# ── Main classifier ───────────────────────────────────────────────

def classify_recipient(
    email: str,
    name: Optional[str] = None,
    lead_record: Optional[dict[str, Any]] = None,
) -> RecipientClass:
    """Classify a recipient. Never raises. Returns a RecipientClass."""
    try:
        local, domain = _split_email(email)
        if not domain:
            return RecipientClass(
                class_name="business_unverified",
                allowed_for=("system", "vip_reply"),
                reason="malformed_email_no_domain",
                is_hard_block=False,
                domain=domain,
                local_part=local,
            )

        # 1. Internal own-domain block (highest priority -- never email ourselves)
        if (m := _check_internal(domain)):
            return RecipientClass(
                class_name="internal_blocked",
                allowed_for=("system",),
                reason=f"internal_domain_match:{m}",
                matched_token=m,
                is_hard_block=True,
                domain=domain,
                local_part=local,
            )

        # 2. Government -- never override, even on vip_reply
        if (m := _check_government(domain)):
            return RecipientClass(
                class_name="government_blocked",
                allowed_for=("system",),
                reason=f"government_domain_match:{m}",
                matched_token=m,
                is_hard_block=True,
                domain=domain,
                local_part=local,
            )

        # 3. Attorney / law firm -- vip_reply CAN bypass (response to a
        #    lawyer who wrote in is not solicitation), but cold cannot.
        if (m := _check_attorney(domain)):
            return RecipientClass(
                class_name="attorney_blocked",
                allowed_for=("system", "vip_reply"),
                reason=f"attorney_token_match:{m}",
                matched_token=m,
                is_hard_block=True,
                domain=domain,
                local_part=local,
            )

        # 4. Role address (info@, admin@, etc.) -- block cold; allow vip_reply
        #    because someone may have written in from contact@ legitimately.
        if (m := _check_role_address(local)):
            return RecipientClass(
                class_name="role_address_blocked",
                allowed_for=("system", "vip_reply"),
                reason=f"role_address_match:{m}",
                matched_token=m,
                is_hard_block=True,
                domain=domain,
                local_part=local,
            )

        # 5. Consumer email provider on a domain we trust as residential.
        if _is_consumer_provider(domain):
            # Extra guard: if the local_part contains a business token,
            # downgrade to consumer_with_warning so the send is logged.
            biz_tok = None
            for tok in _t("soft_block_business_signals_in_local"):
                if tok in local:
                    biz_tok = tok
                    break
            if biz_tok:
                return RecipientClass(
                    class_name="consumer_with_warning",
                    allowed_for=("system", "vip_reply", "nurture", "bulk"),
                    reason=f"consumer_provider_but_business_token_in_local:{biz_tok}",
                    matched_token=biz_tok,
                    is_hard_block=False,
                    domain=domain,
                    local_part=local,
                )
            # If a lead_record was passed and the email matches the homeowner
            # contact email on file, that's the strongest possible signal.
            if lead_record and isinstance(lead_record, dict):
                homeowner_email = (
                    lead_record.get("homeowner_email")
                    or lead_record.get("seller_email")
                    or lead_record.get("contact_email")
                    or ""
                ).strip().lower()
                if homeowner_email and homeowner_email == email.strip().lower():
                    return RecipientClass(
                        class_name="consumer_residential",
                        allowed_for=("system", "vip_reply", "nurture", "bulk"),
                        reason="consumer_provider_matches_lead_homeowner",
                        is_hard_block=False,
                        domain=domain,
                        local_part=local,
                    )
            return RecipientClass(
                class_name="consumer_residential",
                allowed_for=("system", "vip_reply", "nurture", "bulk"),
                reason="consumer_email_provider",
                is_hard_block=False,
                domain=domain,
                local_part=local,
            )

        # 6. Non-consumer domain -- soft block. Allow warm-reply, block cold.
        biz_match = _check_business_signals(local, domain)
        return RecipientClass(
            class_name="business_unverified",
            allowed_for=("system", "vip_reply"),
            reason=(
                f"business_signal:{biz_match}" if biz_match
                else "non_consumer_domain_unverified"
            ),
            matched_token=biz_match or "",
            is_hard_block=False,
            domain=domain,
            local_part=local,
        )

    except Exception as exc:
        # Defensive: never let the classifier crash the mailer.
        log.exception("classify_recipient unexpected error: %s", exc)
        return RecipientClass(
            class_name="business_unverified",
            allowed_for=("system", "vip_reply"),
            reason=f"classifier_error:{exc}",
            is_hard_block=False,
        )


# ── Audit log ─────────────────────────────────────────────────────

def _atomic_append_jsonl(path: Path, line: str) -> bool:
    """Append a line to a JSONL file using a tmp+rename copy.

    JSONL append doesn't truly need atomicity, but we use a lock-style
    pattern: read existing -> write new file with appended line -> rename.
    For low-volume audit logs this is safer than a streaming append on
    flaky filesystems (the phone in particular).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = b""
        if path.exists():
            try:
                existing = path.read_bytes()
            except Exception:
                existing = b""
        new_blob = existing + line.encode("utf-8")
        if not new_blob.endswith(b"\n"):
            new_blob += b"\n"
        # Write to tmp in same directory (so rename is atomic on same FS)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=str(path.parent), prefix=".tmp_psb_",
            suffix=".jsonl", delete=False,
        ) as tmp:
            tmp.write(new_blob)
            tmp.flush()
            try:
                os.fsync(tmp.fileno())
            except OSError:
                pass
            tmp_path = tmp.name
        os.replace(tmp_path, str(path))
        return True
    except Exception as exc:
        log.warning("could not append to %s: %s", path, exc)
        return False


def log_block(
    *,
    recipient: str,
    class_name: str,
    reason: str,
    matched_token: str = "",
    budget_category: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> bool:
    """Append a single block event to phrase_scrub_blocks.jsonl.

    Tries every known path; succeeds if any one write lands. Never raises.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "recipient": recipient,
        "class_name": class_name,
        "reason": reason,
        "matched_token": matched_token,
        "budget_category": budget_category,
        "source": "recipient_class",
    }
    if extra:
        try:
            record["extra"] = dict(extra)
        except Exception:
            pass
    try:
        line = json.dumps(record, ensure_ascii=False, default=str)
    except Exception as exc:
        log.warning("could not serialize block record: %s", exc)
        return False

    wrote_any = False
    for p in PHRASE_SCRUB_PATHS:
        if _atomic_append_jsonl(p, line):
            wrote_any = True

    # Append-only audit envelope (HIVE_GOVERNANCE_V2.md Section 4).
    # Every recipient_class block writes a cryptographically chained envelope.
    # Best-effort: a write failure here does NOT mask the underlying block result.
    try:
        from audit_log import write_envelope as _audit_write  # type: ignore
        _audit_write(
            agent_id="recipient_class",
            action_type="outbound.recipient_class_blocked",
            payload={
                "recipient": recipient,
                "class_name": class_name,
                "reason": reason,
                "matched_token": matched_token or "",
                "budget_category": budget_category or "",
                "extra": dict(extra) if extra else {},
                "phrase_scrub_wrote": wrote_any,
            },
        )
    except Exception as _audit_err:
        log.warning("audit_log envelope failed (non-fatal): %s", _audit_err)

    return wrote_any


# ── Mailer integration helper ─────────────────────────────────────

# Categories that may bypass attorney_blocked specifically (responses to
# inbound from a lawyer are not solicitation). Government remains blocked
# for ALL cold/warm/reply categories except `system`.
_VIP_BYPASS_CLASSES = {"attorney_blocked", "role_address_blocked"}


def is_send_allowed(
    email: str,
    *,
    budget_category: str,
    name: Optional[str] = None,
    lead_record: Optional[dict[str, Any]] = None,
) -> tuple[bool, RecipientClass]:
    """The single function the mailer calls. Returns (allowed, classification).

    Decision matrix:
      - system:    ALWAYS allowed (admin/internal). Even own-domain.
      - vip_reply: allowed for everything EXCEPT government_blocked +
                   internal_blocked. Attorney/role can be replied to.
      - nurture / bulk:
          - hard-block classes -> NOT allowed
          - business_unverified -> NOT allowed (soft block on cold)
          - consumer_residential / consumer_with_warning -> allowed

    The caller is expected to log_block() on a False result.
    """
    rc = classify_recipient(email, name=name, lead_record=lead_record)
    cat = (budget_category or "bulk").lower()

    if cat == "system":
        return True, rc  # System mail never blocked here.

    if rc.class_name == "internal_blocked":
        return False, rc  # Never email ourselves except system.

    if rc.class_name == "government_blocked":
        return False, rc  # Never, regardless of category.

    if cat == "vip_reply":
        # vip_reply may answer attorneys and role addresses, but not gov/internal.
        if rc.class_name in _VIP_BYPASS_CLASSES:
            return True, rc
        if rc.class_name in ("consumer_residential", "consumer_with_warning",
                             "business_unverified"):
            return True, rc
        return False, rc

    # nurture / bulk path -- the strict cold-outbound gate
    if rc.is_hard_block:
        return False, rc
    if rc.class_name == "business_unverified":
        return False, rc
    return True, rc


# ── CLI for quick smoke tests ─────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Classify a recipient email")
    ap.add_argument("email")
    ap.add_argument("--name", default=None)
    ap.add_argument("--budget-category", default="bulk",
                    choices=["bulk", "nurture", "vip_reply", "system"])
    args = ap.parse_args()
    allowed, rc = is_send_allowed(
        args.email, budget_category=args.budget_category, name=args.name,
    )
    print(json.dumps({
        "email": args.email,
        "budget_category": args.budget_category,
        "allowed": allowed,
        "classification": rc.to_dict(),
        "tokens_loaded_from": _TOKENS_LOADED_FROM,
    }, indent=2))
    return 0 if allowed else 2


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
