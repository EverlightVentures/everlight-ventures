"""Shared helpers for investigators: HTTP fetch + live_log instrumentation."""
import time
import httpx
from .. import live_log

UA = "Mozilla/5.0 (compatible; EverlightIntel/1.0)"
DEFAULT_TIMEOUT = 8


async def fetch(http: httpx.AsyncClient, url: str, *, timeout: int = DEFAULT_TIMEOUT,
                method: str = "GET") -> tuple[int, str, str | None]:
    """
    HTTP fetch with auto live_log recording. Returns (status_code, text, error).
    Domain is parsed from URL.
    """
    domain = url.split("//", 1)[-1].split("/", 1)[0].split("?", 1)[0]
    try:
        r = await http.request(method, url, timeout=timeout,
                               headers={"User-Agent": UA},
                               follow_redirects=True)
        live_log.record(domain, status_code=r.status_code,
                        bytes_received=len(r.content or b""),
                        method=method)
        return r.status_code, r.text, None
    except httpx.TimeoutException:
        live_log.record(domain, status_code=0, error="timeout", method=method)
        return 0, "", "timeout"
    except Exception as e:
        live_log.record(domain, status_code=0, error=str(e)[:80], method=method)
        return 0, "", str(e)[:80]


async def head(http: httpx.AsyncClient, url: str, timeout: int = 6) -> int:
    """Fast HEAD probe -- enough to mark a domain live_active."""
    domain = url.split("//", 1)[-1].split("/", 1)[0].split("?", 1)[0]
    try:
        r = await http.head(url, timeout=timeout, follow_redirects=True,
                            headers={"User-Agent": UA})
        live_log.record(domain, status_code=r.status_code, method="HEAD")
        return r.status_code
    except Exception as e:
        live_log.record(domain, status_code=0, error=str(e)[:80], method="HEAD")
        return 0


def now_ms() -> int:
    return int(time.time() * 1000)


def detect_kind(target: str) -> str:
    """Heuristic entity classifier -- which investigator type fits the target?"""
    t = target.strip().lower()
    if "@" in t and "." in t.split("@")[-1]:
        return "email"
    if t.startswith(("http://", "https://")) or "." in t and " " not in t:
        return "domain"
    digits = "".join(c for c in t if c.isdigit())
    if len(digits) >= 10 and len(digits) <= 11:
        return "phone"
    if any(w in t for w in (" street", " ave", " rd", " dr ", " blvd", " lane", " ln ")):
        return "address"
    if any(w in t for w in ("inc", "llc", "corp", "ltd", "company", "co.", "group", "holdings")):
        return "company"
    parts = t.split()
    if 2 <= len(parts) <= 4 and all(p.replace("-", "").isalpha() for p in parts):
        return "person"
    return "company"  # safest catch-all -- companies are the broadest investigator coverage
