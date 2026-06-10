#!/usr/bin/env python3
"""
Daily screenshot -> structured-text ingestion. The CLI's "off-grid eyes."

WHY THIS EXISTS
---------------
The Claude Code native binary (proot Debian, arm64) occasionally SEGFAULTS when
it base64-encodes a full image *in-process*. It is the heaviest memory path the
CLI has, and this sandbox is memory-tight. This script takes that work OUT of the
CLI: it resizes each image and sends it to the Anthropic vision API in its own
short-lived process, then writes back plain TEXT. The CLI only ever reads text,
so the fragile path is never touched -- viewing 25 screenshots can't crash it.

Peak memory = ONE resized (~300 KB) image at a time, regardless of batch size.

USAGE
-----
  # Newest 25 screenshots from the default Android screenshots folder:
  python3 screenshot_ingest.py

  # A specific folder or a single file, newest 50:
  python3 screenshot_ingest.py /mnt/sdcard/DCIM/Screenshots --batch 50
  python3 screenshot_ingest.py ~/some/shot.png

  # Bump quality model for a dense screen:
  python3 screenshot_ingest.py --model sonnet

OUTPUT
------
  - One Markdown digest + one JSON sidecar under
    07_STAGING/Inbox/screenshot_ingest/<timestamp>/
  - A compact text digest on stdout so the CLI's NEXT turn can read the contents
    of every screenshot WITHOUT ever opening an image.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# --- reuse the existing, battle-tested resize logic (no parallel duplicate) ---
_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))
from claude_photo_prep import _resize_one, _collect, _fmt_size  # noqa: E402

from PIL import Image  # noqa: E402
import anthropic  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
DEFAULT_SOURCE = Path("/mnt/sdcard/DCIM/Screenshots")   # Android dumps shots here
OUT_ROOT = WORKSPACE / "07_STAGING/Inbox/screenshot_ingest"
DEFAULT_BATCH = 25                                      # Rich's daily volume
MAX_EDGE = 1568                                         # Anthropic's vision sweet spot
QUALITY = 85
MAX_TOKENS = 2048

MODELS = {
    "haiku": "claude-haiku-4-5",      # default: cheap, plenty for OCR/UI
    "sonnet": "claude-sonnet-4-6",    # dense / ambiguous screens
    "opus": "claude-opus-4-8",        # rarely needed for transcription
}

# ---------------------------------------------------------------------------
# The one knob worth tuning: what to PULL OUT of each screenshot.
# This prompt decides how "implementable into the system" the output is.
# Edit freely -- everything below it is plumbing.
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are the visual intake for an operator who screenshots \
things all day to feed into his automation system. Read this screenshot and return \
ONLY a JSON object (no prose, no code fences) with these keys:

{
  "title": "<=8 word label for what this screen is",
  "kind": "one of: app | website | code | terminal | chart | document | chat | social | dashboard | other",
  "source": "the app/site/tool shown, if identifiable, else null",
  "transcription": "ALL readable text on screen, in reading order, verbatim. Preserve numbers, URLs, code, prices, tickers exactly.",
  "summary": "1-2 sentences: what this screen shows and why someone screenshotted it",
  "action_items": ["concrete things to do / build / follow up on, [] if none"],
  "entities": ["notable names, URLs, $amounts, tickers, repos, file paths, [] if none"],
  "hashtags": ["#tags LITERALLY VISIBLE as text in the screenshot, lowercase, [] if none"],
  "suggested_hashtags": ["1-3 lowercase #tags to FILE this under based on its content; ALWAYS give at least one even if hashtags is empty"]
}

Be exhaustive in "transcription" -- it is the operator's eyes. Distinguish clearly: \
"hashtags" = tags you can actually SEE written on screen; "suggested_hashtags" = your \
own topical labels for organizing it. If the image is unreadable or blank, set \
transcription to "" and summary to a short note why."""


