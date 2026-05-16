"""
Lucrex autonomous research helper -- the Hive's self-learning loop.

When Lucrex (or any Hive persona) encounters an unknown -- a term, an agent,
a tool, a concept surfaced through agent-to-agent contact on moltbook -- this
script runs a 5-path parallel discovery, synthesizes findings, gate-checks
the result for privacy, stores it as a Hive knowledge artifact, and tries
to ingest it into Blinko (the Hive's RAG memory at e5-mother:1111).

PRIVACY DISCIPLINE:
  - The research itself reads PUBLIC moltbook content. Nothing internal flows
    OUT to moltbook (Lucrex's reads are passive).
  - The synthesis artifact gets gate-checked BEFORE storage -- ensuring no
    accidental cross-contamination if Lucrex's bearer token were to leak data
    in error responses.
  - Blinko ingestion is internal-only (e5-mother is tailnet, not public).
  - No reply / comment / DM is drafted or sent by this script. It only LEARNS.
    Acting on learnings requires explicit operator approval + the standard
    moltbook_post or comment helper, both gated.

USAGE:
    python3 lucrex_learn.py --topic "ClawHub skills"
    python3 lucrex_learn.py --topic "agent-to-agent protocol" --depth deep
    python3 lucrex_learn.py --topic "A2A" --notify-slack

Memory ref: feedback-public-ai-network-confidentiality-envelope
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

sys.path.insert(0, str(Path(__file__).parent))
from moltbook_confidentiality_gate import (  # noqa: E402
    ConfidentialityViolation,
    assert_safe,
    scan,
)

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
KEYS_FILE = WORKSPACE / "_state" / "moltbook" / "agent_keys.jsonl"
LEARNINGS_DIR = WORKSPACE / "_state" / "moltbook" / "lucrex_learnings"
LEARN_LOG = WORKSPACE / "_logs" / "lucrex_learn.jsonl"
BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")


def _load_api_key(persona: str = "lucrex") -> str:
    for line in KEYS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("persona") == persona and rec.get("response", {}).get("status") == 201:
            return rec["response"]["body"]["agent"]["api_key"]
    raise KeyError(f"no claimed-and-registered api_key for persona={persona}")


def _get(api_key: str, path: str, timeout: float = 10.0):
    url = f"https://www.moltbook.com/api/v1/{path}"
    req = urlrequest.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urlerror.HTTPError as e:
        return e.code, {}
    except Exception:
        return 0, {}


def _topic_to_slug(topic: str) -> str:
    s = topic.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:60] or "unknown"


def research(topic: str, *, persona: str = "lucrex", depth: str = "normal") -> dict:
    """Runs 5-path moltbook discovery for a topic. Returns structured findings."""
    api_key = _load_api_key(persona)
    findings = {
        "topic": topic,
        "persona": persona,
        "researched_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {},
    }

    # Path 1: direct search
    status, body = _get(api_key, f"search?q={urlparse.quote(topic)}")
    p1 = []
    for hit in (body.get("results") or [])[:15]:
        p1.append({
            "title": (hit.get("title") or "")[:200],
            "content_preview": (hit.get("content") or "")[:400],
            "author": (hit.get("author") or {}).get("name", "?"),
            "submolt": (hit.get("submolt") or {}).get("name", "?"),
        })
    findings["paths"]["direct_search"] = p1

    # Path 2: topic + "skills" (works for ClawHub-style ecosystem queries)
    status, body = _get(api_key, f"search?q={urlparse.quote(topic + ' skills')}")
    p2 = []
    for hit in (body.get("results") or [])[:10]:
        if topic.lower() in (hit.get("content") or "").lower() or topic.lower() in (hit.get("title") or "").lower():
            p2.append({
                "title": (hit.get("title") or "")[:200],
                "content_preview": (hit.get("content") or "")[:400],
                "author": (hit.get("author") or {}).get("name", "?"),
            })
    findings["paths"]["skills_search"] = p2

    # Path 3: high-karma adjacent terms (deep mode only)
    if depth == "deep":
        for adjacent in [topic + " api", topic + " protocol", topic + " architecture"]:
            status, body = _get(api_key, f"search?q={urlparse.quote(adjacent)}")
            for hit in (body.get("results") or [])[:3]:
                findings["paths"].setdefault("adjacent_terms", []).append({
                    "query": adjacent,
                    "title": (hit.get("title") or "")[:200],
                    "content_preview": (hit.get("content") or "")[:300],
                    "author": (hit.get("author") or {}).get("name", "?"),
                })

    # Path 4: probe topic-named endpoints (e.g. /clawhub, /skills)
    slug = _topic_to_slug(topic).split("_")[0]
    if slug:
        status, body = _get(api_key, slug)
        if status == 200 and isinstance(body, dict):
            findings["paths"]["endpoint_probe"] = {
                "path": f"/api/v1/{slug}",
                "keys": list(body.keys())[:10],
            }

    # Path 5: founder's official announcements -- check if topic mentioned
    # (we know ClawdClawderberg is the founder; relevant for moltbook-internal terms)
    status, body = _get(api_key, "feed?filter=announcements")
    p5 = []
    for hit in (body.get("posts") or [])[:5]:
        content = hit.get("content") or ""
        if topic.lower() in content.lower() or topic.lower() in (hit.get("title") or "").lower():
            p5.append({
                "title": (hit.get("title") or "")[:200],
                "content_preview": content[:500],
                "author": (hit.get("author") or {}).get("name", "?"),
            })
    findings["paths"]["announcements"] = p5

    return findings


def synthesize(findings: dict) -> str:
    """Produce a markdown synthesis from raw findings. Pure text-shaping --
    no opinions beyond what's in the source material. Returns markdown body."""
    topic = findings["topic"]
    lines = []
    lines.append(f"---")
    lines.append(f"learned_by: {findings['persona']}")
    lines.append(f"learned_at: {findings['researched_at_utc']}")
    lines.append(f"source: moltbook autonomous discovery")
    lines.append(f"topic: {topic}")
    lines.append(f"---")
    lines.append("")
    lines.append(f"# {topic} -- Hive Learning Note")
    lines.append("")
    lines.append("## What this is")
    lines.append("")
    lines.append(f"Autonomous research synthesis by {findings['persona']} on '{topic}'.")
    lines.append(f"5-path moltbook discovery; raw findings preserved below for audit.")
    lines.append("")

    # Aggregate the most-cited authors
    author_counts = {}
    all_titles = []
    for path_name, items in findings["paths"].items():
        if isinstance(items, list):
            for item in items:
                a = item.get("author")
                if a and a != "?":
                    author_counts[a] = author_counts.get(a, 0) + 1
                t = item.get("title")
                if t and t.strip():
                    all_titles.append(f"  - @{item.get('author', '?')}: {t}")

    top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_authors:
        lines.append("## Top contributors on this topic")
        lines.append("")
        for a, c in top_authors:
            lines.append(f"- **@{a}** ({c} mentions)")
        lines.append("")

    if all_titles:
        lines.append("## All discovered titles")
        lines.append("")
        for t in all_titles[:25]:
            lines.append(t)
        lines.append("")

    # Append a few content previews for actual substance
    lines.append("## Substantive previews")
    lines.append("")
    seen = set()
    preview_count = 0
    for path_name, items in findings["paths"].items():
        if not isinstance(items, list):
            continue
        for item in items:
            preview = (item.get("content_preview") or "").strip()
            if preview and len(preview) > 80 and preview not in seen:
                seen.add(preview)
                lines.append(f"### From @{item.get('author', '?')}")
                lines.append("")
                lines.append(f"> {preview}")
                lines.append("")
                preview_count += 1
                if preview_count >= 12:
                    break
        if preview_count >= 12:
            break

    lines.append("---")
    lines.append("")
    lines.append("## Next-action proposals (require Rich approval)")
    lines.append("")
    lines.append(f"1. Identify highest-karma agent in the top contributors above and engage with one of their recent posts on this topic.")
    lines.append(f"2. If topic is product/skill/tool-shaped, evaluate whether the Hive should publish a related capability OR consume one.")
    lines.append(f"3. If topic is a risk/threat, route to compliance review.")
    lines.append("")
    lines.append(f"_Lucrex does not post about this topic without operator approval._")

    return "\n".join(lines)


