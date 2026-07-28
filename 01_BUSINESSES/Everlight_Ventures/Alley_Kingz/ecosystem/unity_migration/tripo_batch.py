#!/usr/bin/env python3
"""
Alley Kingz -- Tripo3D batch pipeline.

Reads cards.json (the 106-card manifest already exported from canon.js), tiers each
card (hero vs standard), pushes its reference image through Tripo's v2 OpenAPI, and
downloads the finished GLB into the Unity migration scaffold.

Resume-safe: every task is recorded in the run manifest, so a re-run picks up where it
stopped instead of re-spending credits. Credit spend is capped by --max-credits.

Usage:
    export TRIPO_API_KEY=tsk_xxx
    python3 tripo_batch.py --input-dir ./refs --dry-run          # plan + credit estimate
    python3 tripo_batch.py --input-dir ./refs --max-credits 2900 # real run

Docs: https://platform.tripo3d.ai/docs/generation
"""
import argparse, json, os, sys, time
from pathlib import Path

import requests

API = "https://api.tripo3d.ai/v2/openapi"

# Credit costs per tier. CONFIRM against the live pricing page before a full run --
# these drive the spend cap. Observed in the studio UI: v3.1 Best Quality = 55.
TIERS = {
    "hero":     {"model_version": "v3.1-20250625", "credits": 55, "texture": True},
    "standard": {"model_version": "v2.5-20250123", "credits": 20, "texture": True},
}


def upload_image(session, path):
    with open(path, "rb") as fh:
        r = session.post(f"{API}/upload", files={"file": (Path(path).name, fh)}, timeout=120)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 0:
        raise RuntimeError(f"upload failed for {path}: {body}")
    return body["data"]["image_token"]


def create_task(session, file_token, ext, tier):
    cfg = TIERS[tier]
    payload = {
        "type": "image_to_model",
        "file": {"type": ext, "file_token": file_token},
        "model_version": cfg["model_version"],
        "texture": cfg["texture"],
        # Quad topology + a game-sane budget. Tripo's smart retopo is the whole reason
        # we are paying instead of using the free meshers.
        "quad": True,
        "face_limit": 20000,
    }
    r = session.post(f"{API}/task", json=payload, timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 0:
        raise RuntimeError(f"task create failed: {body}")
    return body["data"]["task_id"]


def poll_task(session, task_id, timeout=900, interval=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = session.get(f"{API}/task/{task_id}", timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        status = data.get("status")
        if status == "success":
            out = data.get("output", {})
            return out.get("pbr_model") or out.get("model")
        if status in ("failed", "cancelled", "banned", "expired"):
            raise RuntimeError(f"task {task_id} ended: {status}")
        time.sleep(interval)
    raise TimeoutError(f"task {task_id} still running after {timeout}s")


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 16):
                fh.write(chunk)
    return dest.stat().st_size


def load_manifest(path):
    return json.loads(path.read_text()) if path.exists() else {"runs": {}, "credits_spent": 0}


def save_manifest(path, data):
    path.write_text(json.dumps(data, indent=2))


def find_ref(input_dir, card):
    """Reference image per card. Full-body standing refs live here, named by card number."""
    num = str(card.get("cardNumber", "")).zfill(4)
    for ext in ("png", "jpg", "jpeg", "webp"):
        hit = Path(input_dir) / f"{num}.{ext}"
        if hit.exists():
            return hit
    return None


def tier_for(card, hero_rarities, forced_heroes):
    """The roster already knows who the heroes are -- rarity drives the premium pass."""
    num = str(card.get("cardNumber", "")).zfill(4)
    if num in forced_heroes:
        return "hero"
    return "hero" if card.get("rarity") in hero_rarities else "standard"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", default=str(Path(__file__).parent / "cards.json"))
    ap.add_argument("--input-dir", required=True, help="full-body reference images, named 0001.png ...")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent / "Assets/AlleyKingz/Models"))
    ap.add_argument("--manifest", default=str(Path(__file__).parent / "tripo_run_manifest.json"))
    ap.add_argument("--heroes", default="", help="extra card numbers to force to hero tier")
    ap.add_argument("--hero-rarities", default="Mythic,Legendary",
                    help="rarities that get the premium pass (4 Mythic + 10 Legendary = 14 heroes)")
    ap.add_argument("--max-credits", type=int, default=2900, help="hard spend cap for this run")
    ap.add_argument("--limit", type=int, default=0, help="only process N cards (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("TRIPO_API_KEY")
    if not key and not args.dry_run:
        sys.exit("TRIPO_API_KEY not set. Get it from platform.tripo3d.ai after subscribing to Pro.")

    cards = json.loads(Path(args.cards).read_text())["cards"]
    forced_heroes = {h.strip().zfill(4) for h in args.heroes.split(",") if h.strip()}
    hero_rarities = {r.strip() for r in args.hero_rarities.split(",") if r.strip()}
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}"})

    planned, missing = [], []
    for card in cards:
        num = str(card.get("cardNumber", "")).zfill(4)
        if manifest["runs"].get(num, {}).get("status") == "done":
            continue
        ref = find_ref(args.input_dir, card)
        if not ref:
            missing.append(num)
            continue
        planned.append((num, card, ref, tier_for(card, hero_rarities, forced_heroes)))

    if args.limit:
        planned = planned[: args.limit]

    est = sum(TIERS[t]["credits"] for _, _, _, t in planned)
    print(f"cards={len(cards)} ready={len(planned)} missing_ref={len(missing)} est_credits={est}")
    if missing:
        print(f"  no reference image for: {', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''}")
    if args.dry_run:
        print("dry run -- nothing submitted")
        return
    if est > args.max_credits:
        sys.exit(f"ABORT: estimate {est} exceeds --max-credits {args.max_credits}. Narrow with --limit.")

    for num, card, ref, tier in planned:
        name = card.get("name", num)
        try:
            token = upload_image(session, ref)
            task_id = create_task(session, token, ref.suffix.lstrip("."), tier)
            manifest["runs"][num] = {"status": "running", "task_id": task_id, "tier": tier, "name": name}
            save_manifest(manifest_path, manifest)

            url = poll_task(session, task_id)
            dest = Path(args.out_dir) / tier / f"{num}_{name.replace(' ', '_')}.glb"
            size = download(url, dest)

            manifest["credits_spent"] += TIERS[tier]["credits"]
            manifest["runs"][num] = {"status": "done", "task_id": task_id, "tier": tier,
                                     "name": name, "glb": str(dest), "bytes": size}
            print(f"  OK {num} {name} [{tier}] -> {dest.name} ({size//1024} KB) "
                  f"| spent={manifest['credits_spent']}")
        except Exception as exc:
            manifest["runs"][num] = {"status": "error", "tier": tier, "name": name, "error": str(exc)}
            print(f"  FAIL {num} {name}: {exc}")
        finally:
            save_manifest(manifest_path, manifest)

        if manifest["credits_spent"] >= args.max_credits:
            print(f"STOP: hit credit cap {args.max_credits}")
            break

    done = sum(1 for r in manifest["runs"].values() if r.get("status") == "done")
    print(f"done={done} credits_spent={manifest['credits_spent']}")


if __name__ == "__main__":
    main()
