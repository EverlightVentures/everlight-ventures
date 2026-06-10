"""
dnc_check -- read-only lookup against Wholesale/compliance/dnc_list.json.

Used by intel_enricher to flag any persisted enrichment record with
dnc_blocked=true when the owner matches a DNC entry. This is a KNOWLEDGE
guard, not a CONTACT guard -- the contact guard is `content_tools/resend_guard.py`
which sits in front of every outbound send.

Verified findings can still be COLLECTED on someone on the DNC (we want to
understand the world). But every downstream consumer (pitch_generator, Piper,
branded_mailer) must short-circuit on dnc_blocked=true.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DNC_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json")


@lru_cache(maxsize=1)
def _load_dnc() -> list[dict]:
    if not DNC_PATH.exists():
        return []
    try:
        return json.loads(DNC_PATH.read_text())
    except Exception:
        return []


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def check(*, owner_name: str = "", phone: str = "", email: str = "",
          address: str = "") -> dict:
    """
    Returns:
      {
        "is_dnc": bool,
        "reason": str,        # which signal matched, or '' if not DNC
        "entry_id": str|None, # which dnc_list.json entry matched
      }
    Match logic:
      - email exact (case-insensitive) -> high-confidence DNC
      - phone last-10 digits exact
      - name normalized exact OR fuzzy first+last match
      - address normalized substring match against blocked property_addresses
    """
    entries = _load_dnc()
    if not entries:
        return {"is_dnc": False, "reason": "", "entry_id": None}

    norm_name = _norm(owner_name)
    norm_email = (email or "").strip().lower()
    norm_addr = _norm(address)
    digits = "".join(c for c in (phone or "") if c.isdigit())[-10:]

    for entry in entries:
        if not entry.get("do_not_contact"):
            continue
        if norm_email and entry.get("email") and norm_email == entry["email"].strip().lower():
            return {"is_dnc": True, "reason": f"email_match:{norm_email}", "entry_id": entry.get("id")}
        if digits and entry.get("phone"):
            entry_digits = "".join(c for c in str(entry["phone"]) if c.isdigit())[-10:]
            if entry_digits and entry_digits == digits:
                return {"is_dnc": True, "reason": f"phone_match:{digits}", "entry_id": entry.get("id")}
        if norm_name and entry.get("name"):
            entry_norm = _norm(entry["name"])
            if entry_norm:
                # Direct match
                if entry_norm == norm_name or entry_norm in norm_name or norm_name in entry_norm:
                    return {"is_dnc": True, "reason": f"name_match:{entry['name']}", "entry_id": entry.get("id")}
                # Token-set match: if every token in EITHER name appears in the other,
                # treat as same person (handles middle initials, suffixes, reorder).
                t_entry = set(entry_norm.split())
                t_query = set(norm_name.split())
                if t_entry and t_query:
                    # Drop single-letter tokens (middle initials) before comparing
                    t_entry_main = {t for t in t_entry if len(t) > 1}
                    t_query_main = {t for t in t_query if len(t) > 1}
                    if t_entry_main and t_query_main and (
                        t_entry_main.issubset(t_query) or t_query_main.issubset(t_entry)
                    ):
                        return {"is_dnc": True, "reason": f"name_match_tokens:{entry['name']}", "entry_id": entry.get("id")}
        if norm_addr:
            for blocked in entry.get("property_addresses", []) or []:
                if _norm(blocked) and _norm(blocked) in norm_addr or norm_addr in _norm(blocked):
                    return {"is_dnc": True, "reason": f"address_match:{blocked}", "entry_id": entry.get("id")}

    return {"is_dnc": False, "reason": "", "entry_id": None}


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "David Streubel"
    print(check(owner_name=name, address="4435 Westminster Pl, Saint Louis, MO"))
