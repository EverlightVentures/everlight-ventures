"""http_client.py -- canonical outbound HTTP wrapper for the Hive.

Why this exists: 50+ Hive scripts make outbound HTTP calls (Supabase, Slack,
Resend, Anthropic, Perplexity, Blinko, Cloudflare itself). Most use stdlib
urllib defaults, which sends User-Agent: Python-urllib/3.x. Any tightened
Cloudflare WAF rule that filters known-bot UAs will block the entire Hive.
This wrapper sets a single canonical UA, adds sane timeout + retry defaults,
auto-injects Cloudflare Access Service-Token headers when the target host
is one of our protected ev subdomains, and appends one audit line per call.

Three flavors covering the three patterns already in the codebase:
    request_urllib(...)    stdlib only, the branded_mailer.py pattern
    request_requests(...)  requests.Session, the broker_orchestrator pattern
    AsyncClient            httpx.AsyncClient subclass, the MCP-server pattern

All three share:
    - User-Agent: EverLight-Hive/1.0 (+https://everlightventures.io/bots)
    - 30s default timeout
    - 3-retry exponential backoff (1s, 2s, 4s) on 5xx + connection errors
    - CF-Access headers auto-added when cf_access.needs_access(url) is True
    - Per-call audit line to _logs/http_client.jsonl

The audit log is the receipt trail per feedback_prove_real_not_simulated: we
can prove which agent made which outbound call when, and whether it succeeded.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cf_access

USER_AGENT = "EverLight-Hive/1.0 (+https://everlightventures.io/bots)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
RETRY_BACKOFF = [1.0, 2.0, 4.0]

AUDIT_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/http_client.jsonl")

log = logging.getLogger("http_client")


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int
    attempts: int
    error: str = ""

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8") or "null")

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _audit(rec: dict[str, Any]) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except Exception as exc:
        log.warning("http_client: audit log write failed: %s", exc)


def _merge_headers(headers: Optional[dict[str, str]], url: str) -> dict[str, str]:
    final = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        final.update(headers)
    final = cf_access.merge_with_access(final, url)
    return final


def _should_retry(status: int) -> bool:
    return status == 0 or status >= 500


def request_urllib(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    caller: str = "unknown",
) -> Response:
    """stdlib-only HTTP request. Use this when you cannot add requests/httpx
    as a dependency (e.g. inside branded_mailer.py)."""
    final_headers = _merge_headers(headers, url)
    started = time.monotonic()
    last_error = ""
    last_status = 0
    last_body = b""
    last_resp_headers: dict[str, str] = {}
    attempts = 0
    for attempt in range(retries):
        attempts = attempt + 1
        try:
            req = Request(url, data=body, method=method.upper(), headers=final_headers)
            with urlopen(req, timeout=timeout) as resp:
                last_status = resp.status
                last_body = resp.read()
                last_resp_headers = dict(resp.headers.items())
                last_error = ""
                if not _should_retry(last_status):
                    break
        except HTTPError as exc:
            last_status = exc.code
            try:
                last_body = exc.read()
            except Exception:
                last_body = b""
            last_resp_headers = dict(exc.headers.items()) if exc.headers else {}
            last_error = f"HTTP {exc.code}"
            if not _should_retry(last_status):
                break
        except URLError as exc:
            last_status = 0
            last_error = f"URLError: {exc.reason}"
        except Exception as exc:
            last_status = 0
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt + 1 < retries:
            time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])

    elapsed_ms = int((time.monotonic() - started) * 1000)
    response = Response(
        status=last_status,
        body=last_body,
        headers=last_resp_headers,
        elapsed_ms=elapsed_ms,
        attempts=attempts,
        error=last_error,
    )
    _audit({
        "ts": datetime.now(timezone.utc).isoformat(),
        "client": "urllib",
        "caller": caller,
        "method": method.upper(),
        "url": url,
        "status": response.status,
        "elapsed_ms": response.elapsed_ms,
        "attempts": response.attempts,
        "error": response.error,
        "cf_access": cf_access.needs_access(url),
    })
    return response


def request_requests(*args: Any, **kwargs: Any) -> Response:
    """requests-backed wrapper. Lazy-imports requests so this module loads
    on hosts without it."""
    try:
        import requests  # type: ignore
    except ImportError as exc:
        raise RuntimeError("requests not installed; use request_urllib instead") from exc

    url: str = args[0] if args else kwargs.pop("url")
    method: str = kwargs.pop("method", "GET").upper()
    headers = _merge_headers(kwargs.pop("headers", None), url)
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    retries = kwargs.pop("retries", DEFAULT_RETRIES)
    caller = kwargs.pop("caller", "unknown")
    json_body = kwargs.pop("json", None)
    data = kwargs.pop("data", None)
    params = kwargs.pop("params", None)

    started = time.monotonic()
    last_status = 0
    last_body = b""
    last_headers: dict[str, str] = {}
    last_error = ""
    attempts = 0

    session = requests.Session()
    for attempt in range(retries):
        attempts = attempt + 1
        try:
            r = session.request(
                method, url, headers=headers, timeout=timeout,
                json=json_body, data=data, params=params,
            )
            last_status = r.status_code
            last_body = r.content
            last_headers = dict(r.headers.items())
            last_error = ""
            if not _should_retry(last_status):
                break
        except Exception as exc:
            last_status = 0
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt + 1 < retries:
            time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])

    elapsed_ms = int((time.monotonic() - started) * 1000)
    response = Response(
        status=last_status, body=last_body, headers=last_headers,
        elapsed_ms=elapsed_ms, attempts=attempts, error=last_error,
    )
    _audit({
        "ts": datetime.now(timezone.utc).isoformat(),
        "client": "requests", "caller": caller, "method": method, "url": url,
        "status": response.status, "elapsed_ms": response.elapsed_ms,
        "attempts": response.attempts, "error": response.error,
        "cf_access": cf_access.needs_access(url),
    })
    return response


def get_async_client(caller: str = "unknown", **kwargs: Any):
    """Returns an httpx.AsyncClient pre-configured with canonical UA, timeout,
    and a per-request hook that injects CF-Access headers + audits. Lazy-
    imports httpx; callers that don't need async can ignore this."""
    try:
        import httpx  # type: ignore
    except ImportError as exc:
        raise RuntimeError("httpx not installed; use request_urllib or request_requests") from exc

    base_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    base_headers.update(kwargs.pop("headers", {}) or {})
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

    async def _request_audit_hook(request: "httpx.Request") -> None:
        merged = cf_access.merge_with_access(dict(request.headers), str(request.url))
        for k, v in merged.items():
            request.headers[k] = v

    async def _response_audit_hook(response: "httpx.Response") -> None:
        _audit({
            "ts": datetime.now(timezone.utc).isoformat(),
            "client": "httpx_async", "caller": caller,
            "method": response.request.method, "url": str(response.request.url),
            "status": response.status_code,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "cf_access": cf_access.needs_access(str(response.request.url)),
        })

    return httpx.AsyncClient(
        headers=base_headers,
        timeout=timeout,
        event_hooks={"request": [_request_audit_hook], "response": [_response_audit_hook]},
        **kwargs,
    )


def _self_test() -> int:
    """Hit a known-good public endpoint and prove the audit log lands."""
    pre_lines = AUDIT_LOG.read_text().count("\n") if AUDIT_LOG.exists() else 0
    r = request_urllib("https://httpbin.org/headers", caller="self_test", retries=1, timeout=10)
    post_lines = AUDIT_LOG.read_text().count("\n") if AUDIT_LOG.exists() else 0
    if not r.ok:
        print(f"FAIL: status={r.status} error={r.error}")
        return 1
    body = r.json()
    sent_ua = body.get("headers", {}).get("User-Agent", "")
    if USER_AGENT not in sent_ua:
        print(f"FAIL: canonical UA not sent (got {sent_ua!r})")
        return 2
    if post_lines <= pre_lines:
        print("FAIL: audit log line not appended")
        return 3
    print(f"PASS: status={r.status} ua={sent_ua!r} audit_lines={post_lines}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
