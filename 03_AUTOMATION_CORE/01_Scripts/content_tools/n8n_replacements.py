"""n8n_replacements -- Python drop-in replacements for the two n8n workflows.

Why this exists
---------------
We retired the n8n workflows on 2026-04-24 (10,117 errors / 30 days, 100%
failure on the gdoc one, 0 executions on the voice one). These functions
preserve the same input/output contract callers used to send to n8n so we
can migrate them one at a time without breaking anything.

Workflow 1: hive-log-to-gdoc (Google Doc publisher)
---------------------------------------------------
n8n contract was POST {title, body, channel} -> Google Doc URL.
This module's `publish_gdoc(title, body, channel)` calls
`gdocs_bridge.publish_report()` directly (which uses the Everlight branded
template + report_template.py rendering, AND respects GDOCS_DISABLE_N8N=1
to skip n8n entirely). Auto-registers the resulting doc as a HiveArtifact
through hive_logger.current_run().

Workflow 2: hive-voice-action (proxy to localhost:8200)
-------------------------------------------------------
n8n contract was passthrough POST. Since the workflow had 0 executions in
30 days, all current callers that need voice-action hit localhost:8200
directly. `voice_action(payload)` is provided as a future-proof wrapper.

Public API
----------
    from content_tools.n8n_replacements import publish_gdoc, voice_action

    res = publish_gdoc(
        title="Daily Brief - 2026-04-24",
        body="## Today\\n- 5 new leads\\n- 1 deal closed",
        channel="#war-room",
    )
    # res = {"ok": True, "doc_link": "https://docs.google.com/...", "html_link": "...", "error": ""}
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("n8n_replacements")

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]

VOICE_HANDLER_URL = os.environ.get("HIVE_VOICE_HANDLER_URL", "http://localhost:8200/")


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


def _import_gdocs_bridge():
    """Locate gdocs_bridge using the same path resolution as hive_3format."""
    candidates = [
        _workspace() / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools",
        Path("/home/opc/content_tools"),
    ]
    for c in candidates:
        if c.exists() and str(c) not in sys.path:
            sys.path.insert(0, str(c))
    try:
        import gdocs_bridge  # type: ignore
        return gdocs_bridge
    except Exception as exc:
        log.warning("gdocs_bridge unavailable: %s", exc)
        return None


def _import_hive_logger():
    """Optional. If available, register the published doc as a HiveArtifact."""
    try:
        candidates = [
            _workspace() / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools",
            Path("/home/opc/content_tools"),
        ]
        for c in candidates:
            if c.exists() and str(c) not in sys.path:
                sys.path.insert(0, str(c))
        import hive_logger  # type: ignore
        return hive_logger
    except Exception:
        return None


def publish_gdoc(
    title: str,
    body: str,
    channel: str = "#war-room",
    folder_key: str = "ai_hive",
    summary: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Drop-in for the old `POST /webhook/.../hive-log-to-gdoc` call.

    Args:
        title: Document title.
        body: Markdown body content.
        channel: Slack channel for the announcement post.
        folder_key: Drive folder bucket (`ai_hive`, `broker_scout`, etc.)
        summary: One-line Slack summary. Defaults to first 200 chars of body.
        extra_meta: Optional metadata footer dict.

    Returns:
        {ok, doc_link, html_link, slack_ts, error}

    Routes through `gdocs_bridge.publish_report()` which:
      - Uses the Everlight gold Playfair/Inter branded template
      - Skips n8n entirely when GDOCS_DISABLE_N8N=1 (set on Oracle)
      - Posts to Slack with the branded link
    """
    bridge = _import_gdocs_bridge()
    if bridge is None:
        return {
            "ok": False,
            "doc_link": "",
            "html_link": "",
            "slack_ts": "",
            "error": "gdocs_bridge unavailable",
        }

    if summary is None:
        summary = (body or "")[:200].split("\n")[0] or title

    # Resolve folder using gdocs_bridge.FOLDER_MAP if available
    folder = None
    if hasattr(bridge, "FOLDER_MAP"):
        for path, key in bridge.FOLDER_MAP.items():
            if key == folder_key:
                folder = path
                break
    if folder is None:
        folder = "05_AI_Workers/Hive_Mind_Logs"

    # Inject branded meta footer
    if extra_meta:
        footer_lines = ["\n\n---\n\n## Meta\n"]
        for k, v in extra_meta.items():
            footer_lines.append(f"- **{k}**: {v}")
        body = (body or "") + "\n" + "\n".join(footer_lines) + "\n"

    try:
        result = bridge.publish_report(
            title=title,
            content=body,
            folder=folder,
            slack_channel=channel,
            summary=summary,
        )
    except Exception as exc:
        log.error("publish_report exception: %s", exc)
        return {"ok": False, "doc_link": "", "html_link": "", "slack_ts": "", "error": str(exc)}

    if not isinstance(result, dict):
        return {"ok": False, "doc_link": "", "html_link": "", "slack_ts": "", "error": "non-dict result"}

    doc_link = result.get("doc_link") or result.get("webViewLink") or ""
    html_link = result.get("html_link") or ""
    slack_ts_raw = result.get("slack_ts") or ""

    # Brand-consistent Slack post via branded_slack. This OVERWRITES whatever
    # ad-hoc post the gdocs_bridge fallback may have produced -- we want the
    # gold Block Kit card on every channel, every time, even when a doc link
    # is missing because the OAuth token is dead.
    branded_slack_ts = ""
    try:
        from branded_slack import post_branded_slack  # type: ignore
        slack_res = post_branded_slack(
            channel=channel,
            title=title,
            summary=summary,
            body=body[:2900] if body else None,
            report_url=html_link or None,
            doc_url=doc_link or None,
            agent_name="Hive Mind",
            agent_title="Everlight Ventures",
            category="report",
        )
        if slack_res.ok:
            branded_slack_ts = slack_res.ts
        else:
            log.warning("branded_slack post failed: %s", slack_res.error)
    except Exception as exc:
        log.warning("branded_slack import/call failed: %s", exc)

    # Prefer the branded ts; fall back to whatever gdocs_bridge produced
    slack_ts = branded_slack_ts or slack_ts_raw

    # Auto-register as HiveArtifact if a hive_logger run is active.
    hl = _import_hive_logger()
    if hl is not None:
        try:
            run = hl.current_run()
            if run is not None:
                if doc_link:
                    run.artifact("gdoc", url=doc_link, title=title)
                if html_link:
                    run.artifact("html", url=html_link, title=title)
                if slack_ts:
                    run.artifact("slack_post", url=f"slack://{channel}?ts={slack_ts}", title=title)
        except Exception:
            pass

    return {
        "ok": bool(result.get("success", True)) and bool(html_link or doc_link or slack_ts),
        "doc_link": doc_link,
        "html_link": html_link,
        "slack_ts": slack_ts,
        "error": result.get("error") or "",
    }


