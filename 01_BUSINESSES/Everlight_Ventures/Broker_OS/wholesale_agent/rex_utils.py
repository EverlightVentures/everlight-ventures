"""
Rex Utilities -- retry logic, caching, rate tracking, health checks.

Covers:
- Exponential backoff retry wrapper
- Safe email sending with dead letter queue
- Safe IMAP checking with reconnection
- ATTOM API response caching (7-day TTL per zip)
- ATTOM rate tracking with Slack alerts
- Hot zip code discovery for market expansion
- System health check (Resend, IMAP, ATTOM, Supabase, Slack)
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

logging.basicConfig(level=logging.INFO, format="[Rex Utils %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_utils")

AGENT_DIR = Path(__file__).parent
CACHE_DIR = AGENT_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR = AGENT_DIR / "failed_emails"
FAILED_DIR.mkdir(parents=True, exist_ok=True)

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "Piper Reeves <piper@everlightventures.io>")
REPLY_TO = "piper@everlightventures.io"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# RETRY WRAPPER
# ---------------------------------------------------------------------------

def retry(func: Callable, max_retries: int = 3, delay: float = 5,
          backoff: float = 2.0, exceptions: tuple = (Exception,)) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: callable to execute (no args -- use lambda for partials)
        max_retries: max attempts before giving up
        delay: initial delay in seconds between retries
        backoff: multiplier applied to delay each retry
        exceptions: tuple of exception types to catch

    Returns:
        The return value of func on success.

    Raises:
        The last exception if all retries fail.
    """
    last_error = None
    current_delay = delay

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_error = e
            if attempt < max_retries:
                log.warning(
                    f"Attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {current_delay:.1f}s..."
                )
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                log.error(f"All {max_retries} attempts failed. Last error: {e}")

    raise last_error


# ---------------------------------------------------------------------------
# SAFE EMAIL SENDER (with retry + dead letter queue)
# ---------------------------------------------------------------------------

# Dead-end email domains that will never respond to outreach
DEAD_END_DOMAINS = {
    # Government
    "clevelandohio.gov", "city.cleveland.oh.us", "gov", "state.oh.us",
    "state.tx.us", "state.ga.us", "state.fl.us", "state.mo.us",
    "ci.cleveland.oh.us", "cityofatlanta.gov",
    # Generic government patterns (checked via suffix)
    # Land banks, mayors, city departments
    # Institutions
    "edu", "ac.uk",
    # Religious / nonprofits that won't sell
    "dosafl.com", "magdalenhouse.org",
    # Defunct / dead domains
    "worldnet.att.net", "city.cleveland.oh.us",
}

DEAD_END_PREFIXES = [
    "noreply@", "no-reply@", "donotreply@",
    "info@", "admin@", "webmaster@",
    "support@", "help@", "abuse@",
    "postmaster@", "mailer-daemon@",
]

DEAD_END_KEYWORDS = [
    "landbank", "mayor", "clerk", "assessor", "treasurer",
    "council", "sheriff", "police", "fire", "court",
]


def is_dead_end_email(email: str) -> bool:
    """Check if an email address is a dead-end that won't respond to outreach."""
    if not email:
        return True
    email = email.lower().strip()

    # Check prefixes
    for prefix in DEAD_END_PREFIXES:
        if email.startswith(prefix):
            return True

    # Check domain
    domain = email.split("@")[-1] if "@" in email else ""

    # Government TLDs
    if domain.endswith(".gov") or domain.endswith(".gov.us"):
        return True

    # Education
    if domain.endswith(".edu") or domain.endswith(".ac.uk"):
        return True

    # Exact domain matches
    if domain in DEAD_END_DOMAINS:
        return True

    # Keywords in the local part
    local = email.split("@")[0] if "@" in email else ""
    for kw in DEAD_END_KEYWORDS:
        if kw in local:
            return True

    return False