# ---------------------------------------------------------------------------
# API key: env -> encrypted vault -> .env  (reuse the Hive's existing chain)
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        from content_tools.secrets_vault import get_secret  # type: ignore
        key = (get_secret("ANTHROPIC_API_KEY", "") or "").strip()
        if key:
            return key
    except Exception:
        pass
    env_file = WORKSPACE / "03_AUTOMATION_CORE/03_Credentials/.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY=") and not line.lstrip().startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _parse_json_block(text: str) -> dict:
    """Tolerant parse: model usually returns clean JSON, but guard for stray prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    # Last resort: keep the raw text so nothing is silently lost.
    return {"title": "(unparsed)", "kind": "other", "source": None,
            "transcription": text, "summary": "(model did not return JSON)",
            "action_items": [], "entities": []}


def _ahash(img_path: Path) -> int:
    """64-bit average-hash (pure Pillow). Near-dupes share most bits."""
    with Image.open(img_path) as im:
        small = im.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        px = small.tobytes()  # 64 raw grayscale bytes (1/px); future-proof vs getdata()
    avg = sum(px) / len(px)
    bits = 0
    for i, p in enumerate(px):
        if p >= avg:
            bits |= 1 << i
    return bits


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _text_sim(a: str, b: str) -> float:
    """Word-set Jaccard. Orthogonal to the visual hash -- kills white-screen false dups."""
    wa = set(re.findall(r"\w+", (a or "").lower()))
    wb = set(re.findall(r"\w+", (b or "").lower()))
    if not wa and not wb:
        return 1.0          # two blank screens = genuinely alike
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def cluster_duplicates(results: list[dict], threshold: int = 5,
                       text_floor: float = 0.55) -> list[list[dict]]:
    """Cluster shots that are BOTH visually near-identical (aHash) AND textually
    similar (Jaccard). Requiring both signals avoids matching unrelated screens
    that merely share a lot of whitespace."""
    items = [d for d in results if d.get("_ahash") is not None]
    clusters: list[list[dict]] = []
    used: set[int] = set()
    for i, d in enumerate(items):
        if id(d) in used:
            continue
        group = [d]
        used.add(id(d))
        for e in items[i + 1:]:
            if id(e) in used:
                continue
            if (_hamming(d["_ahash"], e["_ahash"]) <= threshold
                    and _text_sim(d.get("transcription", ""), e.get("transcription", "")) >= text_floor):
                group.append(e)
                used.add(id(e))
        if len(group) > 1:
            clusters.append(group)
    return clusters


def _norm_tags(tags) -> list[str]:
    """Lowercase, ensure a leading '#', drop blanks/dupes, keep order."""
    out: list[str] = []
    for t in tags or []:
        t = str(t).strip().lower()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        if t not in out:
            out.append(t)
    return out


def transcribe_one(client: anthropic.Anthropic, src: Path, model_id: str,
                   max_tokens: int) -> dict:
    """Resize -> base64 -> one vision call -> structured dict. Bytes freed on return."""
    small = _resize_one(src, MAX_EDGE, QUALITY)            # writes a tiny JPEG to /tmp
    b64 = base64.standard_b64encode(small.read_bytes()).decode()
    resp = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    data = _parse_json_block(text)
    data["_source_file"] = str(src)
    data["_mtime"] = src.stat().st_mtime
    data["_ahash"] = _ahash(small)   # fingerprint the small copy we already made
    data["_tokens"] = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return data


# ---------------------------------------------------------------------------
# "Implement into the system" -- all three are FAIL-SAFE: any error is swallowed
# so a brain outage or a locked folder can never break the daily ingest.
# ---------------------------------------------------------------------------
def _safe_tag(tag: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", tag.lstrip("#").lower()) or "untagged"


def _primary_tag(d: dict) -> str:
    """Real hashtag wins; fall back to the model's suggested tag; else 'untagged'."""
    tags = d.get("_tags") or _norm_tags(d.get("suggested_hashtags"))
    return _safe_tag(tags[0]) if tags else "untagged"


