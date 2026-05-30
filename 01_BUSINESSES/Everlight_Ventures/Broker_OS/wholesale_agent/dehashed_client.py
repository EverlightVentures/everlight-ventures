#!/usr/bin/env python3
"""
dehashed_client.py -- turn a name/phone/address into a REAL email via DeHashed.

This is the piece that replaces permutation GUESSES (firstname.lastname@gmail.com)
with REAL emails tied to the person from breach corpora. It is the email-resolution
source for the O-cent layer once an operator DeHashed key is configured.

Operator decision 2026-05-29: Rich (licensed PI) signed up for DeHashed; this is the
unlock for the "thousands of TN addresses we can't contact" problem.

Design discipline (prove-real / no-placeholder):
  - If no key is configured -> returns configured=False + empty emails. NEVER fabricates.
  - Every returned email is tagged source="dehashed" so downstream can NEVER confuse a
    real breach-sourced email with a permutation guess.
  - Network/parse errors -> returned in the dict, never raised, never silently faked.

Config (in /root/.config/everlight/secrets.env, chmod 600, NEVER the repo):
  DEHASHED_API_KEY=...           # required
  DEHASHED_EMAIL=...             # required for v1 (basic-auth account email)
  DEHASHED_API_VERSION=v1|v2     # default v1; flip to v2 if the account uses the new API

Stdlib only (runs on the phone proot -- no pip).

CLI:
  python3 dehashed_client.py --probe --name "Jane Doe" --city Memphis --state TN
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

V1_URL = "https://api.dehashed.com/search"
V2_URL = "https://api.dehashed.com/v2/search"
V2_INFO_URL = "https://api.dehashed.com/v2/info/user"
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# emails we never treat as a real contact even if a breach row carries them
_JUNK_DOMAINS = {"example.com", "test.com", "faisalman.com", "email.com"}


def is_configured() -> bool:
    return bool(os.environ.get("DEHASHED_API_KEY", "").strip())


def _street_of(address: str) -> str:
    """Street portion of an address (number + street), dropping city/state/zip.
    '1596  GABAY ST, MEMPHIS, TN 38106' -> '1596 GABAY ST'. This is the unique
    selector DeHashed matches on."""
    street = re.split(r"[,]", address or "")[0]
    return re.sub(r"\s+", " ", street).strip()


def _build_query(name="", phone="", address="", city="", state="") -> str:
    """ONE field per query (DeHashed v2 rejects multi-field AND). Selector priority,
    strongest first:
      address (a property street is ~unique) > phone (unique) > name (common = noisy).
    Proven 2026-05-29: address:"1596 gabay" returns the exact owner + relatives with
    real emails; name:"Toby Jones" returns 1,209 wrong people worldwide.
    """
    street = _street_of(address)
    if street:
        return f'address:"{street}"'
    if phone:
        digits = re.sub(r"\D", "", phone)
        if digits:
            return f"phone:{digits}"
    if name:
        return f'name:"{name.strip()}"'
    return ""


def _http_json(url: str, *, headers: dict, data: bytes | None = None) -> dict:
    """Single chokepoint for the HTTP call -- easy to mock in tests."""
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _first(v) -> str:
    """DeHashed v2 returns every field as an ARRAY (e.g. "name": ["Jane"]).
    Return the first scalar, tolerating a plain string too."""
    if isinstance(v, (list, tuple)):
        return str(v[0]) if v else ""
    return str(v) if v else ""


def _extract_emails(payload: dict, query_name: str = "") -> list[dict]:
    """Pull distinct real emails from DeHashed entries, with the row's corroborating
    fields so identity_verifier can score them against the known owner.

    v2 entries carry array fields: "email": ["a@b.com", ...], "name": [...], etc.
    """
    out: dict[str, dict] = {}
    for e in (payload.get("entries") or payload.get("results") or []):
        if not isinstance(e, dict):
            continue
        emails = e.get("email")
        if isinstance(emails, str):
            emails = [emails]
        if not isinstance(emails, (list, tuple)):
            continue
        for raw in emails:
            email = (str(raw) if raw else "").strip().lower()
            if not email or not _EMAIL_RE.match(email):
                continue
            if email.split("@")[-1] in _JUNK_DOMAINS:
                continue
            if email not in out:
                out[email] = {
                    "email": email,
                    "source": "dehashed",
                    "name": _first(e.get("name")),
                    "phone": _first(e.get("phone")),
                    "address": _first(e.get("address")),
                    "database": _first(e.get("database_name")) or _first(e.get("obtained_from")),
                }
    return list(out.values())


def account_info() -> dict:
    """Validate the key + read credit balances WITHOUT spending a search credit
    (GET /v2/info/user). Returns {configured, ok, info, error}. Never raises."""
    out = {"configured": is_configured(), "ok": False, "info": {}, "error": ""}
    if not out["configured"]:
        out["error"] = "DEHASHED_API_KEY not set"
        return out
    api_key = os.environ["DEHASHED_API_KEY"].strip()
    try:
        out["info"] = _http_json(
            V2_INFO_URL,
            headers={"Dehashed-Api-Key": api_key, "Accept": "application/json"},
        )
        out["ok"] = True
    except urllib.error.HTTPError as e:
        out["error"] = f"http_{e.code}"
    except Exception as e:
        out["error"] = f"{type(e).__name__}:{str(e)[:80]}"
    return out


def search(name="", phone="", address="", city="", state="", size=20) -> dict:
    """Return {configured, query, emails:[...], total, balance, error}.
    emails are REAL (breach-sourced), each tagged source='dehashed'. Never raises.
    """
    result = {"configured": is_configured(), "query": "", "emails": [],
              "total": 0, "balance": None, "error": ""}
    if not result["configured"]:
        result["error"] = "DEHASHED_API_KEY not set"
        return result

    q = _build_query(name=name, phone=phone, address=address, city=city, state=state)
    result["query"] = q
    if not q:
        result["error"] = "empty query (need name/phone/address)"
        return result

    api_key = os.environ["DEHASHED_API_KEY"].strip()
    # v2 is the current API (POST + Dehashed-Api-Key header, just the key). v1 (basic
    # auth, needs DEHASHED_EMAIL) kept as a fallback only.
    version = os.environ.get("DEHASHED_API_VERSION", "v2").strip().lower()
    try:
        if version == "v2":
            # Current API (confirmed from DeHashed v2 docs 2026-05-29): POST /v2/search,
            # Dehashed-Api-Key header, JSON body, 1 credit per search regardless of size.
            headers = {"Dehashed-Api-Key": api_key, "Content-Type": "application/json",
                       "Accept": "application/json"}
            body = json.dumps({"query": q, "page": 1, "size": size,
                               "de_dupe": True}).encode()
            payload = _http_json(V2_URL, headers=headers, data=body)
        else:
            email = os.environ.get("DEHASHED_EMAIL", "").strip()
            if not email:
                result["error"] = "v1 needs DEHASHED_EMAIL (or set DEHASHED_API_VERSION=v2)"
                return result
            token = base64.b64encode(f"{email}:{api_key}".encode()).decode()
            url = f"{V1_URL}?query={urllib.parse.quote(q)}&size={size}"
            headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
            payload = _http_json(url, headers=headers)
    except urllib.error.HTTPError as e:
        result["error"] = f"http_{e.code}"
        return result
    except Exception as e:  # network / json / anything -- degrade, never crash
        result["error"] = f"{type(e).__name__}:{str(e)[:80]}"
        return result

    result["emails"] = _extract_emails(payload, name)
    result["total"] = int(payload.get("total") or len(result["emails"]))
    result["balance"] = payload.get("balance")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="")
    ap.add_argument("--phone", default="")
    ap.add_argument("--address", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--state", default="")
    ap.add_argument("--check", action="store_true", help="validate key + show credits (0 credits)")
    ap.add_argument("--probe", action="store_true", help="run one live query (uses 1 credit)")
    args = ap.parse_args()

    if not is_configured():
        print("DeHashed NOT configured. Set DEHASHED_API_KEY in "
              "/root/.config/everlight/secrets.env, then re-run with --check.")
        return 1

    if args.check:
        r = account_info()
        print(json.dumps(r, indent=2))
        return 0 if r["ok"] else 2
    if not args.probe:
        print("Configured. Add --probe to run a live query (consumes 1 credit).")
        return 0
    r = search(name=args.name, phone=args.phone, address=args.address,
               city=args.city, state=args.state)
    print(json.dumps(r, indent=2))
    return 0 if not r["error"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