def safe_send_email(to: str, subject: str, body: str,
                    max_retries: int = 3,
                    state: str = "",
                    action: str = "outreach") -> bool:
    """
    Send email via Resend with retry and dead letter queue on failure.
    Returns True if sent, False if queued to dead letter.
    Auto-skips government, institutional, and dead-end addresses.
    Enforces per-state compliance (state_gates.json) when `state` is provided.
    Appends CAN-SPAM footer if body does not already have one.
    """
    if not RESEND_KEY:
        log.warning("No RESEND_API_KEY set -- queuing to dead letter")
        _queue_dead_letter(to, subject, body, "no_api_key")
        return False

    if not to:
        return False

    # ERADICATION GATE -- FIRST. Permanent DNC list (Streubel et al.).
    # Hardcoded module. If a DNC subject reaches this function, that's a
    # supervisory failure -- the upstream filter should have removed them
    # from the working set. We still tripwire here as last resort.
    try:
        import sys as _sys
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
        from dnc_filter import alert_dnc_touch
        _erad_assert_safe(email=to, address=subject, caller="rex_utils.safe_send_email")
    except EradicationViolation as _eg_err:
        log.error("ERADICATION GATE tripwire (last-resort): %s", _eg_err)
        try:
            alert_dnc_touch(
                context={"to": to, "subject": subject, "stage": "safe_send_email"},
                caller="rex_utils.safe_send_email",
            )
        except Exception:
            pass
        _queue_dead_letter(to, subject, body, f"eradication_blocked:{_eg_err}")
        return False
    except ImportError as _eg_imp:
        log.error("eradication_gate unavailable -- failing closed: %s", _eg_imp)
        return False

    if is_dead_end_email(to):
        log.info("SKIP dead-end email: %s" % to)
        return False

    try:
        import sys as _sys, pathlib as _pl
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from resend_guard import assert_external_recipient, OwnerEmailBlocked
        assert_external_recipient(to)
    except OwnerEmailBlocked as e:
        log.warning("BLOCKED owner-bound send: %s", e)
        return False
    except Exception:
        pass  # guard unavailable -> fall through to preserve existing behavior

    # --- State compliance gate ----------------------------------------------
    # If caller passed a state, run it through state_gate. Blocks + logs if not
    # allowed. No state == legacy path (warn once per hour so we migrate over).
    if state:
        try:
            import sys as _sys, pathlib as _pl
            _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent / "compliance"))
            from state_gate import check as _state_check
            decision = _state_check(state, channel="email", action=action)
            if not decision.ok:
                log.warning("BLOCKED by state_gate: %s / %s -> %s",
                            state, action, decision.blocked_reason)
                _queue_dead_letter(to, subject, body,
                                   f"state_gate_blocked:{decision.blocked_reason}")
                return False
            if decision.warnings:
                log.info("state_gate warnings for %s: %s", state, "; ".join(decision.warnings))
            # Append CAN-SPAM footer if missing
            if "unsubscribe" not in body.lower() and "opt out" not in body.lower():
                body = body.rstrip() + (
                    "\n\n---\nEverlight Ventures, Wholesale Division\n"
                    "To opt out of future messages reply STOP or email opt-out@everlightventures.io.\n"
                    "You received this message because we believe you may be the owner of a property "
                    "we're interested in acquiring."
                )
        except Exception as e:
            log.warning("state_gate unavailable, proceeding without compliance check: %s", e)
    else:
        log.warning("safe_send_email called without state -- compliance NOT checked. Caller should pass state=<2-letter>.")

    # -----------------------------------------------------------------------

    import requests

    def _send():
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "text": body,
                "reply_to": REPLY_TO,
            },
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Resend API returned {resp.status_code}: {resp.text[:200]}")
        return True

    try:
        return retry(_send, max_retries=max_retries, delay=5, backoff=2.0)
    except Exception as e:
        log.error(f"Email to {to} failed after {max_retries} retries: {e}")
        _queue_dead_letter(to, subject, body, str(e))
        return False


