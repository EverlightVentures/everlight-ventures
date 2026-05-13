#!/bin/bash
# Hive Sync v2 -- the upgrade over the 14-line cp from hive_sync.sh
# Brings Gemini and Codex to parity with Claude across:
#   - canonical doctrine (LUCREX + Hive)
#   - workspace agents (96 files)
#   - global agents (1 file: 37_contract_attorney)
#   - workspace skills (15 dirs)
#   - plugin skills (40+ dirs from /root/.claude/plugins/marketplaces)
#   - workspace commands (3 ev-*)
# Then runs parity check and exits with verdict.

set -euo pipefail

ROOT="/mnt/sdcard/AA_MY_DRIVE"
SCRIPTS="${ROOT}/03_AUTOMATION_CORE/01_Scripts"
GLOBAL_CLAUDE="/root/.claude"
GLOBAL_PLUGINS="/root/.claude/plugins/marketplaces/claude-plugins-official/plugins"

cd "$ROOT"

log()  { echo "[hive-sync] $*"; }
warn() { echo "[hive-sync][WARN] $*" >&2; }

# -- 1. Doctrine compile (canonical -> per-CLI memory files) ---------------------
log "compiling doctrine (CLAUDE.md -> GEMINI.md + AGENTS.md)..."
python3 "${SCRIPTS}/ai_workers/hive_doctrine_compiler.py"

# -- 2. Workspace agents (.claude/agents -> .gemini + .codex) --------------------
# Codex eats agent files as-is. Gemini's loader REQUIRES YAML frontmatter
# (---\nname: <slug>\n---). Most Claude workspace agents only have an HTML
# comment header, so we wrap them on the fly when mirroring to Gemini.
# This was caught by the 2026-05-13 end-to-end audit -- Gemini rejected 95/119.
log "mirroring workspace agents (Codex direct, Gemini frontmatter-wrapped)..."
mkdir -p .gemini/agents .codex/agents
rsync -a --delete .claude/agents/ .codex/agents/
python3 - <<'PYEOF'
import re, shutil
from pathlib import Path

src = Path(".claude/agents")
dst = Path(".gemini/agents")

# Clear stale mirrors so deletes propagate (rsync --delete equivalent).
for f in dst.glob("*.md"):
    if not (src / f.name).exists():
        f.unlink()

def normalize_tools_field(text: str) -> str:
    """Strip the `tools:` line entirely from Gemini-bound frontmatter.
    Claude tool names (Read, Glob, Bash, WebSearch...) are Claude-namespaced;
    Gemini rejects them with 'Invalid tool name'. Without the tools key
    Gemini falls back to its default tool set, which is what we want -- the
    agent file's value is the system-prompt firmware, not the tool grant."""
    if not text.startswith("---\n"):
        return text
    fm_end = text.find("\n---\n", 4)
    if fm_end == -1:
        return text
    fm = text[4:fm_end]
    rest = text[fm_end + 5:]
    new_fm_lines = [
        line for line in fm.splitlines()
        if not re.match(r"^\s*tools:\s*", line)
    ]
    return "---\n" + "\n".join(new_fm_lines) + "\n---\n" + rest

def wrap(body: str, slug: str) -> str:
    # Already has frontmatter? Just normalize tools field.
    if body.startswith("---\n"):
        return normalize_tools_field(body)
    # Pull a description from the first H1 / first non-comment line.
    desc = ""
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("<!--") or line.startswith("-->"):
            continue
        clean = re.sub(r"^#+\s*", "", line)
        desc = clean[:140]
        break
    desc = desc.replace('"', "'")
    return f'---\nname: {slug}\ndescription: "{desc}"\n---\n{body}'

for md in src.glob("*.md"):
    slug = md.stem.replace(" ", "-").lower()
    body = md.read_text(encoding="utf-8")
    out = wrap(body, slug)
    (dst / md.name).write_text(out, encoding="utf-8")
PYEOF

# -- 3. Global agents (/root/.claude/agents -> mirror into workspace agents dir) -
# Gemini and Codex don't have a "global agents" concept like Claude does, so we
# mirror the global ones INTO the workspace mirror so they're discoverable.
if [ -d "${GLOBAL_CLAUDE}/agents" ]; then
    log "mirroring global agents (Codex direct, Gemini frontmatter-wrapped)..."
    GLOBAL_DIR="${GLOBAL_CLAUDE}/agents" python3 - <<'PYEOF'
