#!/usr/bin/env bash
# =============================================================================
# Everlight Hive Mind -- Local AI War Room Installer
# Version: 1.0.0
# Runs in Termux on Android or directly on Linux (Debian/Ubuntu).
# Sets up: proot-distro Ubuntu, Python 3, Node.js, Claude Code CLI,
#           Hive Dashboard (Django), subscription gating, start/stop scripts.
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RELEASE_URL="RELEASE_URL_PLACEHOLDER"  # replaced at build time with real URL
SUPABASE_URL="https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
HIVEMIND_HOME="$HOME/.hivemind"
HIVEMIND_BIN="$HIVEMIND_HOME/bin"
HIVEMIND_WORKSPACE="$HOME/HiveMind"
DASHBOARD_PORT=8504
CONFIG_FILE="$HIVEMIND_HOME/config.json"
USAGE_FILE="$HIVEMIND_HOME/usage.json"
INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Colors / helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

# ---------------------------------------------------------------------------
# Step 0: Detect environment
# ---------------------------------------------------------------------------
detect_environment() {
    if [ -n "${TERMUX_VERSION:-}" ]; then
        ENV_TYPE="termux"
        info "Detected Termux v${TERMUX_VERSION}"
    elif [ -f /etc/os-release ] && grep -qi "ubuntu\|debian" /etc/os-release; then
        ENV_TYPE="linux"
        info "Detected native Linux (Debian/Ubuntu)"
    else
        echo ""
        echo "============================================================"
        echo "  Hive Mind requires one of:"
        echo "    1. Termux on Android (recommended)"
        echo "    2. Debian or Ubuntu Linux"
        echo ""
        echo "  To install Termux:"
        echo "    - Download from F-Droid: https://f-droid.org/packages/com.termux/"
        echo "    - Do NOT use the Play Store version (it is outdated)."
        echo "    - Open Termux, then run:"
        echo "        curl -sL <installer-url> | bash"
        echo "============================================================"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Step 1: Termux -- install proot-distro + Ubuntu
# ---------------------------------------------------------------------------
setup_termux_ubuntu() {
    if [ "$ENV_TYPE" != "termux" ]; then
        return 0
    fi

    info "Updating Termux packages..."
    pkg update -y && pkg upgrade -y

    info "Installing proot-distro and dependencies..."
    pkg install -y proot-distro wget curl git openssh

    if proot-distro list --installed 2>/dev/null | grep -q "ubuntu"; then
        ok "Ubuntu already installed in proot-distro"
    else
        info "Installing Ubuntu via proot-distro (this may take a few minutes)..."
        proot-distro install ubuntu
        ok "Ubuntu installed"
    fi

    # Write a bootstrap script that runs INSIDE Ubuntu
    BOOTSTRAP="/data/data/com.termux/files/home/.hivemind_bootstrap.sh"
    cat > "$BOOTSTRAP" << 'INNER_EOF'
#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "[INFO] Updating Ubuntu packages..."
apt-get update -qq && apt-get upgrade -y -qq

echo "[INFO] Installing core dependencies..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nodejs npm \
    git curl wget jq cron

echo "[INFO] Upgrading pip..."
python3 -m pip install --upgrade pip --break-system-packages 2>/dev/null || \
    python3 -m pip install --upgrade pip

echo "[INFO] Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

echo "[OK] Ubuntu environment ready."
INNER_EOF
    chmod +x "$BOOTSTRAP"

    info "Bootstrapping Ubuntu environment (installing Python, Node, Claude Code)..."
    proot-distro login ubuntu -- bash "$BOOTSTRAP"
    ok "Ubuntu bootstrap complete"

    # From here on, we continue the rest of the installer inside proot Ubuntu.
    # Copy installer files into the Ubuntu filesystem and run the rest there.
    UBUNTU_ROOT="/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu"
    UBUNTU_INSTALLER_DIR="${UBUNTU_ROOT}/root/.hivemind_installer"
    mkdir -p "$UBUNTU_INSTALLER_DIR"
    cp "$INSTALLER_DIR/install_hivemind.sh" "$UBUNTU_INSTALLER_DIR/" 2>/dev/null || true
    cp "$INSTALLER_DIR/subscription_gate.py" "$UBUNTU_INSTALLER_DIR/" 2>/dev/null || true
    cp "$INSTALLER_DIR/query_limiter.py" "$UBUNTU_INSTALLER_DIR/" 2>/dev/null || true
    cp "$INSTALLER_DIR/hive_wrapper.sh" "$UBUNTU_INSTALLER_DIR/" 2>/dev/null || true

    info "Continuing setup inside Ubuntu..."
    proot-distro login ubuntu -- bash -c "cd /root && ENV_TYPE=linux bash /root/.hivemind_installer/install_hivemind.sh --inner"
    exit 0
}

# ---------------------------------------------------------------------------
# Step 2: Native Linux -- install system packages
# ---------------------------------------------------------------------------
setup_linux_packages() {
    if [ "$ENV_TYPE" != "linux" ]; then
        return 0
    fi

    info "Installing system packages..."
    if command -v apt-get &>/dev/null; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq \
            python3 python3-pip python3-venv \
            git curl wget jq cron 2>/dev/null || true

        # Node.js -- use NodeSource if not present
        if ! command -v node &>/dev/null; then
            info "Installing Node.js 20.x..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
            apt-get install -y -qq nodejs
        fi
    else
        warn "apt-get not found. Please install manually: python3 python3-pip python3-venv nodejs npm git curl wget jq cron"
    fi

    # Claude Code CLI
    if ! command -v claude &>/dev/null; then
        info "Installing Claude Code CLI..."
        npm install -g @anthropic-ai/claude-code
    else
        ok "Claude Code CLI already installed"
    fi
}

# ---------------------------------------------------------------------------
# Step 3: Create workspace structure
# ---------------------------------------------------------------------------
create_workspace() {
    info "Creating Hive Mind workspace at $HIVEMIND_WORKSPACE ..."
    mkdir -p "$HIVEMIND_WORKSPACE"/{sessions,templates,outputs,logs,scripts,integrations,config}
    mkdir -p "$HIVEMIND_HOME"/{bin,cache,logs}

    # Default config
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << CONF_EOF
{
    "email": "",
    "plan": "trial",
    "subscription_status": "pending",
    "supabase_url": "${SUPABASE_URL}",
    "supabase_anon_key": "${SUPABASE_ANON_KEY}",
    "dashboard_port": ${DASHBOARD_PORT},
    "workspace": "${HIVEMIND_WORKSPACE}",
    "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "1.0.0"
}
CONF_EOF
    fi

    # Default usage tracker
    if [ ! -f "$USAGE_FILE" ]; then
        cat > "$USAGE_FILE" << USAGE_EOF
{
    "date": "$(date -u +%Y-%m-%d)",
    "queries": 0
}
USAGE_EOF
    fi

    ok "Workspace created"
}

# ---------------------------------------------------------------------------
# Step 4: Download hive dashboard + scripts
# ---------------------------------------------------------------------------
download_hive() {
    info "Downloading Hive Mind dashboard..."
    DASHBOARD_DIR="$HIVEMIND_WORKSPACE/dashboard"

    if [ "$RELEASE_URL" = "RELEASE_URL_PLACEHOLDER" ]; then
        warn "No release URL set -- creating skeleton dashboard instead."
        mkdir -p "$DASHBOARD_DIR"

        # Create a minimal Django project structure
        mkdir -p "$DASHBOARD_DIR"/{hive,templates,static,scripts}

        cat > "$DASHBOARD_DIR/requirements.txt" << 'REQ_EOF'
django>=4.2,<5.0
gunicorn>=21.2
requests>=2.31
python-dotenv>=1.0
REQ_EOF

        cat > "$DASHBOARD_DIR/manage.py" << 'MANAGE_EOF'
#!/usr/bin/env python3
"""Django management entry point for Hive Mind Dashboard."""
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hive.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and "
            "available on your PYTHONPATH, or activate the virtual environment."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
MANAGE_EOF
        chmod +x "$DASHBOARD_DIR/manage.py"
    else
        if command -v git &>/dev/null; then
            git clone "$RELEASE_URL" "$DASHBOARD_DIR" 2>/dev/null || \
                (curl -sL "$RELEASE_URL" -o /tmp/hivemind.tar.gz && \
                 mkdir -p "$DASHBOARD_DIR" && \
                 tar xzf /tmp/hivemind.tar.gz -C "$DASHBOARD_DIR" --strip-components=1 && \
                 rm /tmp/hivemind.tar.gz)
        else
            curl -sL "$RELEASE_URL" -o /tmp/hivemind.tar.gz
            mkdir -p "$DASHBOARD_DIR"
            tar xzf /tmp/hivemind.tar.gz -C "$DASHBOARD_DIR" --strip-components=1
            rm /tmp/hivemind.tar.gz
        fi
    fi

    # Set up Python venv for dashboard
    info "Setting up Python virtual environment..."
    python3 -m venv "$HIVEMIND_WORKSPACE/.venv"
    "$HIVEMIND_WORKSPACE/.venv/bin/pip" install --upgrade pip -q
    if [ -f "$DASHBOARD_DIR/requirements.txt" ]; then
        "$HIVEMIND_WORKSPACE/.venv/bin/pip" install -r "$DASHBOARD_DIR/requirements.txt" -q
    fi

    ok "Dashboard ready"
}

# ---------------------------------------------------------------------------
# Step 5: Install gating scripts
# ---------------------------------------------------------------------------
install_gate_scripts() {
    info "Installing subscription gate and query limiter..."

    # Copy Python gate scripts
    for script in subscription_gate.py query_limiter.py; do
        SRC="$INSTALLER_DIR/$script"
        if [ ! -f "$SRC" ]; then
            SRC="/root/.hivemind_installer/$script"
        fi
        if [ -f "$SRC" ]; then
            cp "$SRC" "$HIVEMIND_BIN/$script"
            chmod +x "$HIVEMIND_BIN/$script"
        else
            warn "Could not find $script -- you may need to copy it manually to $HIVEMIND_BIN/"
        fi
    done

    # Copy hive wrapper
    WRAPPER_SRC="$INSTALLER_DIR/hive_wrapper.sh"
    if [ ! -f "$WRAPPER_SRC" ]; then
        WRAPPER_SRC="/root/.hivemind_installer/hive_wrapper.sh"
    fi
    if [ -f "$WRAPPER_SRC" ]; then
        cp "$WRAPPER_SRC" "$HIVEMIND_BIN/hive"
        chmod +x "$HIVEMIND_BIN/hive"
    fi

    ok "Gate scripts installed"
}

# ---------------------------------------------------------------------------
# Step 6: Create start/stop scripts
# ---------------------------------------------------------------------------
create_service_scripts() {
    info "Creating hive-start and hive-stop scripts..."

    # --- hive-start ---
    cat > "$HIVEMIND_BIN/hive-start" << 'START_EOF'
#!/usr/bin/env bash
set -euo pipefail

HIVEMIND_HOME="$HOME/.hivemind"
HIVEMIND_WORKSPACE="$HOME/HiveMind"
CONFIG="$HIVEMIND_HOME/config.json"
PIDFILE="$HIVEMIND_HOME/dashboard.pid"
LOGFILE="$HIVEMIND_HOME/logs/dashboard.log"
VENV="$HIVEMIND_WORKSPACE/.venv/bin"
PORT=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('dashboard_port', 8504))" 2>/dev/null || echo 8504)

# Check subscription first
if [ -f "$HIVEMIND_HOME/bin/subscription_gate.py" ]; then
    if ! "$VENV/python3" "$HIVEMIND_HOME/bin/subscription_gate.py"; then
        exit 1
    fi
fi

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Hive Dashboard is already running (PID $(cat "$PIDFILE"))"
    echo "Access it at: http://localhost:$PORT"
    exit 0
fi

mkdir -p "$HIVEMIND_HOME/logs"

echo "Starting Hive Mind Dashboard on port $PORT ..."
cd "$HIVEMIND_WORKSPACE/dashboard"
nohup "$VENV/python3" manage.py runserver "0.0.0.0:$PORT" > "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
sleep 2

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo ""
    echo "==========================================="
    echo "  Hive Mind Dashboard is running."
    echo "  Open: http://localhost:$PORT"
    echo "==========================================="
    echo ""
else
    echo "Failed to start dashboard. Check logs at $LOGFILE"
    exit 1
fi
START_EOF
    chmod +x "$HIVEMIND_BIN/hive-start"

    # --- hive-stop ---
    cat > "$HIVEMIND_BIN/hive-stop" << 'STOP_EOF'
#!/usr/bin/env bash
set -euo pipefail

HIVEMIND_HOME="$HOME/.hivemind"
PIDFILE="$HIVEMIND_HOME/dashboard.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm "$PIDFILE"
        echo "Hive Mind Dashboard stopped."
    else
        rm "$PIDFILE"
        echo "Dashboard was not running (stale PID file removed)."
    fi
else
    echo "No dashboard PID file found. Nothing to stop."
fi
STOP_EOF
    chmod +x "$HIVEMIND_BIN/hive-stop"

    ok "Service scripts created"
}

