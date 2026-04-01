#!/usr/bin/env python3
"""Portable Claude delegate for cloud/Docker deployment.

Prefers Anthropic API, falls back to local Claude CLI when available,
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
    p = argparse.ArgumentParser(description="Minimal Claude CLI delegate")
    p.add_argument("--raw", action="store_true", help="Raw output mode")
    p.add_argument("--mode", default="execute", help="Execution mode (ignored, kept for compat)")
    p.add_argument("--output-format", default="text", help="Output format (ignored)")
    p.add_argument("--model", default="opus", help="Claude model to use")
    p.add_argument("--allowed-tool", action="append", dest="allowed_tools", default=[])
    p.add_argument("prompt", nargs="+", help="Prompt text")
    return p.parse_args()


def _anthropic_model(name: str) -> str:
    model_map = {
        "opus": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }
    return model_map.get(name, name)


def _openai_model(name: str) -> str:
    model_map = {
        "haiku": "gpt-4.1-mini",
        "sonnet": "gpt-4.1",
        "opus": "gpt-4.1",
        "": "gpt-4.1-mini",
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


def _call_anthropic(prompt_text: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    payload = {
        "model": _anthropic_model(model),
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        payload,
    )
    parts = data.get("content") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    return text.strip()


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
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            print(_call_anthropic(prompt_text, model), end="")
            return

        if shutil.which("claude"):
            cmd = ["claude", "-p", "--model", _anthropic_model(model)]
            for tool in (args.allowed_tools or []):
                cmd += ["--allowedTools", tool]
            cmd.append(prompt_text)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout, end="")
                return
            print(result.stderr, file=sys.stderr, end="")
            sys.exit(result.returncode)

        if os.environ.get("OPENAI_API_KEY", "").strip():
            print(_call_openai(prompt_text, model), end="")
            return

        print("ERROR: no Claude/OpenAI provider is configured", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
