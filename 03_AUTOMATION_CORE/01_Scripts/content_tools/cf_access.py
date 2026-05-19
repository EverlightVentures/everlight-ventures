"""cf_access.py -- Cloudflare Access Service Token header helper.

Why this exists: the five private *.everlightventures.io tunnel subdomains
(hub, reports, intel, blinko, api) sit behind Cloudflare Access. Browsers
get a login challenge. Bots and Hive agents authenticate using a Service
Token, which is a CF-Access-Client-Id + CF-Access-Client-Secret header pair
that travels with the request and works from any IP.

Rule: any script calling https://*.everlightventures.io from automation MUST
include access_headers() in its request headers, or the request gets the
Cloudflare login page instead of the protected origin. http_client.py auto-
injects these when the target host matches; raw urllib callers must add them
explicitly via dict-merge.

The env vars CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET live in
03_AUTOMATION_CORE/03_Credentials/.env. Generate the pair once in the
Cloudflare Zero Trust dashboard (Access -> Service Auth -> Service Tokens),
name it everlight-hive-bot, copy values into .env, then attach the token
to each Access App policy as an "Allow" rule.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from env_loader import load_env

load_env()

log = logging.getLogger("cf_access")

EV_PROTECTED_SUFFIX = ".everlightventures.io"
EV_PROTECTED_SUBDOMAINS = frozenset({"hub", "reports", "intel", "blinko", "api"})


@dataclass
class AccessIdentity:
    client_id: str
    client_secret: str
    configured: bool


def load_identity() -> AccessIdentity:
    """Load Service Token identity from environment. Returns configured=False
    when either env var is missing, so callers can degrade instead of crash."""
    cid = os.environ.get("CF_ACCESS_CLIENT_ID", "").strip()
    secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "").strip()
    return AccessIdentity(client_id=cid, client_secret=secret, configured=bool(cid and secret))


def access_headers() -> dict[str, str]:
    """Return the two-header dict expected by Cloudflare Access.

    Returns {} when Service Token is not configured so callers can dict-merge
    without conditional logic. Logs a warning so the gap is loud, not silent.
    """
    ident = load_identity()
    if not ident.configured:
        log.warning("cf_access: Service Token not configured; request will hit Access login page")
        return {}
    return {
        "CF-Access-Client-Id": ident.client_id,
        "CF-Access-Client-Secret": ident.client_secret,
    }


def needs_access(url: str) -> bool:
    """True when the URL points at one of the protected Everlight subdomains.

    Lets http_client decide whether to inject headers automatically without
    blanket-attaching them to every outbound call (which would leak the token
    to third-party APIs).
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host.endswith(EV_PROTECTED_SUFFIX):
        return False
    sub = host.removesuffix(EV_PROTECTED_SUFFIX).strip(".").split(".")[0]
    return sub in EV_PROTECTED_SUBDOMAINS


def merge_with_access(headers: dict[str, str] | None, url: str) -> dict[str, str]:
    """Convenience: merge caller headers with access headers when target needs them.

    Caller headers win on conflict so the protocol stays predictable.
    """
    base: dict[str, str] = dict(headers or {})
    if not needs_access(url):
        return base
    for k, v in access_headers().items():
        base.setdefault(k, v)
    return base


if __name__ == "__main__":
    import json
    ident = load_identity()
    print(json.dumps({
        "configured": ident.configured,
        "client_id_prefix": ident.client_id[:8] + "..." if ident.client_id else "",
        "protected_subdomains": sorted(EV_PROTECTED_SUBDOMAINS),
        "suffix": EV_PROTECTED_SUFFIX,
    }, indent=2))
