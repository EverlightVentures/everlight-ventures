#!/usr/bin/env python3
"""
avatar_orchestrator.py -- Everlight Faceless Avatar Content Pipeline
Hive Mind Session: 84a032cf | Updated: 2026-03-05

Pipeline: Trend Fetch -> LLM Script -> TTS Audio -> Avatar Video -> Edit -> Stage -> Publish

Video backends (VIDEO_MODE env var):
  slideshow  -- ffmpeg Ken Burns zoompan from static image (default, free, ARM64)
  d-id       -- D-ID API lip-sync (free tier = 5 min, needs DID_API_KEY)
  sadtalker  -- SadTalker local (needs GPU setup)

Usage:
    python avatar_orchestrator.py --niche crypto --persona expert --count 3
    python avatar_orchestrator.py --product onyx --persona founder --count 2
    python avatar_orchestrator.py --dry-run
"""

import os
import json
import logging
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

# -- Paths (relative to workspace root) ----------------------------------------
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
SCRIPTS_INBOX  = WORKSPACE / "07_STAGING/Inbox/Scripts"
AVATAR_JOBS    = WORKSPACE / "07_STAGING/Processing/avatar_jobs"
OUTPUT_QUEUE   = WORKSPACE / "02_CONTENT_FACTORY/01_Queue/avatar_output"
AVATAR_ASSETS  = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/03_Content/Avatar_Assets"
METRICS_DIR    = WORKSPACE / "02_CONTENT_FACTORY/04_Analytics/avatar_metrics"
LOG_DIR        = WORKSPACE / "_logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "avatar_orchestrator.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("avatar_orchestrator")


# -- Persona configs -----------------------------------------------------------
PERSONAS = {
    "expert": {
        "name": "Alex",
        "niche_context": "crypto + AI finance expert",
        "voice_style": "authoritative, clear, energetic",
        "tone": "confident and educational",
    },
    "advisor": {
        "name": "Jordan",
        "niche_context": "blockchain investment advisor",
        "voice_style": "calm, measured, trustworthy",
        "tone": "analytical and approachable",
    },
    "hype": {
        "name": "Nova",
        "niche_context": "AI tools and automation enthusiast",
        "voice_style": "upbeat, fast-paced, engaging",
        "tone": "excited and motivating",
    },
    "founder": {
        "name": "Eli",
        "niche_context": "small business POS and retail tech founder",
        "voice_style": "direct, relatable, founder-mode",
        "tone": "been-there-done-that practical",
    },
    "builder": {
        "name": "Sage",
        "niche_context": "AI orchestration and multi-agent systems builder",
        "voice_style": "technical but approachable, builder energy",
        "tone": "show-don't-tell, demo-driven",
    },
}

# -- Product-specific script templates ----------------------------------------
PRODUCT_TEMPLATES = {
    "onyx": {
        "pain_points": [
            "Square charges 2.9% on every sale -- that adds up fast",
            "Your POS shouldn't cost more than your rent",
            "Toast, Clover, Square -- they all nickel-and-dime small shops",
        ],
        "hooks": [
            "I built a POS system because I was tired of paying Square 3% on every sale",
            "This $49/mo POS does everything Toast does -- without the contracts",
            "If you run a small shop, stop overpaying for your POS system",
        ],
        "cta": "Try Onyx POS free for 14 days -- no credit card needed. Link in bio.",
        "keywords": ["POS system", "small business", "retail tech", "payment processing"],
    },
    "hivemind": {
        "pain_points": [
            "You're paying for ChatGPT, Claude, and Gemini separately -- and none of them talk to each other",
            "Solo founders waste 2 hours a day switching between AI tools",
            "Your AI workflow is held together with copy-paste and prayer",
        ],
        "hooks": [
            "I use 4 AIs simultaneously and they run my business while I sleep",
            "Claude vs Gemini vs Codex -- why I use ALL of them together",
            "This is what an AI team looks like when they actually collaborate",
        ],
        "cta": "Join the Hive Mind waitlist -- early access for the first 100 builders. Link in bio.",
        "keywords": ["AI automation", "multi-agent AI", "Claude", "business automation"],
    },
    "crypto": {
        "pain_points": [],
        "hooks": [],
        "cta": "Follow for daily crypto + AI alpha.",
        "keywords": ["crypto", "XLM", "trading", "AI"],
    },
}