def _queue_dead_letter(to: str, subject: str, body: str, reason: str):
    """Save failed email to dead letter queue for manual retry later."""
    entry = {
        "to": to,
        "subject": subject,
        "body": body,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retried": False,
    }
    dl_path = FAILED_DIR / f"{TODAY}_dead_letters.jsonl"
    with open(dl_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    log.info(f"Queued dead letter for {to} -> {dl_path.name}")


def retry_dead_letters() -> dict:
    """Retry all un-retried dead letters. Returns counts."""
    sent = 0
    failed = 0
    for dl_file in sorted(FAILED_DIR.glob("*_dead_letters.jsonl")):
        lines = dl_file.read_text().strip().split("\n")
        updated = []
        for line in lines:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("retried"):
                updated.append(line)
                continue
            if safe_send_email(entry["to"], entry["subject"], entry["body"], max_retries=2):
                entry["retried"] = True
                entry["retried_at"] = datetime.now(timezone.utc).isoformat()
                sent += 1
            else:
                failed += 1
            updated.append(json.dumps(entry))
        dl_file.write_text("\n".join(updated) + "\n")
    log.info(f"Dead letter retry: {sent} sent, {failed} still failed")
    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# SAFE IMAP CHECK (with retry + reconnection)
# ---------------------------------------------------------------------------

def safe_imap_check(max_retries: int = 3) -> list[dict]:
    """
    Check IMAP for new replies with retry and reconnection.
    Returns list of reply dicts.
    """
    import imaplib
    import email as emaillib
    import re

    imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    imap_user = os.environ.get("IMAP_USER", "")
    imap_pass = os.environ.get("IMAP_PASS", "")

    if not imap_user or not imap_pass:
        log.warning("No IMAP credentials set")
        return []

    def _check():
        mail = imaplib.IMAP4_SSL(imap_host)
        try:
            mail.login(imap_user, imap_pass)
            mail.select("INBOX")
            status, messages = mail.search(None, '(UNSEEN SUBJECT "Re: Cash offer for")')
            if status != "OK":
                return []

            replies = []
            for msg_id in messages[0].split():
                if not msg_id:
                    continue
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                msg = emaillib.message_from_bytes(data[0][1])
                sender = msg["From"]
                subject = msg["Subject"] or ""
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                addr_match = re.search(r"Cash offer for (.+)", subject)
                address = addr_match.group(1) if addr_match else ""
                replies.append({
                    "from": sender,
                    "subject": subject,
                    "body": body.strip(),
                    "address": address,
                })
            return replies
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    try:
        return retry(_check, max_retries=max_retries, delay=5, backoff=2.0)
    except Exception as e:
        log.error(f"IMAP check failed after {max_retries} retries: {e}")
        return []


# ---------------------------------------------------------------------------
# ATTOM API CACHE (7-day TTL per zip code)
# ---------------------------------------------------------------------------

ATTOM_CACHE_FILE = CACHE_DIR / "attom_cache.json"
ATTOM_CACHE_TTL_DAYS = 7


def _load_attom_cache() -> dict:
    if ATTOM_CACHE_FILE.exists():
        try:
            return json.loads(ATTOM_CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_attom_cache(cache: dict):
    ATTOM_CACHE_FILE.write_text(json.dumps(cache, indent=2, default=str))


def attom_cache_get(zip_code: str, endpoint: str) -> Optional[dict]:
    """
    Get cached ATTOM response for a zip+endpoint combo.
    Returns None if not cached or expired (>7 days).
    """
    cache = _load_attom_cache()
    key = f"{zip_code}_{endpoint}"
    entry = cache.get(key)
    if not entry:
        return None

    cached_date = entry.get("cached_at", "")
    try:
        cached_dt = datetime.fromisoformat(cached_date)
        if datetime.now(timezone.utc) - cached_dt > timedelta(days=ATTOM_CACHE_TTL_DAYS):
            return None  # expired
    except (ValueError, TypeError):
        return None

    return entry.get("data")


def attom_cache_set(zip_code: str, endpoint: str, data: Any):
    """Store an ATTOM API response in cache."""
    cache = _load_attom_cache()
    key = f"{zip_code}_{endpoint}"
    cache[key] = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "zip_code": zip_code,
        "endpoint": endpoint,
        "data": data,
    }
    _save_attom_cache(cache)
    log.info(f"Cached ATTOM response for {key}")


def attom_cache_cleanup():
    """Remove expired entries from cache."""
    cache = _load_attom_cache()
    now = datetime.now(timezone.utc)
    cleaned = {}
    for key, entry in cache.items():
        try:
            cached_dt = datetime.fromisoformat(entry.get("cached_at", ""))
            if now - cached_dt <= timedelta(days=ATTOM_CACHE_TTL_DAYS):
                cleaned[key] = entry
        except (ValueError, TypeError):
            pass
    _save_attom_cache(cleaned)
    removed = len(cache) - len(cleaned)
    if removed:
        log.info(f"Cleaned {removed} expired ATTOM cache entries")


# ---------------------------------------------------------------------------
# ATTOM RATE TRACKER
# ---------------------------------------------------------------------------

ATTOM_RATE_FILE = CACHE_DIR / "attom_rate_tracker.json"
ATTOM_DAILY_LIMIT = 250  # Conservative estimate for free trial
ATTOM_WARN_PCT = 0.80    # Alert at 80% usage


def _load_rate_tracker() -> dict:
    if ATTOM_RATE_FILE.exists():
        try:
            return json.loads(ATTOM_RATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_rate_tracker(tracker: dict):
    ATTOM_RATE_FILE.write_text(json.dumps(tracker, indent=2))


def attom_rate_increment(calls: int = 1) -> dict:
    """
    Increment today's ATTOM API call count.
    Returns dict with today's count and whether limit is approaching.
    """
    tracker = _load_rate_tracker()

    if TODAY not in tracker:
        tracker[TODAY] = {"calls": 0, "alerted": False}

    tracker[TODAY]["calls"] += calls
    current = tracker[TODAY]["calls"]
    warn_threshold = int(ATTOM_DAILY_LIMIT * ATTOM_WARN_PCT)
    approaching_limit = current >= warn_threshold

    if approaching_limit and not tracker[TODAY].get("alerted"):
        msg = (
            f"*ATTOM API Rate Warning*\n"
            f"Used {current}/{ATTOM_DAILY_LIMIT} calls today ({current/ATTOM_DAILY_LIMIT*100:.0f}%).\n"
            f"Pausing non-essential ATTOM calls."
        )
        _post_slack(msg)
        tracker[TODAY]["alerted"] = True

    _save_rate_tracker(tracker)

    return {
        "today_calls": current,
        "limit": ATTOM_DAILY_LIMIT,
        "pct_used": round(current / ATTOM_DAILY_LIMIT * 100, 1),
        "approaching_limit": approaching_limit,
        "over_limit": current >= ATTOM_DAILY_LIMIT,
    }


def attom_rate_check() -> dict:
    """Check today's rate without incrementing."""
    tracker = _load_rate_tracker()
    current = tracker.get(TODAY, {}).get("calls", 0)
    return {
        "today_calls": current,
        "limit": ATTOM_DAILY_LIMIT,
        "pct_used": round(current / ATTOM_DAILY_LIMIT * 100, 1),
        "approaching_limit": current >= int(ATTOM_DAILY_LIMIT * ATTOM_WARN_PCT),
        "over_limit": current >= ATTOM_DAILY_LIMIT,
    }


def attom_rate_can_call(calls_needed: int = 1) -> bool:
    """Returns True if we have enough budget for the requested calls."""
    tracker = _load_rate_tracker()
    current = tracker.get(TODAY, {}).get("calls", 0)
    return (current + calls_needed) < ATTOM_DAILY_LIMIT


def attom_rate_history(days: int = 7) -> list[dict]:
    """Get call counts for the last N days."""
    tracker = _load_rate_tracker()
    history = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        entry = tracker.get(d, {"calls": 0})
        history.append({"date": d, "calls": entry.get("calls", 0)})
    return history


# ---------------------------------------------------------------------------
# HOT ZIP CODE DISCOVERY (auto-expand markets)
# ---------------------------------------------------------------------------

def get_hot_zips(market: str, state: str, count: int = 10) -> list[dict]:
    """
    Find zip codes with high distressed property density using ATTOM.

    Uses the ATTOM property/snapshot endpoint filtered by foreclosure status
    to find zips where inventory is highest.

    Falls back to a curated list per market if ATTOM is unavailable or
    rate-limited.

    Args:
        market: city name (e.g. "Atlanta")
        state: state code (e.g. "GA")
        count: number of zip codes to return

    Returns:
        List of dicts with zip_code, city, state, distress_score.
    """
    # Try ATTOM first if we have budget
    if ATTOM_API_KEY and attom_rate_can_call(1):
        cached = attom_cache_get(f"{market}_{state}", "hot_zips")
        if cached:
            return cached[:count]

        try:
            import requests
            # Use ATTOM area endpoint to find zips in a metro
            resp = requests.get(
                "https://api.gateway.attomdata.com/areaapi/v1.0.0/area/full",
                params={
                    "AreaType": "ZI",
                    "AreaParent": f"ST{state}",
                    "MinPopulation": "5000",
                },
                headers={
                    "apikey": ATTOM_API_KEY,
                    "Accept": "application/json",
                },
                timeout=15,
            )
            attom_rate_increment(1)

            if resp.status_code == 200:
                data = resp.json()
                areas = data.get("response", {}).get("result", {}).get("package", {}).get("item", [])
                zips = []
                for area in areas:
                    zip_code = area.get("AreaCode", "")
                    if zip_code:
                        zips.append({
                            "zip_code": zip_code,
                            "city": market,
                            "state": state,
                            "area_name": area.get("AreaName", ""),
                            "population": area.get("Population", 0),
                        })
                if zips:
                    attom_cache_set(f"{market}_{state}", "hot_zips", zips)
                    return zips[:count]

        except Exception as e:
            log.warning(f"ATTOM hot zips lookup failed for {market}, {state}: {e}")

    # Fallback: curated zip codes per market (known distress corridors)
    CURATED_ZIPS = {
        "atlanta": [
            {"zip_code": "30310", "city": "Atlanta", "state": "GA", "distress_score": 85},
            {"zip_code": "30311", "city": "Atlanta", "state": "GA", "distress_score": 82},
            {"zip_code": "30314", "city": "Atlanta", "state": "GA", "distress_score": 80},
            {"zip_code": "30315", "city": "Atlanta", "state": "GA", "distress_score": 78},
            {"zip_code": "30318", "city": "Atlanta", "state": "GA", "distress_score": 75},
            {"zip_code": "30316", "city": "Atlanta", "state": "GA", "distress_score": 72},
            {"zip_code": "30331", "city": "Atlanta", "state": "GA", "distress_score": 70},
            {"zip_code": "30344", "city": "East Point", "state": "GA", "distress_score": 68},
            {"zip_code": "30354", "city": "Atlanta", "state": "GA", "distress_score": 65},
            {"zip_code": "30337", "city": "College Park", "state": "GA", "distress_score": 63},
        ],
        "dallas": [
            {"zip_code": "75215", "city": "Dallas", "state": "TX", "distress_score": 84},
            {"zip_code": "75216", "city": "Dallas", "state": "TX", "distress_score": 82},
            {"zip_code": "75217", "city": "Dallas", "state": "TX", "distress_score": 80},
            {"zip_code": "75203", "city": "Dallas", "state": "TX", "distress_score": 78},
            {"zip_code": "75227", "city": "Dallas", "state": "TX", "distress_score": 75},
            {"zip_code": "75210", "city": "Dallas", "state": "TX", "distress_score": 72},
            {"zip_code": "75241", "city": "Dallas", "state": "TX", "distress_score": 70},
            {"zip_code": "75228", "city": "Dallas", "state": "TX", "distress_score": 68},
            {"zip_code": "75223", "city": "Dallas", "state": "TX", "distress_score": 65},
            {"zip_code": "75212", "city": "Dallas", "state": "TX", "distress_score": 63},
        ],
        "cleveland": [
            {"zip_code": "44104", "city": "Cleveland", "state": "OH", "distress_score": 88},
            {"zip_code": "44105", "city": "Cleveland", "state": "OH", "distress_score": 85},
            {"zip_code": "44108", "city": "Cleveland", "state": "OH", "distress_score": 83},
            {"zip_code": "44103", "city": "Cleveland", "state": "OH", "distress_score": 80},
            {"zip_code": "44102", "city": "Cleveland", "state": "OH", "distress_score": 78},
            {"zip_code": "44127", "city": "Cleveland", "state": "OH", "distress_score": 75},
            {"zip_code": "44128", "city": "Cleveland", "state": "OH", "distress_score": 72},
            {"zip_code": "44106", "city": "Cleveland", "state": "OH", "distress_score": 70},
            {"zip_code": "44112", "city": "East Cleveland", "state": "OH", "distress_score": 68},
            {"zip_code": "44110", "city": "Cleveland", "state": "OH", "distress_score": 65},
        ],
        "st_louis": [
            {"zip_code": "63106", "city": "St. Louis", "state": "MO", "distress_score": 90},
            {"zip_code": "63107", "city": "St. Louis", "state": "MO", "distress_score": 87},
            {"zip_code": "63115", "city": "St. Louis", "state": "MO", "distress_score": 85},
            {"zip_code": "63112", "city": "St. Louis", "state": "MO", "distress_score": 82},
            {"zip_code": "63111", "city": "St. Louis", "state": "MO", "distress_score": 80},
            {"zip_code": "63113", "city": "St. Louis", "state": "MO", "distress_score": 78},
            {"zip_code": "63120", "city": "St. Louis", "state": "MO", "distress_score": 75},
            {"zip_code": "63116", "city": "St. Louis", "state": "MO", "distress_score": 72},
            {"zip_code": "63118", "city": "St. Louis", "state": "MO", "distress_score": 70},
            {"zip_code": "63104", "city": "St. Louis", "state": "MO", "distress_score": 68},
        ],
        "charlotte": [
            {"zip_code": "28206", "city": "Charlotte", "state": "NC", "distress_score": 80},
            {"zip_code": "28208", "city": "Charlotte", "state": "NC", "distress_score": 78},
            {"zip_code": "28205", "city": "Charlotte", "state": "NC", "distress_score": 76},
            {"zip_code": "28216", "city": "Charlotte", "state": "NC", "distress_score": 74},
            {"zip_code": "28217", "city": "Charlotte", "state": "NC", "distress_score": 72},
            {"zip_code": "28212", "city": "Charlotte", "state": "NC", "distress_score": 70},
            {"zip_code": "28215", "city": "Charlotte", "state": "NC", "distress_score": 68},
            {"zip_code": "28269", "city": "Charlotte", "state": "NC", "distress_score": 65},
            {"zip_code": "28213", "city": "Charlotte", "state": "NC", "distress_score": 63},
            {"zip_code": "28262", "city": "Charlotte", "state": "NC", "distress_score": 60},
        ],
        "jacksonville": [
            {"zip_code": "32206", "city": "Jacksonville", "state": "FL", "distress_score": 82},
            {"zip_code": "32208", "city": "Jacksonville", "state": "FL", "distress_score": 80},
            {"zip_code": "32209", "city": "Jacksonville", "state": "FL", "distress_score": 78},
            {"zip_code": "32205", "city": "Jacksonville", "state": "FL", "distress_score": 76},
            {"zip_code": "32202", "city": "Jacksonville", "state": "FL", "distress_score": 74},
            {"zip_code": "32204", "city": "Jacksonville", "state": "FL", "distress_score": 72},
            {"zip_code": "32254", "city": "Jacksonville", "state": "FL", "distress_score": 70},
            {"zip_code": "32211", "city": "Jacksonville", "state": "FL", "distress_score": 68},
            {"zip_code": "32210", "city": "Jacksonville", "state": "FL", "distress_score": 65},
            {"zip_code": "32218", "city": "Jacksonville", "state": "FL", "distress_score": 63},
        ],
    }

    market_key = market.lower().replace(" ", "_").replace(".", "")
    return CURATED_ZIPS.get(market_key, [])[:count]


# ---------------------------------------------------------------------------
# SLACK HELPER
# ---------------------------------------------------------------------------

def _post_slack(text: str, title: str = "Rex Scout Report"):
    """Post to Slack #wholesale-deals, creating a GDoc first when possible."""
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title=title,
                content=text,
                folder="01_Broker_OS/Scout_Reports",
                summary=text[:200],
                agent="rex_blackwell",
            )
            if result.get("ok"):
                return
        except Exception:
            pass
    # Fallback: raw text post
    if not SLACK_TOKEN:
        log.info(f"[Slack offline] {text[:200]}")
        return
    try:
        import requests
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": SLACK_CHANNEL, "text": text},
            timeout=10,
        )
    except Exception as e:
        log.error(f"Slack post failed: {e}")