def store(synthesis_md: str, topic: str) -> Path:
    """Gate-check + write to _state/moltbook/lucrex_learnings/."""
    LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    # Gate-check the synthesis to ensure no internal-state leakage.
    # (Won't normally happen since we only read public moltbook, but defense
    # in depth: a malicious search result could include forbidden patterns.)
    hits = scan(synthesis_md)
    if hits:
        # Don't write. Log only.
        raise ConfidentialityViolation(
            persona="lucrex",
            category=hits[0]["category"],
            match=hits[0]["match"],
            snippet=hits[0]["snippet"],
        )
    slug = _topic_to_slug(topic)
    outfile = LEARNINGS_DIR / f"{slug}.md"
    outfile.write_text(synthesis_md)
    return outfile


def ingest_blinko(synthesis_md: str, topic: str) -> dict:
    """Push to Blinko RAG (e5-mother:1111). Returns status dict.
    Soft-fails if Blinko is unreachable (offline-first doctrine)."""
    payload = {
        "content": f"# Lucrex moltbook learning: {topic}\n\n#hive/moltbook #hive/lucrex #hive/learnings\n\n{synthesis_md}",
        "type": 1,
    }
    try:
        req = urlrequest.Request(
            f"{BLINKO_URL}/api/v1/note/upsert",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(req, timeout=5) as r:
            return {"status": r.status, "ok": True}
    except Exception as e:
        return {"status": 0, "ok": False, "error": repr(e)[:200]}


def log_run(findings: dict, outfile: Path, blinko_result: dict) -> None:
    LEARN_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "topic": findings["topic"],
        "persona": findings["persona"],
        "path_counts": {k: (len(v) if isinstance(v, list) else 1)
                        for k, v in findings["paths"].items()},
        "outfile": str(outfile),
        "blinko": blinko_result,
    }
    with LEARN_LOG.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        os.chmod(LEARN_LOG, 0o600)
    except Exception:
        pass


def _main(argv):
    ap = argparse.ArgumentParser(description="Lucrex autonomous research on a topic.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--persona", default="lucrex")
    ap.add_argument("--depth", default="normal", choices=["normal", "deep"])
    args = ap.parse_args(argv)

    print(f"== researching: {args.topic} (persona={args.persona} depth={args.depth}) ==")
    findings = research(args.topic, persona=args.persona, depth=args.depth)

    total_hits = sum(len(v) if isinstance(v, list) else 1 for v in findings["paths"].values())
    print(f"  paths probed: {list(findings['paths'].keys())}")
    print(f"  total raw hits: {total_hits}")

    synthesis = synthesize(findings)
    try:
        outfile = store(synthesis, args.topic)
    except ConfidentialityViolation as e:
        print(f"  [GATE BLOCK] synthesis would leak: {e}", file=sys.stderr)
        return 2

    blinko_result = ingest_blinko(synthesis, args.topic)
    log_run(findings, outfile, blinko_result)

    print(f"  written: {outfile}")
    print(f"  blinko: {blinko_result}")
    print()
    print("== FIRST 60 LINES OF SYNTHESIS ==")
    print("\n".join(synthesis.split("\n")[:60]))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
