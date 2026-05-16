# AI Frameworks Isolation

System Python (`/usr/bin/python3` in the proot Debian) carries ONLY what the
Hive engine + Roundtable + branded pipeline actively need:

- `anthropic`        — Claude API SDK (Roundtable, dispatcher)
- `pyyaml`           — process templates + roster
- `pydantic` 2.13.x  — FastAPI / Onyx POS / HivemindSaaS backend models
- `requests`, `httpx`, `slack_sdk`, etc. — branded pipeline (Slack, Resend, Drive)

Optional AI frameworks with **incompatible pinned deps** live in their own
venvs under `/root/venvs/<framework>/` (proot fs — `+x` works there; sdcard
mount strips execute permission).

## When to spin up a framework venv

You DON'T need a venv for:
- One-off pip installs of compatible packages
- Anthropic SDK extensions
- Anything that imports cleanly into system python without `pip check` warnings

You DO need a venv for:
- **CrewAI** (pins `pydantic~=2.11.9`, `python-dotenv~=1.1.1` — conflicts with FastAPI stack)
- **LiteLLM** (pins `python-dotenv==1.0.1` — conflicts with newer dotenv users)
- **Langchain ecosystem** (heavy deps that often pin old versions)
- Anything that triggers >2 conflict warnings on `pip check`

## Pattern

```bash
# 1) Create the venv off-sdcard (where +x works)
mkdir -p /root/venvs
python3 -m venv /root/venvs/crewai
source /root/venvs/crewai/bin/activate

# 2) Install the framework + only what it needs
pip install crewai

# 3) Lock the deps for reproducibility
pip freeze > /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/ai_frameworks/crewai.lock.txt

# 4) Use it via a wrapper script that activates the venv first
cat > /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/ai_frameworks/run_crewai.sh <<'EOF'
#!/usr/bin/env bash
source /root/venvs/crewai/bin/activate
exec python3 "$@"
EOF
chmod +x /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/ai_frameworks/run_crewai.sh
```

## Why off-sdcard

The `/mnt/sdcard/` FAT mount strips execute permission from every file.
That breaks `venv/bin/python3`, `venv/bin/pip`, and shebangs in any script
inside the venv. Putting the venv under `/root/venvs/` (proot Debian fs)
keeps `+x` working. Lock files + wrapper scripts can live on sdcard
(read-only, gets synced via Tailscale to PC + e5-mother).

## Currently provisioned

| Framework | Venv path | Status | Lock file |
|---|---|---|---|
| _(none yet -- add when first real need surfaces)_ |  |  |  |

## History

- 2026-05-16: Removed unused `crewai` (1.13.0 → upgraded to 1.14.4 attempting
  to resolve deps → still conflicted with litellm on `python-dotenv` → both
  uninstalled). Neither was actually imported in any code. This README
  documents the pattern for when they DO get used.
