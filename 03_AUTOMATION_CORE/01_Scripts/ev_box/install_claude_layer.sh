#!/usr/bin/env bash
# Claude Code optimization layer -- cherry-picks from affaan-m/everything-claude-code
# Adds: claude-cheap cost router, MCP templates, PreToolUse safety hook, helper scripts
# Does NOT clobber existing hive_mind setup (that's already more mature than the upstream).
set -euo pipefail

CLAUDE_DIR="/home/ubuntu/.claude"
WORKSPACE="/home/ubuntu/AA_MY_DRIVE"
HELPERS_DIR="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/claude_helpers"
mkdir -p "$CLAUDE_DIR/mcp-templates" "$HELPERS_DIR"

log() { printf '[claude-layer %s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ---------- 1. claude-cheap cost-router function ----------
log "Adding claude-cheap shell function..."
if ! grep -q 'claude-cheap()' /home/ubuntu/.zshrc 2>/dev/null; then
  cat >> /home/ubuntu/.zshrc <<'ROUTER'

# Cost-routing: forces Sonnet 4.6 + 8K thinking tokens for routine tasks
# Saves ~70% vs default Opus. Use cl/claude for non-routine.
claude-cheap() {
  CLAUDE_MODEL='claude-sonnet-4-6' \
    CLAUDE_THINKING_BUDGET='8000' \
    claude "$@"
}
alias clc='claude-cheap'
ROUTER
fi

# ---------- 2. PreToolUse safety hook ----------
log "Installing PreToolUse hook (blocks rm -rf on protected paths)..."
SETTINGS="$CLAUDE_DIR/settings.json"
if [[ ! -f "$SETTINGS" ]]; then
  echo '{}' > "$SETTINGS"
fi
# Merge in the hook (use python for safe JSON merge)
python3 <<'PY'
import json, os
path = "/home/ubuntu/.claude/settings.json"
with open(path) as f:
    cfg = json.load(f)
hooks = cfg.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])
# Idempotent: only add if not already there
if not any(h.get("hook_id") == "ev_box_protect_paths" for h in pre):
    pre.append({
        "hook_id": "ev_box_protect_paths",
        "matcher": {"tool_name": "Bash"},
        "command": "/opt/dfir-lite/protect_paths.sh"
    })
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PY

# Install the hook script itself
sudo tee /opt/dfir-lite/protect_paths.sh >/dev/null <<'PROTECT'
#!/usr/bin/env bash
# Block rm -rf on critical paths. Reads the proposed Bash command from stdin (JSON).
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
PROTECTED='/home/ubuntu/AA_MY_DRIVE|/home/ubuntu/.claude|/home/ubuntu/.ssh|/opt/dfir-lite|/var/log/dfir-lite'
if echo "$CMD" | grep -qE "rm\s+(-[rfRF]+\s+)+(${PROTECTED})"; then
  echo '{"decision": "block", "reason": "rm -rf on protected path blocked by ev-box safety hook"}'
  exit 0
fi
echo '{"decision": "approve"}'
PROTECT
sudo chmod +x /opt/dfir-lite/protect_paths.sh

# ---------- 3. MCP templates (reference only, no auto-wire) ----------
log "Pulling MCP server templates..."
TEMPLATES_REPO="https://raw.githubusercontent.com/affaan-m/everything-claude-code/main/mcp-configs"
for tpl in filesystem.json github.json memory.json puppeteer.json; do
  curl -fsSL "$TEMPLATES_REPO/$tpl" -o "$CLAUDE_DIR/mcp-templates/$tpl" 2>/dev/null || \
    log "  (template $tpl not pulled -- repo may have moved)"
done

# ---------- 4. Helper scripts ----------
log "Writing claude_helpers utilities..."

cat > "$HELPERS_DIR/inventory_agents.sh" <<'INV'
#!/usr/bin/env bash
# List all agents with one-line descriptions
DIR="${1:-$HOME/.claude/agents}"
echo "Agent inventory in $DIR:"
for f in "$DIR"/*.md; do
  name=$(basename "$f" .md)
  desc=$(grep -m1 '^description:' "$f" | sed 's/description: //; s/"//g' | head -c 80)
  printf '  %-30s %s\n' "$name" "$desc"
done
INV

cat > "$HELPERS_DIR/audit_skills.sh" <<'SKILL'
#!/usr/bin/env bash
# List all skills + check for orphaned ones (skill file with no SKILL.md)
DIR="${1:-$HOME/.claude/skills}"
echo "Skills in $DIR:"
for d in "$DIR"/*/; do
  name=$(basename "$d")
  if [[ -f "$d/SKILL.md" ]]; then
    desc=$(grep -m1 '^description:' "$d/SKILL.md" | sed 's/description: //; s/"//g' | head -c 80)
    printf '  [OK]  %-25s %s\n' "$name" "$desc"
  else
    printf '  [!!]  %-25s NO SKILL.md\n' "$name"
  fi
done
SKILL

cat > "$HELPERS_DIR/claude_cost_today.sh" <<'COST'
#!/usr/bin/env bash
# Approximate token spend for today across .claude/projects/*/
TOTAL=0
for p in "$HOME/.claude/projects/"*/; do
  TODAY=$(find "$p" -name '*.jsonl' -newermt 'today 00:00' 2>/dev/null)
  for f in $TODAY; do
    SIZE=$(wc -c < "$f")
    TOTAL=$((TOTAL + SIZE))
  done
done
KB=$((TOTAL / 1024))
echo "Today's transcript size: ${KB} KB (rough proxy for token spend)"
COST

chmod +x "$HELPERS_DIR"/*.sh

log "Claude Code layer install complete."
log "  Try: claude-cheap 'list files in /home/ubuntu' (cheap Sonnet route)"
log "  Try: bash $HELPERS_DIR/inventory_agents.sh"