# ---------------------------------------------------------------------------
# Step 7: Prompt for email and verify subscription
# ---------------------------------------------------------------------------
collect_email_and_verify() {
    echo ""
    echo "============================================================"
    echo "  Hive Mind -- Subscription Activation"
    echo "============================================================"
    echo ""
    echo "Enter the email address you used when you purchased your"
    echo "Hive Mind subscription at everlightventures.io/hivemind."
    echo ""
    echo "If you don't have a subscription yet, enter your email"
    echo "to start a free trial (5 queries per day)."
    echo ""
    read -rp "Email: " USER_EMAIL

    if [ -z "$USER_EMAIL" ]; then
        fail "Email is required."
    fi

    # Write email to config
    python3 -c "
import json
config_path = '$CONFIG_FILE'
with open(config_path) as f:
    config = json.load(f)
config['email'] = '$USER_EMAIL'
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
"

    info "Checking subscription status for $USER_EMAIL ..."

    # Call Supabase to verify
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        "${SUPABASE_URL}/rest/v1/hivemind_subscriptions?email=eq.${USER_EMAIL}&select=subscription_status,plan,expires_at" \
        -H "apikey: ${SUPABASE_ANON_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
        -H "Content-Type: application/json" 2>/dev/null || echo -e "[]\n000")

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if len(d)>0 else 1)" 2>/dev/null; then
        STATUS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('subscription_status','unknown'))")
        PLAN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('plan','trial'))")

        python3 -c "