def push_to_brain(kept: list[dict], stamp: str) -> int:
    """Queue one Blinko note per screenshot (local-first via the existing drain)."""
    try:
        from blinko_queue_drain import enqueue  # the canonical local-first queue
    except Exception:
        return 0
    n = 0
    for d in kept:
        tags = _norm_tags(list(d.get("hashtags") or []) + list(d.get("suggested_hashtags") or []))
        note = [f"# Screenshot: {d.get('title','(untitled)')}",
                (" ".join(tags) + " #hive/screenshot #hive/ingest").strip(), "",
                f"**Kind:** {d.get('kind','?')} | **Source:** {d.get('source') or 'unknown'} | "
                f"**File:** `{Path(d['_source_file']).name}` | **Captured:** {stamp}", "",
                d.get("summary", "")]
        if d.get("action_items"):
            note += ["", "## Action items"] + [f"- {a}" for a in d["action_items"]]
        if d.get("entities"):
            note += ["", "**Entities:** " + ", ".join(str(e) for e in d["entities"])]
        if d.get("transcription"):
            note += ["", "## Transcription", d["transcription"]]
        try:
            enqueue("\n".join(note))
            n += 1
        except Exception:
            pass
    return n


def sort_into_tag_folders(kept: list[dict], dest_root: Path) -> dict[str, list[str]]:
    """Copy (never move) each kept shot into its primary #tag folder. Idempotent."""
    moved: dict[str, list[str]] = {}
    for d in kept:
        src = Path(d["_source_file"])
        if not src.exists():
            continue
        tag = _primary_tag(d)
        folder = dest_root / tag
        try:
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / src.name
            if not dest.exists():
                shutil.copy2(src, dest)
            moved.setdefault(tag, []).append(src.name)
        except OSError:
            continue
    return moved


