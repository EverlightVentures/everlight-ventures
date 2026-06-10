"""
Moltbook post helper -- fire a post from a registered agent.

Reads the agent's api_key from _state/moltbook/agent_keys.jsonl, runs the
content through moltbook_confidentiality_gate.py, POSTs to /api/v1/posts,
returns the result.

Memory ref: feedback-public-ai-network-confidentiality-envelope
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

sys.path.insert(0, str(Path(__file__).parent))
from moltbook_confidentiality_gate import (  # noqa: E402
    ConfidentialityViolation,
    assert_safe,
)

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
KEYS_FILE = WORKSPACE / "_state" / "moltbook" / "agent_keys.jsonl"
POST_LOG = WORKSPACE / "_logs" / "moltbook_posts.jsonl"
POSTS_URL = "https://www.moltbook.com/api/v1/posts"


def load_api_key(persona: str) -> str:
    if not KEYS_FILE.exists():
        raise FileNotFoundError(f"no ledger at {KEYS_FILE} -- run moltbook_register.py first")
    # registration retries can leave failed records (body is an error string);
    # take the newest record that actually carries a key
    key = None
    for line in KEYS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("persona") != persona:
            continue
        body = (rec.get("response") or {}).get("body")
        if isinstance(body, dict):
            candidate = (body.get("agent") or {}).get("api_key")
            if candidate:
                key = candidate
    if key:
        return key
    raise KeyError(f"persona {persona!r} has no usable api_key in ledger")


def _http_post(url: str, headers: dict, body: dict, timeout: float = 20.0) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST", headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return {"status": resp.status, "body": json.loads(text) if text else {}}
    except urlerror.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        return {"status": e.code, "error": str(e), "body": body_text}


def post(persona: str, submolt: str, title: str, content: str,
         post_type: str = "text") -> dict:
    api_key = load_api_key(persona)
    combined = f"submolt: {submolt}\ntitle: {title}\ncontent: {content}"
    assert_safe(persona=persona, text=combined, context="moltbook_post")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "EverlightVentures-Hive/1.0",
    }
    body: dict = {
        "submolt_name": submolt,
        "title": title,
        "type": post_type,
    }
    if content:
        body["content"] = content

    result = _http_post(POSTS_URL, headers, body)

    POST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with POST_LOG.open("a") as fh:
        fh.write(json.dumps({
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "persona": persona,
            "submolt": submolt,
            "title": title,
            "content_length": len(content),
            "http_status": result.get("status"),
            "result": result,
        }, ensure_ascii=False) + "\n")
    try:
        os.chmod(POST_LOG, 0o600)
    except Exception:
        pass

    return result


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Post from a registered moltbook agent.")
    ap.add_argument("--persona", required=True)
    ap.add_argument("--submolt", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--content", default="")
    ap.add_argument("--type", default="text")
    args = ap.parse_args(argv)

    try:
        result = post(
            persona=args.persona,
            submolt=args.submolt,
            title=args.title,
            content=args.content,
            post_type=args.type,
        )
    except ConfidentialityViolation as e:
        print(f"BLOCKED -- confidentiality gate: {e}", file=sys.stderr)
        return 2

    print(f"HTTP {result.get('status')}")
    body = result.get("body")
    if isinstance(body, dict):
        post_obj = body.get("post") or {}
        print(f"post_id: {post_obj.get('id', '?')}")
        print(f"verification_status: {post_obj.get('verification_status', '?')}")
        print(json.dumps(body, indent=2)[:1500])
    else:
        print(body)
    return 0 if result.get("status") in (200, 201) else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
