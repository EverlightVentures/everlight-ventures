# render/image_provider.py
"""Pluggable background-image source. Tests use FakeProvider (offline, deterministic).
Production uses FalFluxProvider (fal.ai Flux Dev), gated behind FAL_KEY."""
from typing import Protocol
import hashlib
from PIL import Image

class ImageProvider(Protocol):
    def generate(self, prompt: str, width: int, height: int) -> Image.Image: ...

class FakeProvider:
    """Deterministic gradient seeded by the prompt; no network."""
    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        seed = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
        r, g, b = (seed % 256), (seed // 256 % 256), (seed // 65536 % 256)
        img = Image.new("RGB", (width, height), (r, g, b))
        # vertical gradient so it's visibly an image, still deterministic
        px = img.load()
        for y in range(height):
            shade = int(255 * y / max(height - 1, 1))
            for x in range(width):
                px[x, y] = ((r + shade) % 256, (g + shade) % 256, (b + shade) % 256)
        return img

class FalFluxProvider:
    """Real provider. Integration-only; not exercised by unit tests."""
    def __init__(self, api_key: str, model: str = "fal-ai/flux/dev"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        import io, requests  # local import keeps unit tests dependency-light
        resp = requests.post(
            f"https://fal.run/{self.model}",
            headers={"Authorization": f"Key {self.api_key}"},
            json={"prompt": prompt, "image_size": {"width": width, "height": height}},
            timeout=120,
        )
        resp.raise_for_status()
        url = resp.json()["images"][0]["url"]
        img_resp = requests.get(url, timeout=120)
        img_resp.raise_for_status()
        img_bytes = img_resp.content
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