def voice_action(payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    """Drop-in for the old hive-voice-action n8n proxy.

    The n8n workflow was just a passthrough to http://localhost:8200/ so this
    function does the same thing -- POST the JSON, return the parsed response.
    """
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        VOICE_HANDLER_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return {"ok": True, "status": resp.status, "response": json.loads(raw) if raw.strip() else {}}
            except json.JSONDecodeError:
                return {"ok": True, "status": resp.status, "response": raw}
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"ok": False, "status": 0, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": 0, "error": repr(exc)}


# ── CLI ─────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    pg = sub.add_parser("gdoc", help="Publish a branded Google Doc")
    pg.add_argument("--title", required=True)
    pg.add_argument("--body", required=True, help="Markdown body or '@path/to/file.md' to read from disk")
    pg.add_argument("--channel", default="#war-room")
    pg.add_argument("--folder-key", default="ai_hive")

    pv = sub.add_parser("voice", help="Send a voice-action payload")
    pv.add_argument("--json", required=True, help="JSON payload (string or @path/to/file.json)")

    args = ap.parse_args()

    def _resolve(s: str) -> str:
        if s and s.startswith("@"):
            return Path(s[1:]).read_text(encoding="utf-8")
        return s

    if args.cmd == "gdoc":
        body = _resolve(args.body)
        out = publish_gdoc(args.title, body, args.channel, args.folder_key)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    if args.cmd == "voice":
        payload = json.loads(_resolve(args.json))
        out = voice_action(payload)
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
