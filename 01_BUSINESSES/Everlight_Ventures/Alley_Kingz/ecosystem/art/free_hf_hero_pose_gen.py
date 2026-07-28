#!/usr/bin/env python3
"""
AK 3D Forge -- free anonymous HF Space image generator (proven working 2026-07-16)
Run on e5. Requires: gradio_client (already installed on e5).

PROVEN WORKING (no HF token needed):
  - black-forest-labs/FLUX.1-schnell   (text-to-image, /infer)
  - multimodalart/FLUX.1-merged        (text-to-image, /infer)
  - InstantX/flux-IP-adapter           (image+text -> style-matched image, /process_image)
      THIS is the roster-consistency tool: feed canon bcardd_walk.jpg as the
      structure/style reference, vary the prompt per card, scale 0.5-0.7.

DEAD ENDS (do not retry):
  - prodia/fast-stable-diffusion, prodia/sdxl-stable-diffusion-xl -> Space PAUSED by owner
  - ByteDance/SDXL-Lightning -> generic RuntimeError (space-side bug, not quota)
  - segmind/Segmind-Stable-Diffusion -> Space itself crash-looping (torch/diffusers version conflict)
  - fal/realtime-stable-diffusion -> Space itself crash-looping (missing audioop module)
  - stabilityai/stable-diffusion-3.5-large -> works but shares the SAME ZeroGPU quota pool

HARD CONSTRAINT -- anonymous ZeroGPU quota:
  Observed: ~4 short generations (512-1216px, 4-28 steps) exhausted the anon
  per-IP quota. Error message on exhaustion gives a real countdown, e.g.:
    "You have exceeded your ZeroGPU quota (90s requested vs. 85s left).
     Try again in 5:33:41."
  That means the quota is a rolling window (~5-6h observed) that refills
  slowly, NOT a per-minute limiter. Budget roughly 60-90 GPU-seconds
  available per ~5-6h window per source IP (e5's IP). At ~15-25s per image
  that is ~3-4 free images per window -> full 106-character roster would
  take WEEKS of drip-feeding through this route. NOT viable as the sole
  batch method.

VERDICT: use this route for spot-checks / one-offs only. For the real
106-card batch, run FLUX.1-schnell (or SDXL) directly via diffusers on a
free Colab/Kaggle T4 GPU session -- same model, zero ZeroGPU tax, limited
only by the 12h session wall clock. That mirrors the mesh-generation
doctrine already proven for Tripo/Hunyuan.
"""
from gradio_client import Client, handle_file

CANON_REF = "/tmp/ak3d/in/bcardd_walk.jpg"

FULLBODY_BIPED_PROMPT_TEMPLATE = (
    "full body character reference sheet, anthropomorphic bipedal gangster dog "
    "standing upright on two legs like Ninja Turtles, jacked muscular humanoid "
    "torso and arms, standing straight both feet on ground, {details}, "
    "entire body visible head to feet including legs and feet, front facing, "
    "plain white studio background, no text, no watermark, video game character turnaround"
)

NEGATIVE = "quadruped, four legs on ground, blurry, cropped, bust, close up, no legs, extra limbs, text, watermark"


def gen_text2img(prompt, out_path, space="black-forest-labs/FLUX.1-schnell",
                  width=832, height=1216, steps=4):
    c = Client(space)
    result, seed = c.predict(prompt, 0, True, width, height, steps, api_name="/infer")
    path = result["path"] if isinstance(result, dict) else result
    _save(path, out_path)
    return out_path


def gen_style_ref(prompt, out_path, ref_image=CANON_REF, scale=0.6,
                   width=832, height=1216):
    """The roster-consistency call: locks style/structure to ref_image, prompt drives content."""
    c = Client("InstantX/flux-IP-adapter")
    result, seed = c.predict(
        handle_file(ref_image), prompt, scale, 0, True, width, height,
        api_name="/process_image"
    )
    path = result["path"] if isinstance(result, dict) else result
    _save(path, out_path)
    return out_path


def _save(webp_path, out_path):
    from PIL import Image
    im = Image.open(webp_path).convert("RGB")
    im.save(out_path)


if __name__ == "__main__":
    import sys
    details = sys.argv[1] if len(sys.argv) > 1 else (
        "wearing a gold crown, aviator sunglasses, cigar in mouth, "
        "thick gold cuban chain with letter B medallion, denim jeans, leather boots"
    )
    prompt = FULLBODY_BIPED_PROMPT_TEMPLATE.format(details=details)
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ak_img/test_out.png"
    print(gen_text2img(prompt, out))