import os, re
from pathlib import Path

src = Path(os.environ["GLOBAL_DIR"])
gem = Path(".gemini/agents")
cdx = Path(".codex/agents")

def wrap(body: str, slug: str) -> str:
    if body.startswith("---\n"):
        return body
    desc = ""
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("<!--") or line.startswith("-->"):
            continue
        clean = re.sub(r"^#+\s*", "", line)
        desc = clean[:140]
        break
    desc = desc.replace('"', "'")
    return f'---\nname: {slug}\ndescription: "{desc}"\n---\n{body}'

for md in src.glob("*.md"):
    body = md.read_text(encoding="utf-8")
    (cdx / md.name).write_text(body, encoding="utf-8")
    (gem / md.name).write_text(wrap(body, md.stem.replace(" ", "-").lower()), encoding="utf-8")
PYEOF
fi

# -- 4. Workspace skills (.claude/skills -> .gemini + .codex) --------------------
log "mirroring workspace skills..."
mkdir -p .gemini/skills .codex/skills
rsync -a --delete .claude/skills/ .gemini/skills/
rsync -a --delete .claude/skills/ .codex/skills/

# -- 5. Plugin skills (from /root/.claude/plugins/marketplaces) ------------------
# These are the hookify:, plugin-dev:, frontend-design, claude-md-improver, etc.
# We flatten the plugin namespace (plugin-dev/skills/agent-development -> plugin-dev_agent-development)
# so Gemini and Codex see them as discrete skill folders without the colon.
if [ -d "${GLOBAL_PLUGINS}" ]; then
    log "mirroring plugin skills..."
    mkdir -p .gemini/skills/_plugin_skills .codex/skills/_plugin_skills
    for plugin_dir in "${GLOBAL_PLUGINS}"/*/; do
        plugin_name=$(basename "$plugin_dir")
        skills_dir="${plugin_dir}skills"
        [ -d "$skills_dir" ] || continue
        for skill_dir in "$skills_dir"/*/; do
            [ -d "$skill_dir" ] || continue
            skill_name=$(basename "$skill_dir")
            target_name="${plugin_name}_${skill_name}"
            cp -r "$skill_dir" ".gemini/skills/_plugin_skills/${target_name}"
            cp -r "$skill_dir" ".codex/skills/_plugin_skills/${target_name}"
        done
    done
fi

# -- 6. Commands (.claude/commands -> .gemini/commands as .toml shims) -----------
# Gemini commands use TOML. We generate a minimal TOML wrapper that just embeds
# the Claude command body as the prompt. Codex doesn't natively support slash
# commands the same way, but we drop them into .codex/commands/ for future use.
if [ -d ".claude/commands" ]; then
    log "translating workspace commands..."
    mkdir -p .gemini/commands .codex/commands
    python3 - <<'PYEOF'
import re
from pathlib import Path

src = Path(".claude/commands")
gem = Path(".gemini/commands")
cdx = Path(".codex/commands")

for md in src.glob("*.md"):
    body = md.read_text(encoding="utf-8")
    # Pull description from frontmatter if present, else from first heading
    desc_match = re.search(r"^description:\s*(.+)$", body, re.MULTILINE)
    if desc_match:
        desc = desc_match.group(1).strip().strip("\"'")
    else:
        head_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        desc = head_match.group(1).strip() if head_match else md.stem
    # Strip frontmatter from body
    if body.startswith("---"):
        body = re.sub(r"^---\n.*?\n---\n", "", body, count=1, flags=re.DOTALL)
    safe_body = body.replace("'''", "''\\'''")
    toml_out = f"description = {desc!r}\nprompt = '''\n{safe_body}\n'''\n"
    (gem / f"{md.stem}.toml").write_text(toml_out, encoding="utf-8")
    # Codex: just drop the md as-is; codex can read it via @-mention
    (cdx / md.name).write_text(body, encoding="utf-8")
PYEOF
fi

# -- 7. Parity check ------------------------------------------------------------
log "running parity check..."
set +e
python3 "${SCRIPTS}/ai_workers/hive_parity_check.py"
PARITY_RC=$?
set -e

if [ $PARITY_RC -eq 0 ]; then
    log "DONE -- full parity across Claude / Gemini / Codex."
else
    warn "parity check returned $PARITY_RC -- see _logs/hive_parity_report.md"
fi

exit $PARITY_RC
