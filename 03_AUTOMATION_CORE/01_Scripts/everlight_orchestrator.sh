#!/bin/bash
# everlight_orchestrator.sh - Hive Mind War Room (4 panes)
# Optimized for Z Fold: 4 quadrant panes, keyboard-friendly.
#
# Usage:
#   ws                         # Opens empty 4-pane war room
#   ws "analyze my bot"        # Opens + broadcasts prompt to all 4
#   ws --tunnel                # Opens war room + starts ngrok tunnel to dashboard
#   ws --tunnel "my prompt"    # Both

SESSION_NAME="everlight_hive"
TUNNEL=false
TUNNEL_SCRIPT="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ngrok_tunnel.sh"

# Parse flags
POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tunnel)
            TUNNEL=true
            shift
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done
set -- "${POSITIONAL[@]}"

PROMPT="${1:-}"

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? == 0 ]; then
    if [ -n "$PROMPT" ]; then
        # Broadcast prompt to all existing panes
        for pane in 0 1 2 3; do
            tmux send-keys -t $SESSION_NAME:0.$pane "$PROMPT" C-m
        done
    fi
    echo "Attaching to existing Hive Mind session..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

echo "Starting Hive Mind War Room (4 managers)..."

# Pane 0: Claude (Chief Operator)
tmux new-session -d -s $SESSION_NAME -n "War_Room"

# Disable mouse so Android keyboard pops up on tap
# Ctrl-b m toggles mouse on/off
tmux set-option -t $SESSION_NAME -g mouse off
tmux bind-key -T prefix m set-option -g mouse \; display-message "Mouse: #{?mouse,ON,OFF}"

tmux send-keys -t $SESSION_NAME:0 "clear && echo '=== CLAUDE (Chief Operator / Strategist) ==='" C-m

# Pane 1: Gemini (Logistics Commander) - split right
tmux split-window -h -t $SESSION_NAME:0
tmux send-keys -t $SESSION_NAME:0.1 "clear && echo '=== GEMINI (Logistics Commander) ==='" C-m

# Pane 2: Codex (Engineering Foreman) - split bottom-left
tmux split-window -v -t $SESSION_NAME:0.0
tmux send-keys -t $SESSION_NAME:0.2 "clear && echo '=== CODEX (Engineering Foreman) ==='" C-m

# Pane 3: Perplexity (Intelligence) - split bottom-right
tmux split-window -v -t $SESSION_NAME:0.1
tmux send-keys -t $SESSION_NAME:0.3 "clear && echo '=== PERPLEXITY (Intelligence Anchor) ==='" C-m

# Tiled layout for even quadrants (works great on Z Fold)
tmux select-layout -t $SESSION_NAME:0 tiled

# If prompt provided, launch each manager interactively
if [ -n "$PROMPT" ]; then
    sleep 1
    # Claude
    tmux send-keys -t $SESSION_NAME:0.0 "cl" C-m
    sleep 0.5
    tmux send-keys -t $SESSION_NAME:0.0 "$PROMPT" C-m
    # Gemini
    tmux send-keys -t $SESSION_NAME:0.1 "gm" C-m
    sleep 0.5
    tmux send-keys -t $SESSION_NAME:0.1 "$PROMPT" C-m
    # Codex
    tmux send-keys -t $SESSION_NAME:0.2 "cx \"$PROMPT\"" C-m
    # Perplexity
    tmux send-keys -t $SESSION_NAME:0.3 "ppx \"$PROMPT\"" C-m
fi

# Start ngrok tunnel if --tunnel flag was passed
if [ "$TUNNEL" = true ]; then
    if [ -f "$TUNNEL_SCRIPT" ]; then
        echo "Starting ngrok tunnel to dashboard (port 8502)..."
        bash "$TUNNEL_SCRIPT" --background --basic-auth "admin:everlight2026"
    else
        echo "WARNING: Tunnel script not found at $TUNNEL_SCRIPT"
    fi
fi

# Focus on Claude pane (primary interaction)
tmux select-pane -t $SESSION_NAME:0.0

sleep 1
echo "Hive Mind War Room ready. Attaching..."
tmux attach-session -t $SESSION_NAME