# ---------------------------------------------------------------------------
# SYSTEM HEALTH CHECK
# ---------------------------------------------------------------------------

def health_check() -> dict:
    """
    Check all Rex dependencies and return status dict.
    Also posts summary to Slack.
    """
    results = {}

    # 1. Resend API
    if RESEND_KEY:
        try:
            import requests
            resp = requests.get(
                "https://api.resend.com/domains",
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                timeout=10,
            )
            results["resend"] = "OK" if resp.status_code == 200 else f"ERROR ({resp.status_code})"
        except Exception as e:
            results["resend"] = f"ERROR ({e})"
    else:
        results["resend"] = "NO_KEY"

    # 2. IMAP
    imap_user = os.environ.get("IMAP_USER", "")
    imap_pass = os.environ.get("IMAP_PASS", "")
    if imap_user and imap_pass:
        try:
            import imaplib
            mail = imaplib.IMAP4_SSL(os.environ.get("IMAP_HOST", "imap.gmail.com"))
            mail.login(imap_user, imap_pass)
            mail.logout()
            results["imap"] = "OK"
        except Exception as e:
            results["imap"] = f"ERROR ({e})"
    else:
        results["imap"] = "NO_CREDENTIALS"

    # 3. ATTOM API
    if ATTOM_API_KEY:
        rate = attom_rate_check()
        results["attom"] = f"OK ({rate['today_calls']}/{rate['limit']} calls today)"
    else:
        results["attom"] = "NO_KEY"

    # 4. Supabase
    supa_url = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
    supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supa_key:
        try:
            import requests
            resp = requests.get(
                f"{supa_url}/rest/v1/",
                headers={"apikey": supa_key},
                timeout=10,
            )
            results["supabase"] = "OK" if resp.status_code in (200, 406) else f"ERROR ({resp.status_code})"
        except Exception as e:
            results["supabase"] = f"ERROR ({e})"
    else:
        results["supabase"] = "NO_KEY"

    # 5. Slack
    if SLACK_TOKEN:
        results["slack"] = "OK"
    else:
        results["slack"] = "NO_TOKEN"

    # Post summary
    status_lines = [f"- {k}: {v}" for k, v in results.items()]
    overall = "HEALTHY" if all("OK" in str(v) for v in results.values()) else "DEGRADED"
    msg = f"*Rex Health Check*\n{chr(10).join(status_lines)}\nOverall: *{overall}*"
    _post_slack(msg)

    return results


