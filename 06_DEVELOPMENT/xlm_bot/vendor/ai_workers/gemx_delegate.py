#!/usr/bin/env python3
"""Portable Gemini delegate for cloud/Docker deployment.

Prefers Gemini SDK when configured, falls back to local Gemini CLI,
and finally uses OpenAI when that is the only configured provider.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal Gemini delegate")
    p.add_argument("--raw", action="store_true")
    p.add_argument("--mode", default="execute")
    p.add_argument("--output-format", default="text")
    p.add_argument("--model", default="gemini-2.0-flash")
    p.add_argument("prompt", nargs="+", help="Prompt text")
    return p.parse_args()


def _openai_model(name: str) -> str:
    model_map = {
        "": "gpt-4.1-mini",
        "flash": "gpt-4.1-mini",
        "pro": "gpt-4.1",
    }
    return model_map.get(name, name)


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:300]}") from exc


def _call_openai(prompt_text: str, model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    payload = {
        "model": _openai_model(model),
        "messages": [{"role": "user", "content": prompt_text}],
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        payload,
    )
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content", "")).strip()


def main() -> None:
    args = parse_args()
    prompt_text = " ".join(args.prompt)
    model = args.model

    try:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model)
            response = client.generate_content(prompt_text)
            print(response.text, end="")
            return

        if shutil.which("gemini"):
            cmd = ["gemini", "--model", model, prompt_text]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout, end="")
                return
            print(result.stderr, file=sys.stderr, end="")
            sys.exit(result.returncode)

        if os.environ.get("OPENAI_API_KEY", "").strip():
            print(_call_openai(prompt_text, model), end="")
            return

        print("ERROR: no Gemini/OpenAI provider is configured", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