VIDEO_MODE = os.environ.get("VIDEO_MODE", "slideshow")


# -- Step 1: Script Generation ------------------------------------------------
def generate_scripts(niche: str, persona: str, count: int, dry_run: bool, product: str = "") -> list[dict]:
    """
    Call Claude/Anthropic API to generate short-form video scripts.
    Returns list of script dicts: {title, hook, body, cta, keywords}
    """
    p = PERSONAS.get(persona, PERSONAS["expert"])
    pt = PRODUCT_TEMPLATES.get(product, {})
    log.info(f"Generating {count} scripts | niche={niche} | persona={p['name']} | product={product or 'generic'}")

    product_context = ""
    if pt and pt.get("hooks"):
        product_context = f"""
You are marketing a specific product. Use these pain points and hook angles as inspiration:
Pain points: {json.dumps(pt['pain_points'])}
Example hooks: {json.dumps(pt['hooks'])}
Default CTA: {pt['cta']}
Target keywords: {json.dumps(pt['keywords'])}
"""

    prompt = f"""You are {p['name']}, a {p['niche_context']}.
Create {count} short-form video scripts (30-45 seconds) about {niche}.
Tone: {p['tone']}. Voice: {p['voice_style']}.
{product_context}
Each script must have:
- A viral HOOK (first 3 seconds -- pattern interrupt)
- A clear VALUE body (15-30 seconds of tip/insight)
- A CTA (link in bio, follow, comment a keyword)
- 3 SEO keywords for caption
Format as JSON array: [{{"title": "...", "hook": "...", "body": "...", "cta": "...", "keywords": [...]}}]
"""

    if dry_run:
        log.info("[DRY RUN] Skipping API call -- returning mock script")
        cta = pt.get("cta", "Follow for daily tips. Comment 'YES' for my free guide.")
        kw = pt.get("keywords", [niche, "AI", "2026"])
        return [{
            "title": f"[MOCK] {(product or niche).title()} Tip #{i+1}",
            "hook": (pt.get("hooks", [f"Nobody talks about this {niche} trick..."])[i % max(1, len(pt.get("hooks", [1])))]),
            "body": f"Here's what you need to know about {product or niche} in 2026...",
            "cta": cta,
            "keywords": kw,
        } for i in range(count)]

    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    return json.loads(raw.strip())


# -- Step 2: TTS Audio Generation ---------------------------------------------
def generate_tts(script: dict, job_dir: Path, dry_run: bool) -> Path:
    """
    Generate TTS audio from script body using ElevenLabs or local fallback.
    Returns path to .mp3 file.
    """
    audio_path = job_dir / "audio.mp3"
    full_text = f"{script['hook']} {script['body']} {script['cta']}"

    log.info(f"  TTS: generating audio ({len(full_text)} chars)")

    if dry_run:
        log.info("  [DRY RUN] Skipping TTS -- creating placeholder")
        audio_path.touch()
        return audio_path

    # ElevenLabs API (set ELEVENLABS_API_KEY in env)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        import requests
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # default: Bella
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": full_text, "model_id": "eleven_turbo_v2"},
        )
        resp.raise_for_status()
        audio_path.write_bytes(resp.content)
    else:
        # Local fallback: pyttsx3 or espeak
        log.warning("  No ELEVENLABS_API_KEY -- falling back to espeak")
        subprocess.run(["espeak", "-w", str(audio_path), full_text], check=False)

    return audio_path