def write_action_items(kept: list[dict], stamp: str, out_dir: Path) -> int:
    """Per-run action_items.md + append to a rolling task list with checkboxes."""
    items = [(a, d.get("title", "?"), Path(d["_source_file"]).name)
             for d in kept for a in (d.get("action_items") or [])]
    body = [f"- [ ] {a}  _(from {title} / {fn})_" for a, title, fn in items]
    (out_dir / "action_items.md").write_text(
        "\n".join([f"# Action items -- {stamp}", ""] + body) + "\n")
    rolling = WORKSPACE / "07_STAGING/Inbox/screenshot_actions.md"
    try:
        rolling.parent.mkdir(parents=True, exist_ok=True)
        with rolling.open("a") as f:
            f.write(f"\n## {stamp}\n" + "\n".join(body) + "\n")
    except OSError:
        pass
    return len(items)


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch screenshot -> structured text (memory-safe).")
    ap.add_argument("target", nargs="?", default=str(DEFAULT_SOURCE),
                    help=f"Image file or folder (default: {DEFAULT_SOURCE})")
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                    help=f"Max images (newest first) from a folder (default {DEFAULT_BATCH})")
    ap.add_argument("--model", choices=MODELS, default="haiku",
                    help="Vision model (default haiku = cheapest)")
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--out", default=None, help="Override output directory")
    ap.add_argument("--no-brain", action="store_true", help="skip Blinko/RAG enqueue")
    ap.add_argument("--no-sort", action="store_true", help="skip copying into #tag folders")
    ap.add_argument("--no-tasks", action="store_true", help="skip the action-item task list")
    ap.add_argument("--tag-root", default=str(WORKSPACE / "04_MEDIA_LIBRARY/Photos/screenshots_by_tag"),
                    help="where #tag folders live")
    args = ap.parse_args()

    model_id = MODELS[args.model]

    key = load_api_key()
    if not key:
        print("ERROR: no ANTHROPIC_API_KEY in env, vault, or .env", file=sys.stderr)
        return 2
    client = anthropic.Anthropic(api_key=key)

    target = Path(args.target).expanduser()
    if not target.exists():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2
    try:
        sources = _collect(target, args.batch)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not sources:
        print(f"ERROR: no images in {target}", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = Path(args.out).expanduser() if args.out else (OUT_ROOT / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    failures: list[tuple[Path, str]] = []
    tok_in = tok_out = 0

    print(f"Reading {len(sources)} image(s) with {model_id}, one at a time...",
          file=sys.stderr)
    for i, src in enumerate(sources, 1):
        for attempt in (1, 2):  # one retry on transient API hiccups
            try:
                data = transcribe_one(client, src, model_id, args.max_tokens)
                results.append(data)
                tok_in += data["_tokens"]["in"]
                tok_out += data["_tokens"]["out"]
                print(f"  [{i}/{len(sources)}] {src.name} -> {data.get('title','?')}",
                      file=sys.stderr)
                break
            except (anthropic.APIError, OSError) as e:
                if attempt == 1:
                    time.sleep(2)
                    continue
                failures.append((src, str(e)))
                print(f"  [{i}/{len(sources)}] {src.name} -> FAILED: {e}", file=sys.stderr)

    # --- organize: group by real hashtag, cluster dupes, suggest tags for untagged ---
    for d in results:
        d["_tags"] = _norm_tags(d.get("hashtags"))
    by_tag: dict[str, list[dict]] = {}
    untagged: list[dict] = []
    for d in results:
        if d["_tags"]:
            for t in d["_tags"]:
                by_tag.setdefault(t, []).append(d)
        else:
            untagged.append(d)

    clusters = cluster_duplicates(results)
    # in each duplicate cluster keep the NEWEST; the rest are deletion candidates
    delete_candidates: list[dict] = []
    for group in clusters:
        keep = max(group, key=lambda d: d.get("_mtime", 0))
        for d in group:
            if d is not keep:
                delete_candidates.append({"file": d["_source_file"],
                                          "dup_of": keep["_source_file"]})

    organization = {
        "by_tag": {t: [d["_source_file"] for d in ds] for t, ds in sorted(by_tag.items())},
        "untagged": [{"file": d["_source_file"],
                      "suggested_hashtags": d.get("suggested_hashtags", [])} for d in untagged],
        "duplicate_clusters": [[d["_source_file"] for d in g] for g in clusters],
        "delete_candidates": delete_candidates,
    }

    # --- "implement into the system": brain + tag folders + tasks (fail-safe) ---
    dropped = {c["file"] for c in delete_candidates}
    kept = [d for d in results if d["_source_file"] not in dropped]
    into_system: dict = {}
    if not args.no_brain:
        into_system["brain_notes_queued"] = push_to_brain(kept, stamp)
    if not args.no_sort:
        moved = sort_into_tag_folders(kept, Path(args.tag_root).expanduser())
        into_system["sorted"] = {"count": sum(len(v) for v in moved.values()),
                                 "root": args.tag_root, "by_tag": moved}
    if not args.no_tasks:
        into_system["action_items"] = write_action_items(kept, stamp, out_dir)

    # --- durable artifacts ---
    (out_dir / "ingest.json").write_text(json.dumps(
        {"meta": {"stamp": stamp, "source": str(target), "model": model_id,
                  "read": len(results), "failed": len(failures)},
         "organization": organization, "into_system": into_system,
         "screenshots": results}, indent=2))

    md = [f"# Screenshot ingest -- {stamp}", "",
          f"Source: `{target}`  |  Model: `{model_id}`  |  {len(results)} read, "
          f"{len(failures)} failed, {len(delete_candidates)} dup(s) flagged", ""]
    if delete_candidates:
        md += ["## ⚠ Possible duplicates (review -- NOT auto-deleted)", ""]
        for group in clusters:
            keep = max(group, key=lambda d: d.get("_mtime", 0))
            md.append(f"- keep `{Path(keep['_source_file']).name}` -- "
                      + ", ".join(f"drop `{Path(d['_source_file']).name}`"
                                  for d in group if d is not keep))
        md += ["", f"Ready-to-run delete list: `{out_dir / 'delete_candidates.sh'}`", "", "---", ""]
    md += ["## Organized by hashtag", ""]
    for t, ds in sorted(by_tag.items()):
        md.append(f"### {t}")
        md += [f"- **{d.get('title','?')}** (`{Path(d['_source_file']).name}`) -- {d.get('summary','')}"
               for d in ds]
        md.append("")
    if untagged:
        md += ["## No hashtag found -- suggested tags", ""]
        for d in untagged:
            sug = " ".join(d.get("suggested_hashtags") or ["#untagged"])
            md.append(f"- **{d.get('title','?')}** (`{Path(d['_source_file']).name}`) "
                      f"-> {sug} -- {d.get('summary','')}")
        md.append("")
    md += ["## Full transcriptions", ""]
    for d in results:
        md += [f"### {d.get('title','(untitled)')}  ",
               f"*{d.get('kind','?')} - {d.get('source') or 'unknown'}* "
               f"`{Path(d['_source_file']).name}` {' '.join(d['_tags'])}".rstrip(), ""]
        if d.get("action_items"):
            md += ["**Action items:**"] + [f"- {a}" for a in d["action_items"]] + [""]
        if d.get("entities"):
            md += ["**Entities:** " + ", ".join(str(e) for e in d["entities"]), ""]
        md += ["<details><summary>transcription</summary>", "", "```",
               d.get("transcription", ""), "```", "</details>", "", "---", ""]
    md_path = out_dir / "ingest.md"
    md_path.write_text("\n".join(md))

    # ready-to-run (but NOT executed) deletion list -- operator pulls the trigger
    if delete_candidates:
        lines = ["#!/usr/bin/env bash",
                 "# Review, then run. Keeps the NEWEST of each duplicate cluster.",
                 "set -e"]
        lines += [f"rm -v {json.dumps(c['file'])}  # dup of {Path(c['dup_of']).name}"
                  for c in delete_candidates]
        (out_dir / "delete_candidates.sh").write_text("\n".join(lines) + "\n")

    # --- stdout digest: the CLI reads THIS (text), never the images ---
    print(f"\n=== {len(results)} screenshot(s) read -> {md_path} ===")
    if by_tag:
        print("\nBY HASHTAG:")
        for t, ds in sorted(by_tag.items()):
            print(f"  {t}: " + ", ".join(d.get("title", "?") for d in ds))
    if untagged:
        print("\nNO TAG (suggested):")
        for d in untagged:
            sug = " ".join(d.get("suggested_hashtags") or ["#untagged"])
            print(f"  {Path(d['_source_file']).name} -> {sug} -- {d.get('title','?')}")
    if delete_candidates:
        print(f"\nPOSSIBLE DUPLICATES ({len(delete_candidates)}) -- review "
              f"{out_dir / 'delete_candidates.sh'}:")
        for c in delete_candidates:
            print(f"  {Path(c['file']).name}  (dup of {Path(c['dup_of']).name})")
    for src, err in failures:
        print(f"\n[FAILED] {src.name}: {err}")

    if into_system:
        print("\nINTO SYSTEM:")
        if "brain_notes_queued" in into_system:
            print(f"  brain: {into_system['brain_notes_queued']} note(s) queued (Blinko, local-first)")
        if "sorted" in into_system:
            s = into_system["sorted"]
            print(f"  sorted: {s['count']} file(s) -> #tag folders under {s['root']}")
            for t, fs in sorted(s["by_tag"].items()):
                print(f"          #{t}: {len(fs)}")
        if "action_items" in into_system:
            print(f"  tasks: {into_system['action_items']} action item(s) -> "
                  f"07_STAGING/Inbox/screenshot_actions.md")

    print(f"\nTokens: {tok_in:,} in / {tok_out:,} out  |  artifacts: {out_dir}",
          file=sys.stderr)
    return 0 if results else 3


if __name__ == "__main__":
    raise SystemExit(main())
