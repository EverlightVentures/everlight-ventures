#!/usr/bin/env python3
"""cf_security_apply.py -- Cloudflare Access + WAF orchestrator for everlightventures.io.

Why this exists: Cloudflare reported 463 security threats in the last month
against the everlightventures.io zone. Five tunnel subdomains (hub, reports,
intel, blinko, api) sit behind Cloudflare Tunnel with ZERO authentication
in front of them. This script creates Cloudflare Access policies in front of
each one, issues a Service Token for the Hive, and adds 5 WAF Custom Rules.

Default mode is --status: prints what's currently provisioned + what the
plan would change. Nothing is mutated until --apply is passed explicitly.
This respects the doctrine of "verify before destroy" and "operator
confirmation before shared-state changes".

Auth: prefers a scoped CF_API_TOKEN env var. Falls back to the Global API
Key (CLOUDFLARE_API_KEY + CLOUDFLARE_EMAIL) which is what the workspace
.env currently holds. The Global Key is a security antipattern -- once
Rich creates a scoped Account-level token (Access:Edit + Zone:Edit +
WAF:Edit) and saves it as CF_API_TOKEN, this script switches automatically.

Usage:
    python3 cf_security_apply.py --status
    python3 cf_security_apply.py --plan-only
    python3 cf_security_apply.py --apply         # mutates! creates 5 Access apps + 1 Service Token + 5 WAF rules
    python3 cf_security_apply.py --rotate-token  # issue fresh Service Token (existing one stays valid)

Per feedback_prove_real_not_simulated: every API call appends to
_logs/cf_security_apply.jsonl with status + duration so we can prove what ran.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "content_tools"))
from env_loader import load_env  # noqa: E402
from http_client import request_urllib  # noqa: E402

load_env()

API_ROOT = "https://api.cloudflare.com/client/v4"
ZONE_NAME = "everlightventures.io"
SERVICE_TOKEN_NAME = "everlight-hive-bot"
AUDIT_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/cf_security_apply.jsonl")

PROTECTED_SUBDOMAINS = [
    {"sub": "hub",     "purpose": "Master Hub / Ultra Mind UI"},
    {"sub": "reports", "purpose": "Branded reports + analytics"},
    {"sub": "intel",   "purpose": "Intel Center static content"},
    {"sub": "blinko",  "purpose": "RAG knowledge base"},
    {"sub": "api",     "purpose": "MCP HTTP bridge for agents"},
]

WAF_RULES = [
    {
        "description": "ev/block-cms-and-secret-probes",
        "expression": '(http.request.uri.path contains "/wp-admin/" or http.request.uri.path contains "/wp-login.php" or http.request.uri.path eq "/.env" or http.request.uri.path contains "/.git/")',
        "action": "block",
    },
    {
        "description": "ev/rate-limit-api-subdomain",
        "expression": '(http.host eq "api.everlightventures.io")',
        "action": "managed_challenge",
        "ratelimit": {"characteristics": ["ip.src"], "period": 60, "requests_per_period": 30, "mitigation_timeout": 600},
    },
    {
        "description": "ev/geoblock-zero-customer-countries",
        "expression": '(ip.geoip.country in {"CN" "RU" "KP" "IR"})',
        "action": "block",
    },
    {
        "description": "ev/challenge-empty-or-stale-bot-uas",
        "expression": '(http.host ne "everlightventures.io") and (http.user_agent eq "" or lower(http.user_agent) contains "python-urllib" or lower(http.user_agent) contains "curl/" or lower(http.user_agent) contains "scrapy")',
        "action": "managed_challenge",
    },
    {
        "description": "ev/challenge-esign-non-browser-post",
        "expression": '(http.host eq "esign.everlightventures.io" and http.request.method eq "POST" and not lower(http.user_agent) contains "mozilla")',
        "action": "managed_challenge",
    },
]


_AUTH_MODE_CACHE: dict[str, str] = {}


def _candidate_auth_headers() -> list[tuple[str, dict[str, str]]]:
    """Returns ordered list of (mode_name, headers) to try. First success wins
    and is cached so subsequent calls skip the probe."""
    out: list[tuple[str, dict[str, str]]] = []
    token = os.environ.get("CF_API_TOKEN", "").strip()
    if token:
        out.append(("bearer-CF_API_TOKEN", {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}))
    key = os.environ.get("CLOUDFLARE_API_KEY", "").strip()
    email = os.environ.get("CLOUDFLARE_EMAIL", "").strip()
    if key:
        out.append(("bearer-CLOUDFLARE_API_KEY", {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}))
    if email and key:
        out.append(("xauth-global-key", {"X-Auth-Email": email, "X-Auth-Key": key, "Content-Type": "application/json"}))
    if not out:
        raise RuntimeError("Cloudflare auth missing: set CF_API_TOKEN, or CLOUDFLARE_API_KEY (+CLOUDFLARE_EMAIL for Global Key)")
    return out


def _auth_headers() -> dict[str, str]:
    cached = _AUTH_MODE_CACHE.get("headers")
    if cached:
        return json.loads(cached)
    return _candidate_auth_headers()[0][1]


def _audit(rec: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), **rec}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def cf_call(method: str, path: str, body: Optional[dict] = None) -> dict:
    url = API_ROOT + path
    payload = json.dumps(body).encode() if body is not None else None
    last_err = ""
    candidates = _candidate_auth_headers() if "headers" not in _AUTH_MODE_CACHE else [("cached", json.loads(_AUTH_MODE_CACHE["headers"]))]
    for mode, headers in candidates:
        started = time.monotonic()
        resp = request_urllib(url, method=method, headers=headers, body=payload, timeout=20, caller=f"cf_security_apply[{mode}]")
        elapsed_ms = int((time.monotonic() - started) * 1000)
        parsed = resp.json() if resp.body else {}
        ok = resp.ok and (not isinstance(parsed, dict) or parsed.get("success", True))
        _audit({"method": method, "path": path, "status": resp.status, "elapsed_ms": elapsed_ms,
                "auth_mode": mode, "cf_success": parsed.get("success") if isinstance(parsed, dict) else None,
                "cf_errors": parsed.get("errors") if isinstance(parsed, dict) else None})
        if ok:
            _AUTH_MODE_CACHE["headers"] = json.dumps(headers)
            return parsed
        last_err = f"status={resp.status} body={resp.body[:300]!r}"
    raise RuntimeError(f"CF {method} {path} failed (tried {len(candidates)} auth modes): {last_err}")


@dataclass
class CFState:
    zone_id: str = ""
    account_id: str = ""
    existing_apps: list[dict] = field(default_factory=list)
    existing_service_tokens: list[dict] = field(default_factory=list)
    existing_waf_ruleset_id: str = ""
    existing_waf_rules: list[dict] = field(default_factory=list)


def discover_state() -> CFState:
    state = CFState()
    state.account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not state.account_id:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID not set in env")
    zone_resp = cf_call("GET", f"/zones?name={ZONE_NAME}")
    zones = zone_resp.get("result") or []
    if not zones:
        raise RuntimeError(f"zone {ZONE_NAME} not found on this account")
    state.zone_id = zones[0]["id"]
    apps_resp = cf_call("GET", f"/accounts/{state.account_id}/access/apps")
    state.existing_apps = apps_resp.get("result") or []
    tokens_resp = cf_call("GET", f"/accounts/{state.account_id}/access/service_tokens")
    state.existing_service_tokens = tokens_resp.get("result") or []
    try:
        ruleset_resp = cf_call("GET", f"/zones/{state.zone_id}/rulesets/phases/http_request_firewall_custom/entrypoint")
        ruleset = ruleset_resp.get("result") or {}
        state.existing_waf_ruleset_id = ruleset.get("id", "")
        state.existing_waf_rules = ruleset.get("rules") or []
    except RuntimeError:
        state.existing_waf_ruleset_id = ""
        state.existing_waf_rules = []
    return state


def render_status(state: CFState, operator_email: Optional[str]) -> str:
    lines = []
    lines.append(f"Zone: {ZONE_NAME}  id={state.zone_id[:10]}...")
    lines.append(f"Account: {state.account_id[:10]}...")
    lines.append("")
    lines.append("ACCESS APPS for protected subdomains:")
    have = {a.get("domain", "").lower() for a in state.existing_apps}
    for spec in PROTECTED_SUBDOMAINS:
        domain = f'{spec["sub"]}.{ZONE_NAME}'
        present = "PROTECTED" if domain in have else "OPEN"
        marker = "[OK]" if domain in have else "[MISSING]"
        lines.append(f"  {marker} {domain:35s} {present:10s} -- {spec['purpose']}")
    lines.append("")
    lines.append("SERVICE TOKENS:")
    matching = [t for t in state.existing_service_tokens if t.get("name") == SERVICE_TOKEN_NAME]
    if matching:
        for t in matching:
            lines.append(f"  [OK] {t.get('name')}  client_id={t.get('client_id','')[:12]}...  exp={t.get('expires_at','')}")
    else:
        lines.append(f"  [MISSING] {SERVICE_TOKEN_NAME}  (will create on --apply)")
    lines.append("")
    lines.append("WAF CUSTOM RULES (zone-level):")
    have_desc = {r.get("description", "") for r in state.existing_waf_rules}
    for rule in WAF_RULES:
        present = "[OK]" if rule["description"] in have_desc else "[MISSING]"
        lines.append(f"  {present} {rule['description']:50s} action={rule['action']}")
    if operator_email:
        lines.append("")
        lines.append(f"Operator email for Access allowlist: {operator_email}")
    lines.append("")
    lines.append(f"Audit log: {AUDIT_LOG}")
    return "\n".join(lines)


def apply_service_token(state: CFState) -> tuple[str, str, bool]:
    """Returns (client_id, client_secret_or_empty, newly_created)."""
    matching = [t for t in state.existing_service_tokens if t.get("name") == SERVICE_TOKEN_NAME]
    if matching:
        return matching[0].get("client_id", ""), "", False
    resp = cf_call("POST", f"/accounts/{state.account_id}/access/service_tokens",
                   body={"name": SERVICE_TOKEN_NAME, "duration": "8760h"})
    result = resp.get("result") or {}
    return result.get("client_id", ""), result.get("client_secret", ""), True


def apply_access_app(state: CFState, sub_spec: dict, operator_email: str, service_client_id: str) -> bool:
    domain = f'{sub_spec["sub"]}.{ZONE_NAME}'
    have = {a.get("domain", "").lower() for a in state.existing_apps}
    if domain in have:
        return False
    app_resp = cf_call("POST", f"/accounts/{state.account_id}/access/apps", body={
        "name": f"ev-{sub_spec['sub']}",
        "domain": domain,
        "type": "self_hosted",
        "session_duration": "24h",
        "auto_redirect_to_identity": False,
    })
    app_id = (app_resp.get("result") or {}).get("id", "")
    include_rules: list[dict] = []
    if operator_email:
        include_rules.append({"email": {"email": operator_email}})
    if service_client_id:
        include_rules.append({"service_token": {"token_id": service_client_id}})
    if not include_rules:
        include_rules = [{"everyone": {}}]
    cf_call("POST", f"/accounts/{state.account_id}/access/apps/{app_id}/policies", body={
        "name": "allow-operator-and-hive",
        "decision": "allow",
        "include": include_rules,
    })
    return True


def apply_waf_rules(state: CFState) -> int:
    have_desc = {r.get("description", "") for r in state.existing_waf_rules}
    new_rules = [r for r in WAF_RULES if r["description"] not in have_desc]
    if not new_rules:
        return 0
    payload_rules = list(state.existing_waf_rules) + [{k: v for k, v in r.items()} for r in new_rules]
    if state.existing_waf_ruleset_id:
        cf_call("PUT", f"/zones/{state.zone_id}/rulesets/{state.existing_waf_ruleset_id}",
                body={"rules": payload_rules})
    else:
        cf_call("POST", f"/zones/{state.zone_id}/rulesets", body={
            "name": "Everlight WAF custom rules",
            "kind": "zone", "phase": "http_request_firewall_custom",
            "rules": payload_rules,
        })
    return len(new_rules)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="default; print current CF state vs plan")
    ap.add_argument("--apply", action="store_true", help="mutate: create missing Access apps + Service Token + WAF rules")
    ap.add_argument("--rotate-token", action="store_true", help="issue a fresh Service Token (existing stays valid)")
    ap.add_argument("--operator-email", default=os.environ.get("EV_OPERATOR_EMAIL", ""),
                    help="email for Access allowlist (default: EV_OPERATOR_EMAIL env)")
    args = ap.parse_args()

    if not any([args.status, args.apply, args.rotate_token]):
        args.status = True

    try:
        state = discover_state()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.status:
        print(render_status(state, args.operator_email or None))
        return 0

    if args.rotate_token:
        resp = cf_call("POST", f"/accounts/{state.account_id}/access/service_tokens",
                       body={"name": f"{SERVICE_TOKEN_NAME}-{datetime.now().strftime('%Y%m%d')}", "duration": "8760h"})
        result = resp.get("result") or {}
        print("New Service Token issued. Save these in .env (secret printed ONCE):")
        print(f"  CF_ACCESS_CLIENT_ID={result.get('client_id','')}")
        print(f"  CF_ACCESS_CLIENT_SECRET={result.get('client_secret','')}")
        print("Existing tokens remain valid until you revoke them in the dashboard.")
        return 0

    if args.apply:
        if not args.operator_email:
            print("ERROR: --apply requires --operator-email or EV_OPERATOR_EMAIL set", file=sys.stderr)
            return 2
        print("Provisioning Cloudflare security perimeter...")
        client_id, client_secret, created = apply_service_token(state)
        if created:
            print()
            print(f"Service Token created. SAVE THESE NOW (secret shown once):")
            print(f"  CF_ACCESS_CLIENT_ID={client_id}")
            print(f"  CF_ACCESS_CLIENT_SECRET={client_secret}")
            print()
        else:
            print(f"Service Token already exists: client_id={client_id[:12]}...")
        state = discover_state()
        new_apps = 0
        for spec in PROTECTED_SUBDOMAINS:
            if apply_access_app(state, spec, args.operator_email, client_id):
                new_apps += 1
                print(f"  + Access app created for {spec['sub']}.{ZONE_NAME}")
        added_waf = apply_waf_rules(state)
        print(f"Apply complete: {new_apps} Access apps, {added_waf} WAF rules created.")
        print("Verify with: curl -I https://hub.everlightventures.io/  (expect Cloudflare Access challenge)")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
