"""secrets_vault.py -- Fernet-encrypted secrets store with graceful .env fallback.

Why this exists: every API key (Anthropic, Resend, Supabase service-role,
Slack, Cloudflare, Twilio, Google OAuth) currently lives in
03_AUTOMATION_CORE/03_Credentials/.env in plain text. One leaked file, one
mis-scoped git add, one shoulder-surfed terminal and the whole estate is
compromised. This module wraps those secrets in a Fernet-encrypted file
mode 600 owned by the operator, keyed by a master key the operator holds
in the EV_VAULT_KEY env var.

Migration path is graceful on purpose: get_secret(name) tries the vault
first, then falls back to os.environ. Scripts can adopt the wrapper today
without waiting for the .env to be drained. As secrets migrate one by one,
the vault becomes the source of truth and .env becomes bootstrap-only.

CLI:
    python3 secrets_vault.py init                 # generate master key, empty vault
    python3 secrets_vault.py get NAME             # print decrypted value
    python3 secrets_vault.py set NAME VALUE       # encrypt + store
    python3 secrets_vault.py list                 # list secret names (not values)
    python3 secrets_vault.py rotate-master        # re-encrypt with new master key
    python3 secrets_vault.py self-test            # roundtrip verification

Lifted-and-adapted from hivemind_saas/backend/core/security.py get_fernet()
pattern. Independent of FastAPI / pydantic-settings so it runs anywhere.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from env_loader import load_env

load_env()

log = logging.getLogger("secrets_vault")

VAULT_DIR = Path(os.environ.get("EV_SECRETS_DIR", "/opt/everlight/secrets"))
VAULT_FILE = VAULT_DIR / "keys.enc"
VAULT_KEY_ENV = "EV_VAULT_KEY"


@dataclass
class VaultStatus:
    initialized: bool
    secret_count: int
    path: str
    master_key_present: bool


def _master_key() -> Optional[bytes]:
    raw = os.environ.get(VAULT_KEY_ENV, "").strip()
    return raw.encode() if raw else None


def _fernet() -> Optional[Fernet]:
    key = _master_key()
    if not key:
        return None
    try:
        return Fernet(key)
    except Exception as exc:
        log.warning("secrets_vault: master key in %s is not a valid Fernet key (%s)", VAULT_KEY_ENV, exc)
        return None


def _read_vault() -> dict[str, str]:
    if not VAULT_FILE.exists():
        return {}
    f = _fernet()
    if not f:
        return {}
    blob = VAULT_FILE.read_bytes()
    if not blob:
        return {}
    try:
        plain = f.decrypt(blob)
    except InvalidToken:
        log.error("secrets_vault: master key cannot decrypt %s (wrong key?)", VAULT_FILE)
        return {}
    return json.loads(plain.decode() or "{}")


def _write_vault(data: dict[str, str]) -> None:
    f = _fernet()
    if not f:
        raise RuntimeError(f"secrets_vault: cannot write without {VAULT_KEY_ENV} set")
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(VAULT_DIR, 0o700)
    except PermissionError:
        pass
    blob = f.encrypt(json.dumps(data, sort_keys=True).encode())
    VAULT_FILE.write_bytes(blob)
    try:
        os.chmod(VAULT_FILE, 0o600)
    except PermissionError:
        pass


def get_secret(name: str, default: str = "") -> str:
    """Vault first, then os.environ. Returns default when neither has it."""
    data = _read_vault()
    if name in data:
        return data[name]
    return os.environ.get(name, default)


def set_secret(name: str, value: str) -> None:
    """Encrypt + store. Requires EV_VAULT_KEY."""
    data = _read_vault()
    data[name] = value
    _write_vault(data)


def delete_secret(name: str) -> bool:
    data = _read_vault()
    if name not in data:
        return False
    del data[name]
    _write_vault(data)
    return True


def list_secrets() -> list[str]:
    return sorted(_read_vault().keys())


def status() -> VaultStatus:
    return VaultStatus(
        initialized=VAULT_FILE.exists(),
        secret_count=len(_read_vault()),
        path=str(VAULT_FILE),
        master_key_present=bool(_master_key()),
    )


def init_vault() -> str:
    """Create an empty encrypted vault file and return the freshly-generated
    master key for the operator to save in EV_VAULT_KEY. Refuses to overwrite
    an existing vault."""
    if VAULT_FILE.exists():
        raise FileExistsError(f"{VAULT_FILE} already exists; use rotate-master to change keys")
    new_key = Fernet.generate_key().decode()
    os.environ[VAULT_KEY_ENV] = new_key
    _write_vault({})
    return new_key


def rotate_master_key() -> str:
    """Re-encrypt every stored secret with a fresh master key. Returns the
    new key for the operator to save in EV_VAULT_KEY before the next call."""
    data = _read_vault()
    new_key = Fernet.generate_key().decode()
    os.environ[VAULT_KEY_ENV] = new_key
    _write_vault(data)
    return new_key


def _self_test() -> int:
    """Roundtrip a probe secret to prove the vault works. Cleans up after itself.

    Returns 0 on success, non-zero on failure. Per
    feedback_prove_real_not_simulated: claims of working require receipts.
    """
    probe_name = "__vault_self_test__"
    probe_value = "secret-roundtrip-probe-" + os.urandom(4).hex()
    if not _master_key():
        print(f"FAIL: {VAULT_KEY_ENV} not set; vault unusable")
        return 2
    try:
        set_secret(probe_name, probe_value)
        echoed = get_secret(probe_name)
        if echoed != probe_value:
            print(f"FAIL: roundtrip mismatch (expected {probe_value!r}, got {echoed!r})")
            return 3
        delete_secret(probe_name)
        if get_secret(probe_name, "<missing>") != "<missing>":
            print("FAIL: delete did not remove probe")
            return 4
        print(f"PASS: roundtrip ok; vault at {VAULT_FILE}; {len(list_secrets())} stored secrets")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc!r}")
        return 1


def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: secrets_vault.py {init|get NAME|set NAME VALUE|delete NAME|list|status|rotate-master|self-test}")
        return 1
    cmd = argv[1]
    if cmd == "init":
        try:
            key = init_vault()
        except FileExistsError as e:
            print(str(e))
            return 1
        print("Vault initialized at", VAULT_FILE)
        print()
        print(f"Save this in {VAULT_KEY_ENV} (export in shell + add to .env). It will NOT be printed again:")
        print(key)
        return 0
    if cmd == "status":
        st = status()
        print(json.dumps(st.__dict__, indent=2))
        return 0
    if cmd == "list":
        for n in list_secrets():
            print(n)
        return 0
    if cmd == "get" and len(argv) >= 3:
        v = get_secret(argv[2])
        if not v:
            print(f"(no value for {argv[2]})", file=sys.stderr)
            return 1
        print(v)
        return 0
    if cmd == "set" and len(argv) >= 4:
        set_secret(argv[2], argv[3])
        print(f"stored {argv[2]} ({len(argv[3])} chars)")
        return 0
    if cmd == "delete" and len(argv) >= 3:
        ok = delete_secret(argv[2])
        print("deleted" if ok else "(not present)")
        return 0 if ok else 1
    if cmd == "rotate-master":
        new_key = rotate_master_key()
        print(f"Re-encrypted {len(list_secrets())} secrets. New {VAULT_KEY_ENV}:")
        print(new_key)
        return 0
    if cmd == "self-test":
        return _self_test()
    print("unknown command:", cmd)
    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