import json
config_path = '$CONFIG_FILE'
with open(config_path) as f:
    config = json.load(f)
config['subscription_status'] = '$STATUS'
config['plan'] = '$PLAN'
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
"

        if [ "$STATUS" = "active" ]; then
            ok "Subscription verified -- plan: $PLAN"
        else
            warn "Subscription status: $STATUS"
            warn "You can still use the trial (5 queries/day)."
            warn "Activate or renew at: https://everlightventures.io/hivemind"
        fi
    else
        warn "Could not reach subscription server (HTTP $HTTP_CODE)."
        warn "Starting in trial mode (5 queries/day)."
        warn "Your subscription will be verified on the next daily check."

        python3 -c "
import json
config_path = '$CONFIG_FILE'
with open(config_path) as f:
    config = json.load(f)
config['subscription_status'] = 'trial'
config['plan'] = 'trial'
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
"
    fi
}

# ---------------------------------------------------------------------------
# Step 8: Set up daily subscription check (cron)
# ---------------------------------------------------------------------------
setup_cron() {
    info "Setting up daily subscription check..."

    CRON_SCRIPT="$HIVEMIND_BIN/daily_sub_check.sh"
    cat > "$CRON_SCRIPT" << 'CRON_EOF'
#!/usr/bin/env bash
# Daily subscription status check for Hive Mind
HIVEMIND_HOME="$HOME/.hivemind"
VENV="$HOME/HiveMind/.venv/bin"

if [ -f "$HIVEMIND_HOME/bin/subscription_gate.py" ]; then
    "$VENV/python3" "$HIVEMIND_HOME/bin/subscription_gate.py" --update-config >/dev/null 2>&1
fi
CRON_EOF
    chmod +x "$CRON_SCRIPT"

    # Add cron entry (idempotent -- remove existing, then add)
    CRON_LINE="0 8 * * * $CRON_SCRIPT"
    (crontab -l 2>/dev/null | grep -v "daily_sub_check.sh" || true; echo "$CRON_LINE") | crontab - 2>/dev/null || \
        warn "Could not set up cron job. You can run '$CRON_SCRIPT' manually to check subscription status."

    ok "Daily subscription check configured (runs at 8:00 AM)"
}

