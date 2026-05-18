"""
gmail_calendar_to_drive.py
──────────────────────────
Backs up Gmail + Google Calendar to your encrypted Drive folder so
all account data lives together in one organized structure.

What it backs up:
  Gmail   → drive_everlight_crypt:gmail_archive/<YYYY-MM>/<msgid>.eml
            One file per email, organized by month, eml format.
            Searchable later via grep, indexable by any mail client.
  Calendar → drive_everlight_crypt:calendar_archive/calendar_<YYYY-MM-DD>.ics
            Snapshot of the next 365 days of events as ICS.

Auth: uses the SAME Google account as drive_everlight (rclone token).
      Reads /home/opc/secrets/google_docs_token.json or whatever the
      shared OAuth token is on phone.

Cron (recommend daily at 4 AM):
  0 4 * * * /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/gmail_calendar_to_drive.py >> /mnt/sdcard/AA_MY_DRIVE/_logs/gmail_cal_to_drive.log 2>&1

NOTE: This script needs google-api-python-client. Install on phone with:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

The OAuth scope must include:
  - https://www.googleapis.com/auth/gmail.readonly
  - https://www.googleapis.com/auth/calendar.readonly
If the existing token doesn't have these scopes, run gen_google_token.py
(separate setup) to refresh with the right scopes.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR = WORKSPACE / "08_BACKUPS/offsite_mirror/active" / "gmail_calendar_staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "gmail_cal_to_drive.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("gmail_cal_to_drive")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
log.addHandler(console)

CRYPT_REMOTE = "drive_everlight_crypt"


def find_google_token() -> Path | None:
    """Look for a usable Google OAuth token across known phone locations."""
    candidates = [
        WORKSPACE / "03_AUTOMATION_CORE" / "03_Credentials" / "google_token.json",
        WORKSPACE / "03_AUTOMATION_CORE" / "03_Credentials" / "google_docs_token.json",
        Path.home() / ".config" / "rclone" / "rclone.conf",  # rclone token (need extraction)
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def backup_gmail(token_path: Path, since_days: int = 30) -> int:
    """Pull last N days of email; one .eml per message under staging/gmail_archive/."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        log.error("google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        return 0

    if token_path.suffix != ".json":
        log.error("Need a token.json. rclone token is in different format. Run gen_google_token.py")
        return 0

    try:
        creds = Credentials.from_authorized_user_file(str(token_path),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"])
        service = build("gmail", "v1", credentials=creds)
    except Exception as e:
        log.error(f"Gmail auth failed: {e}")
        return 0

    cutoff = (datetime.now() - timedelta(days=since_days)).strftime("%Y/%m/%d")
    query = f"after:{cutoff}"
    log.info(f"Querying Gmail: {query}")

    msg_ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=500
        ).execute()
        msg_ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    log.info(f"Got {len(msg_ids)} message IDs to back up")
    saved = 0

    archive_dir = STAGING_DIR / "gmail_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for msg_id in msg_ids:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="raw"
            ).execute()
            raw_b64 = msg["raw"]
            raw_bytes = base64.urlsafe_b64decode(raw_b64.encode("ASCII"))

            # Organize by year-month from message internalDate
            ts_ms = int(msg.get("internalDate", "0"))
            dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            ym_dir = archive_dir / dt.strftime("%Y-%m")
            ym_dir.mkdir(parents=True, exist_ok=True)

            out_file = ym_dir / f"{msg_id}.eml"
            out_file.write_bytes(raw_bytes)
            saved += 1
        except Exception as e:
            log.warning(f"Failed to fetch {msg_id}: {e}")

    log.info(f"Gmail backup: saved {saved} / {len(msg_ids)} messages")
    return saved


