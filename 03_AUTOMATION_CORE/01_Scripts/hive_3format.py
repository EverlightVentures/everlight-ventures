"""hive_3format.py - One-call wrapper for the Hive's 3-format publishing standard.

Every significant Hive output must produce:
  1. Styled HTML served from Oracle :8504/reports/
  2. Google Doc in Drive (via gdocs_bridge)
  3. Slack post linking to both

This wrapper loads env, imports the correct modules, and calls publish_report()
with sensible defaults so Hive agents never drop back to raw chat.postMessage.

Usage (from any Hive script):
    from hive_3format import publish

    publish(
        title="Phase 2 Wrap Upgrade",
        summary="Shipped 11 artifacts across folders 1-10.",
        markdown_body=long_markdown,
        folder_key="ai_hive",        # lookup key from FOLDER_MAP
        slack_channel="#war-room",
    )

Why this file exists:
The repo already has `content_tools/gdocs_bridge.py` with a `publish_report` fn,
but nothing imports it consistently because the import path differs across run
contexts (phone vs Oracle vs cron). This wrapper resolves path + env +
credentials once and exposes `publish()` - the entry point every new Hive
script should call.

Source directive: CLAUDE.md "3-Format Reporting Standard" section.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]

WAR_ROOM_TOKEN_ENV = "SLACK_WARROOM_TOKEN"
WAR_ROOM_CHANNEL_ID = "C0ANAU30UQ2"


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


def _load_env_once() -> None:
    if os.environ.get("_HIVE_ENV_LOADED"):
        return
    env_paths = [
        _workspace() / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
        Path("/home/opc/.env"),
    ]
    for env_path in env_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    os.environ["_HIVE_ENV_LOADED"] = "1"


def _import_gdocs_bridge():
    """Import content_tools.gdocs_bridge using a path-safe lookup."""
    ct = _workspace() / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
    if str(ct) not in sys.path:
        sys.path.insert(0, str(ct))
    try:
        import gdocs_bridge  # type: ignore
        return gdocs_bridge
    except Exception as exc:  # pragma: no cover
        print(f"[hive_3format] gdocs_bridge unavailable: {exc}", file=sys.stderr)
        return None


def _fallback_slack_post(channel: str, summary: str) -> bool:
    """Used only if publish_report fails entirely. Raw text, but never silent."""
    _load_env_once()
    token = os.environ.get(WAR_ROOM_TOKEN_ENV, "") or os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return False
    chan = channel if channel.startswith("C") else WAR_ROOM_CHANNEL_ID
    body = json.dumps({
        "channel": chan,
        "text": f"[3-format fallback] {summary}",
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return bool(json.loads(resp.read().decode()).get("ok"))
    except Exception:
        return False


def publish(
    title: str,
    summary: str,
    markdown_body: str,
    folder_key: str = "ai_hive",
    slack_channel: str = "#war-room",
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a Hive report in the 3-format standard.

    Args:
        title: Short headline.
        summary: One-liner Slack would show.
        markdown_body: Full markdown content.
        folder_key: One of `content_tools.gdocs_bridge.FOLDER_MAP` values.
                    Use "ai_hive" for generic Hive sessions, "broker_scout" for broker, etc.
        slack_channel: "#war-room", "#ft-consult", "#hive-alerts" etc.
        extra_meta: Optional dict merged into footer section of the doc.

    Returns:
        {success: bool, doc_link: str, html_link: str, slack_ts: str, error: str}
    """
    _load_env_once()
    bridge = _import_gdocs_bridge()
    if bridge is None:
        ok = _fallback_slack_post(slack_channel, f"{title} (degraded to raw text): {summary}")
        return {"success": False, "doc_link": "", "html_link": "", "slack_ts": "", "error": "gdocs_bridge import failed"}

    # Inject meta footer if provided
    if extra_meta:
        footer_lines = ["\n---\n\n## Meta\n"]
        for k, v in extra_meta.items():
            footer_lines.append(f"- **{k}**: {v}")
        markdown_body = markdown_body + "\n" + "\n".join(footer_lines) + "\n"

    folder = None
    if hasattr(bridge, "FOLDER_MAP"):
        for path, key in bridge.FOLDER_MAP.items():
            if key == folder_key:
                folder = path
                break
    if folder is None:
        folder = "05_AI_Workers/Hive_Mind_Logs"  # safe default

    try:
        result = bridge.publish_report(
            title=title,
            content=markdown_body,
            folder=folder,
            slack_channel=slack_channel,
            summary=summary,
        )
    except Exception as exc:
        traceback.print_exc()
        _fallback_slack_post(slack_channel, f"{title} (publish_report exception): {summary}")
        return {"success": False, "doc_link": "", "html_link": "", "slack_ts": "", "error": str(exc)}

    if not isinstance(result, dict):
        return {"success": False, "doc_link": "", "html_link": "", "slack_ts": "", "error": "non-dict publish_report result"}

    doc_link = result.get("doc_link") or result.get("webViewLink") or ""
    html_link = result.get("html_link") or ""
    slack_ts = result.get("slack_ts") or ""

    # Auto-register artifacts with the current hive_logger run (if any).
    # Wrapped so a logger failure never breaks publish().
    try:
        ct = _workspace() / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
        if str(ct) not in sys.path:
            sys.path.insert(0, str(ct))
        import hive_logger  # type: ignore
        run = hive_logger.current_run()
        if run is not None:
            if doc_link:
                run.artifact("gdoc", url=doc_link, title=title)
            if html_link:
                run.artifact("html", url=html_link, title=title)
            if slack_ts:
                run.artifact("slack_post", url=f"slack://{slack_channel}?ts={slack_ts}", title=title)
    except Exception:  # pragma: no cover
        pass

    return {
        "success": bool(result.get("success", True)),
        "doc_link": doc_link,
        "html_link": html_link,
        "slack_ts": slack_ts,
        "error": "",
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--body-file", required=True, help="Path to markdown body file")
    ap.add_argument("--folder-key", default="ai_hive")
    ap.add_argument("--channel", default="#war-room")
    args = ap.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8")
    out = publish(args.title, args.summary, body, args.folder_key, args.channel)
    print(json.dumps(out, indent=2))
    sys.exit(0 if out["success"] else 1)
