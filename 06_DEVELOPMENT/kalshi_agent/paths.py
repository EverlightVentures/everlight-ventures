"""Cross-host path + secret resolution.

The bot runs on the phone (workspace SOT) AND e5-mother (24/7 mirror). Each host
holds its OWN local copy of the credentials .env at a different root. This
resolves the workspace + secrets across hosts with FAILOVER: try one root, then
the other, so the bot finds its keys wherever it runs ("phone no -> e5, e5 no ->
phone"). Keys are read from the local file, never printed, never committed.
"""
import os

# Candidate workspace roots, in failover order.
CANDIDATE_ROOTS = [
    "/mnt/sdcard/AA_MY_DRIVE",     # phone (workspace source of truth)
    "/home/ubuntu/AA_MY_DRIVE",    # e5-mother mirror
    "/home/opc/AA_MY_DRIVE",       # oracle fallback
]
_CRED_REL = "03_AUTOMATION_CORE/03_Credentials"


def workspace_root() -> str:
    for r in CANDIDATE_ROOTS:
        if os.path.isdir(r):
            return r
    return CANDIDATE_ROOTS[0]


def credentials_env() -> str:
    """Path to the FIRST existing .env across candidate roots (failover)."""
    for r in CANDIDATE_ROOTS:
        p = os.path.join(r, _CRED_REL, ".env")
        if os.path.isfile(p):
            return p
    return os.path.join(CANDIDATE_ROOTS[0], _CRED_REL, ".env")


def wallet_key_path() -> str:
    """Path to the FIRST existing wallet key across candidate roots (failover)."""
    for r in CANDIDATE_ROOTS:
        p = os.path.join(r, _CRED_REL, "polymarket_wallet.key")
        if os.path.isfile(p):
            return p
    return os.path.join(CANDIDATE_ROOTS[0], _CRED_REL, "polymarket_wallet.key")


def read_env_key(name: str) -> str | None:
    """Read a secret from the local .env (whichever host), then env var.
    The operator-edited .env is authoritative; env var is the fallback. Never
    logs or returns more than the single requested value."""
    p = credentials_env()
    if os.path.isfile(p):
        try:
            for line in open(p):
                if line.startswith(name + "="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
        except OSError:
            pass
    v = os.getenv(name)
    return v.strip() if v else None