def backup_calendar(token_path: Path, days_ahead: int = 365) -> int:
    """Snapshot next N days of calendar events to ICS."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        log.error("google-api-python-client not installed")
        return 0

    if token_path.suffix != ".json":
        log.error("Need a token.json for Calendar")
        return 0

    try:
        creds = Credentials.from_authorized_user_file(str(token_path),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"])
        service = build("calendar", "v3", credentials=creds)
    except Exception as e:
        log.error(f"Calendar auth failed: {e}")
        return 0

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)
    events = []
    page_token = None
    while True:
        resp = service.events().list(
            calendarId="primary",
            timeMin=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            timeMax=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            singleEvents=True,
            orderBy="startTime",
            maxResults=2500,
            pageToken=page_token,
        ).execute()
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    log.info(f"Got {len(events)} calendar events for next {days_ahead} days")

    cal_dir = STAGING_DIR / "calendar_archive"
    cal_dir.mkdir(parents=True, exist_ok=True)

    # Build minimal ICS file
    ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Everlight//Phone Backup//EN"]
    for e in events:
        try:
            uid = e.get("id", "no-id")
            summary = e.get("summary", "(no title)").replace("\n", " ").replace(",", "\\,")
            start = (e.get("start", {}).get("dateTime") or e.get("start", {}).get("date") or "").replace("-", "").replace(":", "").replace(" ", "T")
            end_ = (e.get("end", {}).get("dateTime") or e.get("end", {}).get("date") or "").replace("-", "").replace(":", "").replace(" ", "T")
            location = e.get("location", "").replace("\n", " ").replace(",", "\\,")
            description = e.get("description", "").replace("\n", "\\n").replace(",", "\\,")
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"SUMMARY:{summary}",
                f"DTSTART:{start}",
                f"DTEND:{end_}",
                f"LOCATION:{location}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
            ])
        except Exception as e:
            log.warning(f"Couldn't serialize event: {e}")
    ics_lines.append("END:VCALENDAR")

    out_file = cal_dir / f"calendar_{now.strftime('%Y-%m-%d')}.ics"
    out_file.write_text("\n".join(ics_lines))
    log.info(f"Calendar snapshot: {out_file} ({len(events)} events)")
    return len(events)


def push_to_crypt() -> bool:
    """rclone copy staging → drive_everlight_crypt."""
    try:
        # Gmail archive
        if (STAGING_DIR / "gmail_archive").exists():
            subprocess.run([
                "rclone", "copy",
                str(STAGING_DIR / "gmail_archive"),
                f"{CRYPT_REMOTE}:gmail_archive/",
                "--transfers", "4",
                "--quiet",
            ], check=False, timeout=3600)
            log.info("Pushed gmail_archive to crypt remote")

        # Calendar archive
        if (STAGING_DIR / "calendar_archive").exists():
            subprocess.run([
                "rclone", "copy",
                str(STAGING_DIR / "calendar_archive"),
                f"{CRYPT_REMOTE}:calendar_archive/",
                "--transfers", "4",
                "--quiet",
            ], check=False, timeout=600)
            log.info("Pushed calendar_archive to crypt remote")

        return True
    except Exception as e:
        log.error(f"Push to crypt failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gmail-days", type=int, default=30, help="how many days of Gmail to back up (incremental)")
    ap.add_argument("--cal-days", type=int, default=365, help="how many days of Calendar forward to snapshot")
    ap.add_argument("--no-push", action="store_true", help="stage only, don't rclone push")
    args = ap.parse_args()

    log.info("="*70)
    log.info("Gmail + Calendar → encrypted Drive backup starting")

    token = find_google_token()
    if not token:
        log.error("No Google token found in known locations.")
        log.error("Set up via gen_google_token.py with scopes for gmail.readonly + calendar.readonly")
        sys.exit(1)
    log.info(f"Using token: {token}")

    g_count = backup_gmail(token, since_days=args.gmail_days)
    c_count = backup_calendar(token, days_ahead=args.cal_days)

    if not args.no_push:
        push_to_crypt()
        # cleanup local staging after successful push (delta only stays)
        # Actually keep local staging too — that's our 3rd 3-2-1 copy

    log.info(f"Done. Gmail: {g_count} msgs / Calendar: {c_count} events")
    log.info("="*70)


if __name__ == "__main__":
    main()