# ---------------------------------------------------------------------------
# Step 9: Add bin directory to PATH
# ---------------------------------------------------------------------------
setup_path() {
    info "Adding Hive Mind to your PATH..."

    SHELL_RC="$HOME/.bashrc"
    if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-bash}")" = "zsh" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    PATH_LINE="export PATH=\"\$HOME/.hivemind/bin:\$PATH\""
    if ! grep -qF ".hivemind/bin" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Hive Mind CLI" >> "$SHELL_RC"
        echo "$PATH_LINE" >> "$SHELL_RC"
    fi

    export PATH="$HIVEMIND_BIN:$PATH"
    ok "PATH updated"
}

# ---------------------------------------------------------------------------
# Step 10: .env.example for the dashboard
# ---------------------------------------------------------------------------
create_env_example() {
    DASHBOARD_DIR="$HIVEMIND_WORKSPACE/dashboard"
    if [ -d "$DASHBOARD_DIR" ] && [ ! -f "$DASHBOARD_DIR/.env.example" ]; then
        cat > "$DASHBOARD_DIR/.env.example" << 'ENV_EOF'
# Hive Mind Dashboard -- Environment Variables
# Copy to .env and fill in your values.

# Django
DJANGO_SECRET_KEY=change-me-to-a-random-string
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase (subscription verification)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Stripe (if running your own billing)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AI API Keys (users provide their own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_AI_API_KEY=
PERPLEXITY_API_KEY=

# Slack (audit logging)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# Dashboard
DASHBOARD_PORT=8504
ENV_EOF
    fi
}

# ---------------------------------------------------------------------------
# Welcome message
# ---------------------------------------------------------------------------
print_welcome() {
    echo ""
    echo "============================================================"
    echo "  Hive Mind -- Installation Complete"
    echo "============================================================"
    echo ""
    echo "  Your AI war room is ready."
    echo ""
    echo "  Commands:"
    echo "    hive-start        Start the Hive Mind Dashboard"
    echo "    hive-stop         Stop the Dashboard"
    echo "    hive <prompt>     Send a query to the hive"
    echo ""
    echo "  Dashboard URL:      http://localhost:${DASHBOARD_PORT}"
    echo "  Workspace:          ${HIVEMIND_WORKSPACE}"
    echo "  Config:             ${CONFIG_FILE}"
    echo "  Logs:               ${HIVEMIND_HOME}/logs/"
    echo ""
    echo "  Next steps:"
    echo "    1. Run 'hive-start' to launch the dashboard"
    echo "    2. Open http://localhost:${DASHBOARD_PORT} in your browser"
    echo "    3. Set your AI API keys in the dashboard settings"
    echo "    4. Run 'hive \"summarize my last week\"' to test"
    echo ""
    echo "  Subscription:       $(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('plan','trial').upper())" 2>/dev/null || echo 'TRIAL')"
    echo "  Manage account:     https://everlightventures.io/hivemind"
    echo ""
    echo "  If you just opened a new shell, run:"
    echo "    source ~/.bashrc"
    echo "============================================================"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo "============================================================"
    echo "  Everlight Hive Mind -- Installer v1.0.0"
    echo "============================================================"
    echo ""

    # If called with --inner, skip Termux detection (we are already inside Ubuntu)
    if [ "${1:-}" = "--inner" ]; then
        ENV_TYPE="linux"
    else
        detect_environment

        # If Termux, set up Ubuntu and re-enter
        if [ "$ENV_TYPE" = "termux" ]; then
            setup_termux_ubuntu
            # setup_termux_ubuntu calls exit, so we never reach here
        fi
    fi

    setup_linux_packages
    create_workspace
    download_hive
    install_gate_scripts
    create_service_scripts
    collect_email_and_verify
    setup_cron
    setup_path
    create_env_example
    print_welcome
}

main "$@"
