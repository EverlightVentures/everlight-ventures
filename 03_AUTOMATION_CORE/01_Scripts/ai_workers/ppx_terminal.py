#!/usr/bin/env python3
"""
Perplexity Terminal Tool - Call Perplexity AI from command line
Usage: ppx "your research question here"
"""

import sys
import os
import argparse
import urllib.parse
import subprocess
import shutil
from pathlib import Path

ENV_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value

def load_env():
    """Load keys from .env file"""
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), _strip_wrapping_quotes(value))


def mask_key(key: str) -> str:
    if not key:
        return "<missing>"
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"

def get_api_key():
    """Get Perplexity API key from env/.env; returns None if missing."""
    load_env()
    return os.getenv('PERPLEXITY_API_KEY') or os.getenv('PPLX_API_KEY')

def load_api_key():
    """Load Perplexity API key or exit with guidance."""
    key = get_api_key()
    if key:
        return key
    print("❌ No Perplexity API key found.")
    print("   Checked: PERPLEXITY_API_KEY, PPLX_API_KEY")
    print(f"   Add it to: {ENV_FILE}")
    print("   Get your key from: https://www.perplexity.ai/settings/api")
    sys.exit(1)

class PerplexityAuthError(Exception):
    pass

class PerplexityRequestError(Exception):
    pass

def call_perplexity(prompt, api_key):
    """Call Perplexity AI API"""
    import requests

    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    model = os.getenv("PERPLEXITY_MODEL", "sonar")
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful research assistant that provides accurate, up-to-date information with sources."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)
    if response.status_code == 401:
        raise PerplexityAuthError(
            "Perplexity authentication failed (401 Unauthorized).\n"
            "   Your configured key is not authorized for this API.\n"
            f"   Key in use: {mask_key(api_key)}\n"
            "   Action: generate a new API key at https://www.perplexity.ai/settings/api\n"
            f"   Then update PERPLEXITY_API_KEY in: {ENV_FILE}"
        )

    try:
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        body = ""
        if getattr(e, "response", None) is not None:
            body = f"\nResponse: {e.response.text}"
        raise PerplexityRequestError(f"API Error: {e}{body}") from e

    content = result['choices'][0]['message']['content']
    citations = result.get('citations', [])
    return content, citations

def build_web_url(prompt: str) -> str:
    return "https://www.perplexity.ai/search?q=" + urllib.parse.quote_plus(prompt)

def open_url(url: str) -> tuple[bool, str]:
    browser_env = os.getenv("BROWSER")
    candidates = []
    if browser_env:
        candidates.append(([browser_env, url], browser_env))
    if shutil.which("termux-open-url"):
        candidates.append((["termux-open-url", url], "termux-open-url"))
    if shutil.which("xdg-open"):
        candidates.append((["xdg-open", url], "xdg-open"))
    if shutil.which("open"):
        candidates.append((["open", url], "open"))
    if shutil.which("am"):
        candidates.append((["am", "start", "-a", "android.intent.action.VIEW", "-d", url], "am"))

    for cmd, label in candidates:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0:
                return True, label
        except Exception:
            continue
    return False, "none"

def run_web_mode(prompt: str) -> int:
    url = build_web_url(prompt)
    ok, opener = open_url(url)
    print("🌐 Perplexity Web Mode")
    print(f"Query URL: {url}")
    if ok:
        print(f"Opened in browser via: {opener}")
    else:
        print("⚠️ Could not auto-open browser. Open the URL above manually.")
    print("Note: web mode is interactive and does not return structured API data to bots.")
    return 0

def parse_args():
    parser = argparse.ArgumentParser(
        description="Perplexity CLI helper (API mode + web fallback mode)."
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "api", "web"],
        default=os.getenv("PPX_MODE", "auto"),
        help="auto=try API then fallback to web, api=API only, web=browser only",
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Research query",
    )
    return parser.parse_args()

def main():
    if len(sys.argv) < 2:
        print("Usage: ppx [--mode auto|api|web] \"your research question here\"")
        print("\nExamples:")
        print("  ppx --mode auto \"What are the latest developments in AI?\"")
        print("  ppx \"Best payment rails for crypto 2026\"")
        print("  ppx --mode web \"Latest XLM news\"")
        print("  PERPLEXITY_MODEL=sonar-pro ppx \"Deep research question\"")
        sys.exit(1)

    args = parse_args()
    prompt = " ".join(args.query)

    print("🔍 Perplexity is researching...\n")

    if args.mode == "web":
        sys.exit(run_web_mode(prompt))

    api_key = get_api_key()
    if args.mode == "api":
        if not api_key:
            load_api_key()
            return
        try:
            response, citations = call_perplexity(prompt, api_key)
        except PerplexityAuthError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except PerplexityRequestError as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(response)
        if citations:
            print("\n📚 Sources:")
            for i, citation in enumerate(citations, 1):
                print(f"  [{i}] {citation}")
        print()
        return

    # auto mode: try API first (if key exists), then fallback to web mode.
    if api_key:
        try:
            response, citations = call_perplexity(prompt, api_key)
            print(response)
            if citations:
                print("\n📚 Sources:")
                for i, citation in enumerate(citations, 1):
                    print(f"  [{i}] {citation}")
            print()
            return
        except PerplexityAuthError as e:
            print(f"⚠️ {e}")
            print("↪ Falling back to web mode...\n")
            sys.exit(run_web_mode(prompt))
        except PerplexityRequestError as e:
            print(f"⚠️ {e}")
            print("↪ Falling back to web mode...\n")
            sys.exit(run_web_mode(prompt))

    print("⚠️ No valid API key found; falling back to web mode.\n")
    sys.exit(run_web_mode(prompt))

if __name__ == "__main__":
    main()
