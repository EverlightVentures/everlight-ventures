"""
Shared OpenAI DALL-E image generation utilities.

Consolidates duplicated functions from:
  - generate_book_images.py::generate_image, download_image
  - generate_covers.py::generate_image, download_image
  - build_cover_pdfs.py::generate_cover_image
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    raise ImportError("Install requests: pip install requests")

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "dall-e-3"
DEFAULT_SIZE = "1024x1024"


def get_api_key() -> str:
    """Retrieve the OpenAI API key from environment."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        logger.warning("OPENAI_API_KEY not set")
    return key


def generate_image(
    prompt: str,
    is_bw: bool = False,
    bw_prefix: str = "Professional children's coloring book line art, thick bold clean black outlines, white background, no color, black and white only, gentle grey shading for depth. Scene: ",
    color_prefix: str = "",
    style_suffix: str = "",
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    quality: str = "standard",
    max_retries: int = 2,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """Generate an image via OpenAI DALL-E API.

    Returns the temporary image URL on success, None on failure.
    """
    api_key = api_key or get_api_key()
    if not api_key:
        logger.error("No API key available for image generation")
        return None

    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if is_bw:
        full_prompt = f"{bw_prefix}{prompt}"
    else:
        full_prompt = f"{color_prefix}{prompt}" if color_prefix else prompt

    if style_suffix:
        full_prompt = f"{full_prompt} {style_suffix}"

    data = {
        "model": model,
        "prompt": full_prompt,
        "n": 1,
        "size": size,
        "quality": quality,
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            return response.json()["data"][0]["url"]
        except Exception as e:
            logger.warning("Image generation attempt %d failed: %s", attempt + 1, e)
            if hasattr(e, "response") and e.response is not None:
                logger.debug("Details: %s", e.response.text)
            if attempt < max_retries:
                time.sleep(2)
    return None


def download_image(url: str, save_path, timeout: int = 60) -> bool:
    """Download an image from a URL and save to disk.

    Args:
        url: Source URL.
        save_path: Destination path (str or Path).
        timeout: Request timeout in seconds.

    Returns True on success, False on failure.
    """
    save_path = Path(save_path)
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        logger.info("Saved: %s", save_path)
        return True
    except Exception as e:
        logger.error("Error downloading %s: %s", url, e)
        return False
