"""Seed the key registry from current key NAMES. Never copies secret values.

Sources:
  - .env  : take the left side of each `NAME=...` line (name only)
  - .mcp.json : walk all values; any secret-shaped value flags its key NAME as a LEAK
  - vault : list names only (best-effort)

Project / sub-avenue are inferred from name prefixes. Anything unmatched is tagged
UNCONFIRMED so Rich verifies rather than us guessing silently.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from token_economics import key_registry as kr

ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"
MCP_PATH = ROOT / ".mcp.json"
TODAY = "2026-06-25"

PREFIX_MAP = {
    "CF_": ("infra", "cloudflare"),
    "CLOUDFLARE_": ("infra", "cloudflare"),
    "SUPABASE_": ("infra", "supabase"),
    "ANTHROPIC_": ("llm", "shared-inference"),
    "OPENAI_": ("llm", "shared-inference"),
    "OPENROUTER_": ("llm", "fallback-routing"),
    "RESEND_": ("comms", "email"),
    "SLACK_": ("comms", "slack"),
    "ELEVENLABS_": ("comms", "voice"),
    "TELEGRAM_": ("bcardi", "telegram"),
    "BCARDD_": ("bcardi", "community"),
    "BCARDI_": ("bcardi", "community"),
    "AK_": ("alley_kingz", "game"),
    "ALLEY_": ("alley_kingz", "game"),
    "STRIPE_": ("revenue", "checkout"),
    "GITHUB_": ("infra", "ci-deploy"),
    "GH_": ("infra", "ci-deploy"),
    "KALSHI_": ("trading", "kalshi"),
    "COINBASE_": ("trading", "xlm-bot"),
    "FAL_": ("media", "image-gen"),
    "SEEDANCE_": ("media", "video-gen"),
    "TWILIO_": ("comms", "sms"),
    "GOOGLE_": ("infra", "google-workspace"),
    "GDOCS_": ("infra", "google-workspace"),
}


# Exact-name tags for keys that do not follow a clean prefix.
EXACT_NAME_MAP = {
    "ATTOM_API_KEY": ("broker_os", "property-data"),
    "BLINKO_URL": ("infra", "knowledge-rag"),
    "IMAP_HOST": ("comms", "email-inbound"),
    "IMAP_USER": ("comms", "email-inbound"),
    "IMAP_PASS": ("comms", "email-inbound"),
    "SMTP_HOST": ("comms", "email-smtp"),
    "SMTP_USER": ("comms", "email-smtp"),
    "SMTP_PASS": ("comms", "email-smtp"),
    "SMTP_PORT": ("comms", "email-smtp"),
    "SMTP_FROM": ("comms", "email-smtp"),
    "SMTP_PROVIDER": ("comms", "email-smtp"),
    "LEONARDO_API_KEY": ("media", "image-gen"),
    "PERPLEXITY_API_KEY": ("research", "perplexity"),
    "MARCUS_COLE_PHONE": ("comms", "voice-handler"),
    "SITE_BASE_URL": ("infra", "site-config"),
}


def infer(name: str) -> tuple[str, str]:
    if name in EXACT_NAME_MAP:
        return EXACT_NAME_MAP[name]
    for pre, tag in PREFIX_MAP.items():
        if name.upper().startswith(pre):
            return tag
    return ("UNCONFIRMED", "UNCONFIRMED")


def env_names(path: Path) -> list[str]:
    names = []
    if not path.exists():
        return names
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name = line.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            names.append(name)
    return sorted(set(names))


def leaked_mcp_names(path: Path) -> set[str]:
    """Return env-var NAMES in .mcp.json whose value is a literal secret.

    Robust to non-strict JSON: a raw regex scan over "KEY": "VALUE" pairs always
    runs, so a parse failure can never silently report a clean file.
    """
    leaks: set[str] = set()
    if not path.exists():
        return leaks
    text = path.read_text()
    # Method 1: structured walk (catches dict values AND bare list elements)
    try:
        leaks |= kr.scan_object_for_secrets(json.loads(text))
    except Exception:
        pass
    # Method 2: raw regex fallback (survives non-strict JSON)
    for m in re.finditer(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*"([^"]+)"', text):
        k, v = m.group(1), m.group(2)
        if kr.looks_like_secret(v):
            leaks.add(k)
    return leaks


def vault_names() -> set[str]:
    try:
        import subprocess
        out = subprocess.run(
            ["python3", str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools" / "secrets_vault.py"), "list"],
            capture_output=True, text=True, timeout=20,
        )
        return {ln.strip() for ln in out.stdout.splitlines() if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ln.strip())}
    except Exception:
        return set()


def main() -> int:
    names = env_names(ENV_PATH)
    leaks = leaked_mcp_names(MCP_PATH)
    named_leaks = {l for l in leaks if not l.endswith("[]")}
    positional_leaks = {l for l in leaks if l.endswith("[]")}
    vault = vault_names()
    all_names = sorted(set(names) | named_leaks)

    entries = []
    for name in all_names:
        project, sub = infer(name)
        in_vault = name in vault
        notes = "LEAK: hardcoded in .mcp.json (local, not in git); move to vault + rotate" if name in named_leaks else ""
        entries.append(kr.KeyEntry(
            key_name=name, project=project, sub_avenue=sub, provider=name.split("_")[0].lower(),
            owner="rich", created=TODAY, expires=None, refresh_cadence="unknown",
            monthly_cost_usd=0.0, status="leaked" if name in named_leaks else "live",
            value_location=f"vault:{name}" if in_vault else f"env:{name}", notes=notes,
        ))

    violations = kr.validate_registry(entries)
    if violations:
        print("ABORT - registry would contain secrets:")
        for v in violations:
            print("  -", v)
        return 1

    kr.save_registry(entries)
    unconfirmed = [e.key_name for e in entries if e.project == "UNCONFIRMED"]
    print(f"Wrote {len(entries)} keys to {kr.DEFAULT_PATH}")
    print(f"  vault-backed: {sum(1 for e in entries if e.value_location.startswith('vault:'))}")
    print(f"  env-only:     {sum(1 for e in entries if e.value_location.startswith('env:'))}")
    print(f"  named-key LEAKS in .mcp.json ({len(named_leaks)}): {sorted(named_leaks) if named_leaks else 'none'}")
    print(f"  positional LEAKS (token in an array, no key name) ({len(positional_leaks)}): {sorted(positional_leaks) if positional_leaks else 'none'}")
    print(f"  UNCONFIRMED project ({len(unconfirmed)}): {unconfirmed if unconfirmed else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
