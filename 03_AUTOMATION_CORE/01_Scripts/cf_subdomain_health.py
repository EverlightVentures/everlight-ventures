#!/usr/bin/env python3
"""cf_subdomain_health.py -- prove the Cloudflare Access perimeter is up.

Why this exists: after cf_security_apply.py --apply puts Cloudflare Access in
front of the 5 private subdomains, we need a recurring receipt that the lock
is actually holding. Before --apply, this script reports every subdomain as
OPEN -- the visceral confirmation of the 463-threat exposure. After --apply,
the same command flips them to PROTECTED. One command, before/after proof.

How it classifies each subdomain:
  PROTECTED  -- request without a Service Token gets a 302 redirect to
                *.cloudflareaccess.com (Access challenge). The lock is holding.
  OPEN       -- request reaches the origin (2xx/4xx/5xx that is NOT an Access
                redirect). Anyone can hit it. This is the pre-apply state.
  TOKEN_OK   -- with the Hive Service Token attached, request passes Access
                and reaches origin. Proves agents can still get through.
  DOWN       -- connection refused / timeout (tunnel offline, not a security
                state).

Run modes:
    python3 cf_subdomain_health.py                # human table
    python3 cf_subdomain_health.py --json         # machine output
    python3 cf_subdomain_health.py --slack        # post branded summary to #hive-alerts
    python3 cf_subdomain_health.py --check-token  # also test Service Token passthrough

Exit code = number of subdomains that SHOULD be protected but are OPEN. 0 means
the perimeter is fully locked (or you haven't applied yet and accept the openness).
Cron-friendly: a non-zero exit after --apply means the lock slipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "content_tools"))
import cf_access  # noqa: E402
from http_client import request_urllib  # noqa: E402

ZONE = "everlightventures.io"
# Subdomains that SHOULD be behind Access after --apply.
SHOULD_PROTECT = ["hub", "reports", "intel", "blinko", "api"]
# Public-by-design: stays open, gets Turnstile not Access.
PUBLIC_OK = ["esign"]


@dataclass
class SubResult:
    subdomain: str
    url: str
    status: int
    classification: str
    should_protect: bool
    token_passthrough: str = "not_tested"
    detail: str = ""


def _classify(url: str, status: int, headers: dict[str, str], error: str) -> str:
    if status == 0:
        return "DOWN"
    location = headers.get("Location", "") or headers.get("location", "")
    if status in (301, 302, 303, 307, 308) and "cloudflareaccess.com" in location.lower():
        return "PROTECTED"
    # Some Access setups return 302 to a /cdn-cgi/access path on same host
    if status in (301, 302, 303, 307, 308) and "/cdn-cgi/access" in location.lower():
        return "PROTECTED"
    return "OPEN"


def probe(subdomain: str, should_protect: bool, check_token: bool) -> SubResult:
    url = f"https://{subdomain}.{ZONE}/"
    # First probe: NO token. We want to see if Access challenges us.
    resp = request_urllib(url, method="GET", headers={}, timeout=10, retries=1,
                          caller="cf_subdomain_health")
    classification = _classify(url, resp.status, resp.headers, resp.error)
    result = SubResult(
        subdomain=subdomain, url=url, status=resp.status,
        classification=classification, should_protect=should_protect,
        detail=resp.error,
    )
    # Second probe: WITH token, only if requested and the subdomain is protected.
    if check_token and classification == "PROTECTED":
        ident = cf_access.load_identity()
        if not ident.configured:
            result.token_passthrough = "no_token_configured"
        else:
            tok_resp = request_urllib(
                url, method="GET",
                headers=cf_access.access_headers(),
                timeout=10, retries=1, caller="cf_subdomain_health[token]",
            )
            tok_class = _classify(url, tok_resp.status, tok_resp.headers, tok_resp.error)
            result.token_passthrough = "passes" if tok_class != "PROTECTED" else "still_blocked"
    return result


def run(check_token: bool) -> list[SubResult]:
    out: list[SubResult] = []
    for sub in SHOULD_PROTECT:
        out.append(probe(sub, True, check_token))
    for sub in PUBLIC_OK:
        out.append(probe(sub, False, check_token))
    return out


def exit_code(results: list[SubResult]) -> int:
    return sum(1 for r in results if r.should_protect and r.classification == "OPEN")


def render_table(results: list[SubResult]) -> str:
    lines = [f"Cloudflare Access health -- {ZONE}", ""]
    lines.append(f"{'SUBDOMAIN':<28} {'HTTP':<6} {'STATE':<10} {'EXPECT':<10} {'TOKEN':<14}")
    lines.append("-" * 72)
    for r in results:
        expect = "protected" if r.should_protect else "public-ok"
        flag = ""
        if r.should_protect and r.classification == "OPEN":
            flag = "  <-- EXPOSED"
        elif r.should_protect and r.classification == "PROTECTED":
            flag = "  ok"
        elif r.classification == "DOWN":
            flag = "  (origin/tunnel offline)"
        lines.append(f"{r.subdomain + '.' + ZONE:<28} {r.status:<6} {r.classification:<10} {expect:<10} {r.token_passthrough:<14}{flag}")
    exposed = exit_code(results)
    down = sum(1 for r in results if r.classification == "DOWN")
    protected = sum(1 for r in results if r.should_protect and r.classification == "PROTECTED")
    lines.append("")
    if down:
        lines.append(f"{down} subdomain(s) DOWN -- origin/tunnel not serving (e5-mother offline or cloudflared down). Cannot assess Access state until the tunnel is up.")
    if exposed:
        lines.append(f"{exposed} of {len(SHOULD_PROTECT)} private subdomains are OPEN (reachable, no Access). Run cf_security_apply.py --apply to lock them.")
    if not down and not exposed:
        lines.append(f"All {protected} private subdomains protected by Cloudflare Access.")
    elif not exposed and not down:
        lines.append("Perimeter clean.")
    return "\n".join(lines)


def post_slack(results: list[SubResult]) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "content_tools"))
        from branded_slack import post_branded_alert  # type: ignore
    except Exception as exc:
        print(f"(slack unavailable: {exc})", file=sys.stderr)
        return
    exposed = exit_code(results)
    severity = "warning" if exposed else "info"
    title = f"Cloudflare perimeter: {exposed} subdomain(s) exposed" if exposed else "Cloudflare perimeter: all locked"
    detail = " | ".join(f"{r.subdomain}={r.classification}" for r in results)
    try:
        post_branded_alert(channel="#hive-alerts", severity=severity, title=title,
                           detail=detail, agent_name="CF Health")
    except Exception as exc:
        print(f"(slack post failed: {exc})", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--slack", action="store_true")
    ap.add_argument("--check-token", action="store_true", help="also test Service Token passthrough on protected subdomains")
    args = ap.parse_args()

    results = run(args.check_token)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(render_table(results))
    if args.slack:
        post_slack(results)
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
