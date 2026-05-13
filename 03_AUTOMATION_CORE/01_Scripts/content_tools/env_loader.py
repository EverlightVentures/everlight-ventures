"""
env_loader.py -- One call, all Everlight creds in os.environ.

Use it at the top of any script that needs SUPABASE_URL, RESEND_API_KEY,
GMAIL_APP_PASSWORD, OPENAI_API_KEY, etc.:

    from env_loader import load_env
    load_env()
    import os
    print(os.environ['SUPABASE_URL'])

Idempotent: safe to call multiple times. Already-set env vars are not
overwritten unless force=True.

Per memory rule: feedback_env_propagation_doctrine (2026-05-13).
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")


def load_env(env_path: Path | str | None = None, force: bool = False) -> int:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Returns the number of new variables added (or overwritten when force=True).
    Existing env vars take precedence unless force=True so explicit shell
    exports always win.
    """
    p = Path(env_path) if env_path else DEFAULT_ENV
    if not p.exists():
        return 0
    added = 0
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if not force and key in os.environ:
            continue
        os.environ[key] = value
        added += 1
    return added


# Convenience: auto-load when imported, can be turned off via env var
if os.environ.get("EVERLIGHT_ENV_AUTOLOAD", "1") == "1":
    load_env()
