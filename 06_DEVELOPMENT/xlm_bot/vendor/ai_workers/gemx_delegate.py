#!/usr/bin/env python3
"""Minimal Gemini delegate for cloud/Docker deployment.

Drop-in replacement for 03_AUTOMATION_CORE gemx_delegate.py that works
without the full AA_MY_DRIVE workspace.

Uses google-generativeai Python SDK directly (no CLI required).
Requires: GEMINI_API_KEY env var set.
"""
import argparse
import os
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal Gemini delegate")
    p.add_argument("--raw", action="store_true")
    p.add_argument("--mode", default="execute")
    p.add_argument("--output-format", default="text")
    p.add_argument("--model", default="gemini-1.5-pro-latest")
    p.add_argument("prompt", nargs="+", help="Prompt text")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    prompt_text = " ".join(args.prompt)
    model = args.model

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(model)
        response = client.generate_content(prompt_text)
        print(response.text, end="")
    except ImportError:
        print("ERROR: google-generativeai not installed. Run: pip install google-generativeai", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