# ---------------------------------------------------------------------------
# ATTOM CACHED FETCH WRAPPER
# ---------------------------------------------------------------------------

def attom_fetch(endpoint: str, params: dict, zip_code: str = "") -> Optional[dict]:
    """
    Fetch from ATTOM with caching and rate tracking.
    Returns None if rate-limited, cached data expired, or API error.
    """
    if not ATTOM_API_KEY:
        log.warning("No ATTOM_API_KEY set")
        return None

    cache_key = zip_code or "_".join(str(v) for v in params.values())

    # Check cache first
    cached = attom_cache_get(cache_key, endpoint)
    if cached is not None:
        log.info(f"ATTOM cache hit: {cache_key}/{endpoint}")
        return cached

    # Check rate limit
    if not attom_rate_can_call(1):
        log.warning("ATTOM daily rate limit reached -- skipping call")
        return None

    # Make the call with retry
    import requests

    def _call():
        resp = requests.get(
            f"https://api.gateway.attomdata.com{endpoint}",
            params=params,
            headers={
                "apikey": ATTOM_API_KEY,
                "Accept": "application/json",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"ATTOM returned {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    try:
        data = retry(_call, max_retries=2, delay=3, backoff=2.0)
        attom_rate_increment(1)
        attom_cache_set(cache_key, endpoint, data)
        return data
    except Exception as e:
        log.error(f"ATTOM fetch failed: {endpoint} -- {e}")
        attom_rate_increment(1)  # still counts against quota
        return None


def load_leads_filtered(path, *, caller: str = "unknown") -> list[dict]:
    """
    Canonical lead loader for ALL rex_* scripts. Reads a leads_db.json file
    and applies the DNC filter at load time. Any DNC contact found in the
    file fires an alert (log + Slack) and is removed from the working set
    before downstream code sees it.

    Doctrine (Rich, 2026-05-15): "never should those DNC contacts be part
    of an autonomous process. they are do not contact and blacklisted."

    Use this instead of `json.loads(LEADS_DB.read_text())`.
    """
    import json as _json
    import pathlib as _pl
    import sys as _sys
    _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
    from dnc_filter import filter_dnc

    p = _pl.Path(path)
    if not p.exists():
        log.info("load_leads_filtered: %s does not exist; returning []", p)
        return []
    raw = _json.loads(p.read_text())
    if not isinstance(raw, list):
        log.warning("load_leads_filtered: %s is not a list; passing through", p)
        return raw  # pass-through, no filter possible
    clean, removed = filter_dnc(raw, caller=f"{caller}:load_leads_filtered({p.name})")
    if removed:
        log.error(
            "load_leads_filtered REMOVED %d DNC contact(s) from %s -- alerts fired",
            len(removed), p.name,
        )
    return clean
