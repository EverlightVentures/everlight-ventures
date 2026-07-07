from __future__ import annotations

import os

# Broadcastify Premium ($30/yr) feed archives: 365-day rolling, 30-min MP3
# blocks. Personal download + transcription is within the CC BY 3.0 archive
# license. Throttle politely (>=5s between blocks) and never share the login.
BASE = "https://www.broadcastify.com"
ARCHIVE_API = BASE + "/archives/api/archives.php"
DOWNLOAD = BASE + "/archives/download/{block_id}"

# Solano feeds (feed_id -> label). 45149 is the main county PD/Fire/CHP feed.
SOLANO_FEEDS = {
    "45149": "Solano: Fairfield/Vacaville/Suisun PD, Fire & CHP",
    "4881": "Solano: Sheriff, Rio Vista & Dixon PD",
}


def client(user: str | None = None, password: str | None = None):
    """An authenticated Premium session (httpx client with the auth cookie)."""
    import httpx

    user = user or os.environ.get("SLD_BROADCASTIFY_USER")
    password = password or os.environ.get("SLD_BROADCASTIFY_PASS")
    s = httpx.Client(
        follow_redirects=True, timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (personal safety tool)"},
    )
    s.post(f"{BASE}/login/", data={"username": user, "password": password,
                                   "action": "auth", "redirect": "/"})
    if "bcfyuser1" not in s.cookies:
        raise RuntimeError("Broadcastify login failed (no auth cookie)")
    return s


def list_blocks(session, feed_id: str, date: str) -> list[dict]:
    """30-minute archive blocks for a feed on a date (YYYY-MM-DD).

    Each block: {id: '45149-<startTs>', start, end, startTs, endTs, duration}.
    """
    r = session.get(ARCHIVE_API, params={"feedId": feed_id, "date": date})
    r.raise_for_status()
    data = r.json()
    blocks = data if isinstance(data, list) else data.get("data") or data.get("archives") or []
    return blocks


def download_block(session, block_id: str, out_path: str) -> str:
    """Download one archive block's MP3 to out_path. Returns out_path."""
    r = session.get(DOWNLOAD.format(block_id=block_id))
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path