# -- Step 3: Avatar Video Generation ------------------------------------------
def generate_avatar_video(script: dict, audio_path: Path, job_dir: Path, dry_run: bool) -> Path:
    """
    Generate video from static portrait + audio.
    Backends (set VIDEO_MODE env var):
      slideshow  -- ffmpeg Ken Burns zoompan (default, free, runs on ARM64)
      d-id       -- D-ID API lip-sync (free tier = 5 min video)
      sadtalker  -- SadTalker local inference (needs GPU)
    """
    video_path = job_dir / "avatar_raw.mp4"
    portrait = AVATAR_ASSETS / "base_portraits" / "default.jpg"

    log.info(f"  Avatar: generating video (mode={VIDEO_MODE})")

    if dry_run or not portrait.exists():
        if not portrait.exists():
            log.warning(f"  Portrait not found: {portrait}")
        log.info("  [DRY RUN] Skipping avatar gen -- creating placeholder")
        video_path.touch()
        return video_path

    if VIDEO_MODE == "d-id":
        video_path = _generate_did(portrait, audio_path, job_dir)
    elif VIDEO_MODE == "sadtalker":
        log.warning("  SadTalker mode -- requires local GPU setup")
        # subprocess.run(["python", "inference.py", ...], cwd="SadTalker/")
        video_path.touch()
    else:
        # Default: ffmpeg Ken Burns slideshow
        video_path = _generate_slideshow(portrait, audio_path, job_dir)

    return video_path


def _generate_slideshow(portrait: Path, audio_path: Path, job_dir: Path) -> Path:
    """ffmpeg Ken Burns zoompan from static image + audio track. Free, no API."""
    video_path = job_dir / "avatar_raw.mp4"

    # Get audio duration for video length
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 30.0
    frames = int(duration * 25)  # 25 fps

    # Ken Burns: slow zoom in from 100% to 115% over the clip
    # zoompan: z=zoom factor, d=duration in frames, s=output size (9:16 vertical)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(portrait),
        "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0005,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1080x1920:fps=25[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(video_path),
    ]

    log.info(f"  ffmpeg slideshow: {duration:.1f}s, {frames} frames")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"  ffmpeg error: {result.stderr[:300]}")
    else:
        log.info(f"  Slideshow video created: {video_path}")

    return video_path


def _generate_did(portrait: Path, audio_path: Path, job_dir: Path) -> Path:
    """D-ID API lip-sync. Free tier = 5 min of video. Async poll pattern."""
    video_path = job_dir / "avatar_raw.mp4"
    api_key = os.environ.get("DID_API_KEY")

    if not api_key:
        log.warning("  No DID_API_KEY set -- falling back to slideshow")
        return _generate_slideshow(portrait, audio_path, job_dir)

    import requests
    import base64

    # Upload portrait as base64
    portrait_b64 = base64.b64encode(portrait.read_bytes()).decode()
    portrait_url = f"data:image/jpeg;base64,{portrait_b64}"

    # Upload audio
    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode()
    audio_url = f"data:audio/mpeg;base64,{audio_b64}"

    # Create talk
    resp = requests.post(
        "https://api.d-id.com/talks",
        headers={
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "source_url": portrait_url,
            "script": {
                "type": "audio",
                "audio_url": audio_url,
            },
        },
    )
    if resp.status_code != 201:
        log.warning(f"  D-ID create failed ({resp.status_code}): {resp.text[:200]}")
        return _generate_slideshow(portrait, audio_path, job_dir)

    talk_id = resp.json().get("id")
    log.info(f"  D-ID talk created: {talk_id} -- polling for result")

    # Poll for completion (max 120s)
    for _ in range(24):
        time.sleep(5)
        status_resp = requests.get(
            f"https://api.d-id.com/talks/{talk_id}",
            headers={"Authorization": f"Basic {api_key}"},
        )
        data = status_resp.json()
        if data.get("status") == "done":
            result_url = data.get("result_url")
            if result_url:
                vid_resp = requests.get(result_url)
                video_path.write_bytes(vid_resp.content)
                log.info(f"  D-ID video downloaded: {video_path}")
            return video_path
        elif data.get("status") == "error":
            log.warning(f"  D-ID error: {data}")
            return _generate_slideshow(portrait, audio_path, job_dir)

    log.warning("  D-ID timeout after 120s -- falling back to slideshow")
    return _generate_slideshow(portrait, audio_path, job_dir)


