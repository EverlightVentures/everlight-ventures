"""resend_guard -- shared rule: Resend sends only to external, non-DNC candidates.

Per owner directive (2026-04-23): agents do NOT email the owner or internal
company aliases. Owner-bound status updates go to Slack, not Resend.

Per owner directive (2026-05-04 -- Streubel BBB incident): anyone on the DNC
list (Do-Not-Contact) MUST never receive ANY outbound Resend traffic, ever,
regardless of bypass flags. Adding a recipient to DNC is a permanent, append-
only action; only manual JSON edit can remove.

Any script sending through Resend (branded_mailer.send_branded_email, the
rex_utils direct send, etc.) MUST call assert_safe_recipient() first.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable


class OwnerEmailBlocked(RuntimeError):
    """Raised when a Resend send would hit an owner or internal address."""


class DoNotContactBlocked(RuntimeError):
    """Raised when a Resend send would hit a DNC-listed recipient. NEVER bypassable."""


# Explicit blocks -- the owner's personal inbox and owner-bound business aliases.
_OWNER_EMAILS = {
    "1m.rich.gee@gmail.com",
    "rich.gee@everlightventures.io",
    "rich@everlightventures.io",
    "owner@everlightventures.io",
    "admin@everlightventures.io",
    "ceo@everlightventures.io",
    "me@everlightventures.io",
    "founder@everlightventures.io",
}

# Regex catch-alls for owner-ish patterns.
_OWNER_PATTERNS = [
    re.compile(r"rich[._]?gee@", re.I),
    re.compile(r"^(owner|admin|ceo|founder|me|personal)@everlightventures\.io$", re.I),
]


def _bypass_enabled() -> bool:
    # Escape hatch for one-off, audited sends (manual test runs, recovery).
    return os.environ.get("RESEND_ALLOW_OWNER") == "1"


def is_owner_recipient(addr: str) -> bool:
    if not addr:
        return False
    a = addr.strip().lower()
    if a in _OWNER_EMAILS:
        return True
    return any(p.search(a) for p in _OWNER_PATTERNS)


def assert_external_recipient(to: str | Iterable[str]) -> None:
    """Raise OwnerEmailBlocked if any recipient is the owner / internal.

    Slack is the owner-comms channel; Resend is for outbound to the world.
    """
    if _bypass_enabled():
        return
    recipients = [to] if isinstance(to, str) else list(to)
    for addr in recipients:
        if is_owner_recipient(addr):
            raise OwnerEmailBlocked(
                f"Refusing to Resend to owner/internal address '{addr}'. "
                "Owner status updates belong in Slack, not email. "
                "Set RESEND_ALLOW_OWNER=1 to override for audited manual sends."
            )


# ---- DNC enforcement (added 2026-05-04, Streubel BBB incident) ----

_DNC_PATHS = [
    "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json",
    str(Path.home() / "AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"),
]
_OPTOUT_PATHS = [
    "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json",
    str(Path.home() / "AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json"),
]


def _load_dnc_emails() -> set[str]:
    """Load all DNC + opted-out emails from canonical files. Fail-closed: empty set on read error means BLOCK SUSPECTS."""
    emails: set[str] = set()
    for path in _DNC_PATHS:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    for entry in json.load(f) or []:
                        e = (entry.get("email") or "").strip().lower()
                        if e:
                            emails.add(e)
                break
        except Exception:
            continue
    for path in _OPTOUT_PATHS:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    for entry in json.load(f) or []:
                        e = (entry.get("email") or "").strip().lower()
                        if e:
                            emails.add(e)
                break
        except Exception:
            continue
    return emails


def is_dnc_recipient(addr: str) -> bool:
    if not addr:
        return False
    return addr.strip().lower() in _load_dnc_emails()


def assert_not_dnc(to: str | Iterable[str]) -> None:
    """Hard block on DNC. NOT bypassable by RESEND_ALLOW_OWNER. NEVER overrideable."""
    recipients = [to] if isinstance(to, str) else list(to)
    dnc = _load_dnc_emails()
    for addr in recipients:
        a = (addr or "").strip().lower()
        if a in dnc:
            raise DoNotContactBlocked(
                f"BLOCKED: '{addr}' is on the Do-Not-Contact list. "
                "This block is permanent and cannot be bypassed. "
                "If you believe this is in error, contact the operator. "
                "DNC list is at compliance/dnc_list.json + opted_out_emails.json."
            )


def assert_safe_recipient(to: str | Iterable[str]) -> None:
    """Run BOTH guards: external (owner-block) AND DNC. The single canonical entry point.

    Every Resend send path SHOULD call this instead of assert_external_recipient alone.
    """
    assert_not_dnc(to)
    assert_external_recipient(to)


__all__ = [
    "OwnerEmailBlocked",
    "DoNotContactBlocked",
    "assert_external_recipient",
    "assert_not_dnc",
    "assert_safe_recipient",
    "is_owner_recipient",
    "is_dnc_recipient",
]
