#!/usr/bin/env bash
# =============================================================================
# Hive Mind -- Command Wrapper
# This is the main 'hive' command that users run.
# Checks subscription status and query limits before executing.
# =============================================================================
set -euo pipefail

HIVEMIND_HOME="$HOME/.hivemind"
HIVEMIND_WORKSPACE="$HOME/HiveMind"
VENV_PYTHON="$HIVEMIND_WORKSPACE/.venv/bin/python3"
GATE_SCRIPT="$HIVEMIND_HOME/bin/subscription_gate.py"
LIMITER_SCRIPT="$HIVEMIND_HOME/bin/query_limiter.py"

# ---------------------------------------------------------------------------
# Preflight: check that installation exists
# ---------------------------------------------------------------------------
if [ ! -d "$HIVEMIND_HOME" ]; then
    echo "Hive Mind is not installed."
    echo "Run the installer first: bash install_hivemind.sh"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Python virtual environment not found at $HIVEMIND_WORKSPACE/.venv"
    echo "Re-run the installer to fix this."
    exit 1
fi

# ---------------------------------------------------------------------------
# Gate 1: Subscription check
# ---------------------------------------------------------------------------
if [ -f "$GATE_SCRIPT" ]; then
    if ! "$VENV_PYTHON" "$GATE_SCRIPT" 2>/dev/null; then
        echo ""
        echo "Your Hive Mind subscription has expired."
        echo "Reactivate at: https://everlightventures.io/hivemind"
        echo ""
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Gate 2: Query limit check (with increment)
# ---------------------------------------------------------------------------
if [ -f "$LIMITER_SCRIPT" ]; then
    if ! "$VENV_PYTHON" "$LIMITER_SCRIPT" --increment 2>/dev/null; then
        echo ""
        echo "Daily query limit reached."
        echo "Upgrade your plan at: https://everlightventures.io/hivemind"
        echo ""
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Handle subcommands
# ---------------------------------------------------------------------------
SUBCMD="${1:-}"

case "$SUBCMD" in
    start)
        exec "$HIVEMIND_HOME/bin/hive-start"
        ;;
    stop)
        exec "$HIVEMIND_HOME/bin/hive-stop"
        ;;
    status)
        echo "--- Subscription ---"
        "$VENV_PYTHON" "$GATE_SCRIPT" 2>/dev/null || true
        echo ""
        echo "--- Usage ---"
        "$VENV_PYTHON" "$LIMITER_SCRIPT" --status 2>/dev/null || true
        echo ""

        PIDFILE="$HIVEMIND_HOME/dashboard.pid"
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            PORT=$(python3 -c "import json; print(json.load(open('$HIVEMIND_HOME/config.json')).get('dashboard_port', 8504))" 2>/dev/null || echo 8504)
            echo "--- Dashboard ---"
            echo "Running (PID $(cat "$PIDFILE"))"
            echo "URL: http://localhost:$PORT"
        else
            echo "--- Dashboard ---"
            echo "Not running. Use 'hive start' to launch."
        fi
        exit 0
        ;;
    help|--help|-h)
        echo "Hive Mind -- AI War Room"
        echo ""
        echo "Usage:"
        echo "  hive <query>      Send a query to the AI hive"
        echo "  hive start        Start the dashboard"
        echo "  hive stop         Stop the dashboard"
        echo "  hive status       Show subscription, usage, and dashboard status"
        echo "  hive help         Show this message"
        echo ""
        echo "Examples:"
        echo "  hive \"draft a marketing plan for Q2\""
        echo "  hive \"analyze my sales data from last month\""
        echo "  hive \"write a blog post about remote work\""
        echo ""
        echo "Dashboard:   http://localhost:8504"
        echo "Account:     https://everlightventures.io/hivemind"
        exit 0
        ;;
    "")
        echo "Usage: hive <query>"
        echo "       hive start | stop | status | help"
        echo ""
        echo "Run 'hive help' for details."
        exit 0
        ;;
esac

# ---------------------------------------------------------------------------
# Execute: pass the query to Claude Code CLI
# ---------------------------------------------------------------------------
QUERY="$*"

echo "Dispatching to Hive Mind..."
echo ""

# Use Claude Code CLI as the execution engine
if command -v claude &>/dev/null; then
    cd "$HIVEMIND_WORKSPACE"
    exec claude "$QUERY"
else
    echo "Claude Code CLI not found."
    echo "Install it with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