# -- Step 4: ffmpeg Overlay (captions, logo, music) ---------------------------
def assemble_final_video(job_dir: Path, script: dict, dry_run: bool) -> Path:
    """
    Add captions, background music, and logo overlay via ffmpeg.
    Returns path to finished .mp4.
    """
    raw = job_dir / "avatar_raw.mp4"
    final = job_dir / "final.mp4"
    caption = f"{script['hook'][:60]}..."

    log.info(f"  ffmpeg: assembling final video")

    if dry_run:
        log.info("  [DRY RUN] Skipping ffmpeg -- placeholder final.mp4")
        final.touch()
        return final

    # Basic ffmpeg: add text overlay (expand as needed)
    cmd = [
        "ffmpeg", "-y", "-i", str(raw),
        "-vf", f"drawtext=text='{caption}':fontsize=40:fontcolor=white:x=10:y=h-80",
        "-c:a", "copy",
        str(final),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"  ffmpeg error: {result.stderr[:200]}")

    return final


# -- Step 5: Stage for Review -------------------------------------------------
def stage_for_review(job_dir: Path, script: dict, niche: str, persona: str):
    """Copy final video + metadata to the output queue for manual review before posting."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = OUTPUT_QUEUE / f"{ts}_{niche}_{persona}"
    dest.mkdir(parents=True, exist_ok=True)

    final = job_dir / "final.mp4"
    if final.exists() and final.stat().st_size > 0:
        import shutil
        shutil.copy2(final, dest / "final.mp4")

    meta = {
        "timestamp": ts,
        "niche": niche,
        "persona": persona,
        "title": script.get("title"),
        "hook": script.get("hook"),
        "keywords": script.get("keywords", []),
        "cta": script.get("cta"),
        "status": "ready_for_review",
    }
    (dest / "metadata.json").write_text(json.dumps(meta, indent=2))
    log.info(f"  Staged: {dest}")
    return dest


# -- Main Pipeline Run --------------------------------------------------------
def run_pipeline(niche: str, persona: str, count: int, dry_run: bool, product: str = ""):
    log.info(f"=== Avatar Pipeline START | niche={niche} persona={persona} product={product} count={count} dry={dry_run} mode={VIDEO_MODE} ===")

    scripts = generate_scripts(niche, persona, count, dry_run, product=product)

    for i, script in enumerate(scripts):
        log.info(f"Processing script {i+1}/{len(scripts)}: {script.get('title', 'untitled')}")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        job_dir = AVATAR_JOBS / f"job_{ts}"
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "script.json").write_text(json.dumps(script, indent=2))

        audio = generate_tts(script, job_dir, dry_run)
        video = generate_avatar_video(script, audio, job_dir, dry_run)
        final = assemble_final_video(job_dir, script, dry_run)
        staged = stage_for_review(job_dir, script, niche, persona)

        log.info(f"  Done: {staged}")

    log.info("=== Avatar Pipeline COMPLETE ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Everlight Avatar Content Orchestrator")
    parser.add_argument("--niche", default="crypto", help="Content niche (e.g. crypto, AI tools, trading)")
    parser.add_argument("--persona", default="expert", choices=list(PERSONAS.keys()))
    parser.add_argument("--product", default="", choices=["", "onyx", "hivemind", "crypto"],
                        help="Product to market (onyx, hivemind, crypto)")
    parser.add_argument("--count", type=int, default=3, help="Number of scripts to generate")
    parser.add_argument("--dry-run", action="store_true", help="Simulate pipeline without API calls")
    args = parser.parse_args()

    # Auto-set niche from product if not overridden
    if args.product and args.niche == "crypto":
        niche_map = {"onyx": "retail POS", "hivemind": "AI automation", "crypto": "crypto"}
        args.niche = niche_map.get(args.product, args.niche)

    run_pipeline(args.niche, args.persona, args.count, args.dry_run, product=args.product)
