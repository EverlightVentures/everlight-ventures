#!/usr/bin/env python3
"""
social_poster.py -- Direct API Social Media Posting
Posts content to X/Twitter and LinkedIn. Falls back to Slack queue for TikTok/IG.

Usage:
    python social_poster.py --dry-run                    # simulate all platforms
    python social_poster.py --platform twitter --text "Hello world"
    python social_poster.py --from-queue                 # post next item from content queue

Env vars:
    TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
    LINKEDIN_ACCESS_TOKEN
    SLACK_WEBHOOK_URL (for manual upload queue fallback)
"""

import os
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
OUTPUT_QUEUE = WORKSPACE / "02_CONTENT_FACTORY/01_Queue/avatar_output"
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "social_poster.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("social_poster")


def post_twitter(text: str, media_path: str = None, dry_run: bool = False) -> dict:
    """Post to X/Twitter using v2 API (free tier)."""
    if dry_run:
        log.info(f"[DRY RUN] Twitter: {text[:80]}...")
        return {"status": "dry_run", "platform": "twitter"}

    import requests
    from requests_oauthlib import OAuth1

    auth = OAuth1(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_SECRET"],
    )

    payload = {"text": text}
    media_id = None

    # Upload media if provided
    if media_path and os.path.exists(media_path):
        upload_resp = requests.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            auth=auth,
            files={"media": open(media_path, "rb")},
        )
        if upload_resp.status_code == 200:
            media_id = upload_resp.json().get("media_id_string")
            payload["media"] = {"media_ids": [media_id]}

    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json=payload,
    )

    if resp.status_code in (200, 201):
        tweet_id = resp.json().get("data", {}).get("id")
        log.info(f"Twitter posted: tweet_id={tweet_id}")
        return {"status": "posted", "platform": "twitter", "id": tweet_id}
    else:
        log.error(f"Twitter error ({resp.status_code}): {resp.text[:200]}")
        return {"status": "error", "platform": "twitter", "error": resp.text[:200]}


def post_linkedin(text: str, dry_run: bool = False) -> dict:
    """Post to LinkedIn using free posting API."""
    if dry_run:
        log.info(f"[DRY RUN] LinkedIn: {text[:80]}...")
        return {"status": "dry_run", "platform": "linkedin"}

    import requests

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        log.warning("No LINKEDIN_ACCESS_TOKEN set")
        return {"status": "skipped", "platform": "linkedin"}

    # Get user profile URN
    profile_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    if profile_resp.status_code != 200:
        log.error(f"LinkedIn profile fetch failed: {profile_resp.status_code}")
        return {"status": "error", "platform": "linkedin"}

    user_sub = profile_resp.json().get("sub")

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "author": f"urn:li:person:{user_sub}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
    )

    if resp.status_code in (200, 201):
        log.info(f"LinkedIn posted successfully")
        return {"status": "posted", "platform": "linkedin"}
    else:
        log.error(f"LinkedIn error ({resp.status_code}): {resp.text[:200]}")
        return {"status": "error", "platform": "linkedin", "error": resp.text[:200]}


def queue_to_slack(text: str, media_path: str = None, platform: str = "tiktok", dry_run: bool = False) -> dict:
    """Queue content to Slack for manual upload (TikTok/IG)."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        log.warning("No SLACK_WEBHOOK_URL set -- cannot queue")
        return {"status": "skipped", "platform": platform}

    if dry_run:
        log.info(f"[DRY RUN] Slack queue ({platform}): {text[:80]}...")
        return {"status": "dry_run", "platform": platform}

    import requests

    msg = f"*Manual Upload Needed: {platform.upper()}*\n\n{text}"
    if media_path:
        msg += f"\n\nMedia: `{media_path}`"

    requests.post(webhook, json={
        "text": msg,
        "channel": "#04-content-factory",
    }, timeout=5)

    log.info(f"Queued to Slack for {platform} manual upload")
    return {"status": "queued", "platform": platform}


def post_from_queue(dry_run: bool = False):
    """Find next ready item in content queue and post to all platforms."""
    if not OUTPUT_QUEUE.exists():
        log.info("No output queue found")
        return

    for item_dir in sorted(OUTPUT_QUEUE.iterdir()):
        meta_path = item_dir / "metadata.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text())
        if meta.get("status") != "ready_for_review":
            continue

        text = f"{meta.get('hook', '')}\n\n{meta.get('cta', '')}\n\n" + " ".join(
            f"#{kw.replace(' ', '')}" for kw in meta.get("keywords", [])
        )
        media = str(item_dir / "final.mp4") if (item_dir / "final.mp4").exists() else None

        results = []
        results.append(post_twitter(text, media, dry_run))
        results.append(post_linkedin(text, dry_run))
        results.append(queue_to_slack(text, media, "tiktok", dry_run))
        results.append(queue_to_slack(text, media, "instagram", dry_run))

        # Mark as posted
        meta["status"] = "posted" if not dry_run else "dry_run_posted"
        meta["posted_at"] = datetime.now().isoformat()
        meta["post_results"] = results
        meta_path.write_text(json.dumps(meta, indent=2))

        log.info(f"Processed: {item_dir.name}")
        break  # One item per run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Social Media Poster")
    parser.add_argument("--platform", choices=["twitter", "linkedin", "tiktok", "instagram", "all"],
                        default="all", help="Platform to post to")
    parser.add_argument("--text", help="Text to post (overrides queue)")
    parser.add_argument("--media", help="Path to media file")
    parser.add_argument("--from-queue", action="store_true", help="Post next item from content queue")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without posting")
    args = parser.parse_args()

    if args.from_queue:
        post_from_queue(args.dry_run)
    elif args.text:
        if args.platform in ("twitter", "all"):
            post_twitter(args.text, args.media, args.dry_run)
        if args.platform in ("linkedin", "all"):
            post_linkedin(args.text, args.dry_run)
        if args.platform in ("tiktok", "all"):
            queue_to_slack(args.text, args.media, "tiktok", args.dry_run)
        if args.platform in ("instagram", "all"):
            queue_to_slack(args.text, args.media, "instagram", args.dry_run)
    else:
        log.info("No action specified. Use --text or --from-queue.")
