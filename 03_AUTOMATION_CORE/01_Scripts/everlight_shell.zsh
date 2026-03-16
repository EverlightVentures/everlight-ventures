# ============================================================
# EVERLIGHT SHELL EXTRAS
# Sourced by /root/.zshrc -- single source of truth for banner,
# PATH fixes, and any aliases that need to stay in sync.
# ============================================================

# --- PATH: ensure ~/bin is available (matches bash) ---
export PATH="$HOME/bin:$PATH"

# --- Wake lock: keep Termux alive (matches bash) ---
termux-wake-lock 2>/dev/null

# --- Django Dashboard alias ---
alias ddr='bash /mnt/sdcard/AA_MY_DRIVE/xlm_bot/dashboard_django/ddr'

# --- Startup Banner ---
if [[ -o interactive ]]; then
    # Check which services are running
    local _bot_status="\033[0;31moff\033[0m"
    local _dash_status="\033[0;31moff\033[0m"
    local _django_status="\033[0;31moff\033[0m"
    local _ws_status="\033[0;31moff\033[0m"
    local _hive_status="\033[0;31moff\033[0m"
    local _code_status="\033[0;31moff\033[0m"

    pgrep -f "xpb-fg|main.py.*xlm_bot" &>/dev/null && _bot_status="\033[0;32mlive\033[0m"
    pgrep -f "streamlit.*dashboard" &>/dev/null && _dash_status="\033[0;32m:8502\033[0m"
    pgrep -f "manage.py runserver.*8503" &>/dev/null && _django_status="\033[0;32m:8503\033[0m"
    pgrep -f "xws-fg\|live_ws.py" &>/dev/null && _ws_status="\033[0;32mlive\033[0m"
    pgrep -f "manage.py runserver.*8504" &>/dev/null && _hive_status="\033[0;32m:8504\033[0m"
    pgrep -f "code-server" &>/dev/null && _code_status="\033[0;32m:8080\033[0m"

    echo ""
    echo "\033[1;36m  EVERLIGHT VENTURES\033[0m \033[0;90m|\033[0m \033[0;33m$(date '+%b %d, %Y %H:%M')\033[0m"
    echo "\033[0;90m  -------------------------------------------------------\033[0m"
    echo ""
    echo "\033[0;90m  +-- AI WORKERS ------------------------------------+\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mai\033[0m \033[0;90mGPT    \033[1;37mcx\033[0m \033[0;90mCodex    \033[1;37mppx\033[0m \033[0;90mPerplexity    \033[1;37mask\033[0m \033[0;90mAuto-route\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mgm\033[0m \033[0;90mGemini  \033[1;37mcl\033[0m \033[0;90mClaude   \033[1;37mhive\033[0m \033[0;90mHive Mind\033[0m"
    echo "\033[0;90m  |\033[0m"
    echo "\033[0;90m  +-- XLM BOT --------------------------------------+\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mxon\033[0m \033[0;90mStart all    \033[1;37mxpb\033[0m \033[0;90mBot [$_bot_status\033[0;90m]    \033[1;37mxws\033[0m \033[0;90mWS feed [$_ws_status\033[0;90m]\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mxdr\033[0m \033[0;90mStreamlit [$_dash_status\033[0;90m]  \033[1;37mddr\033[0m \033[0;90mDjango  [$_django_status\033[0;90m]\033[0m"
    echo "\033[0;90m  |\033[0m"
    echo "\033[0;90m  +-- DASHBOARDS -----------------------------------+\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mhdx\033[0m \033[0;90mHive Mind [$_hive_status\033[0;90m]   \033[1;37madr\033[0m \033[0;90mAA Master     \033[1;37mmdl\033[0m \033[0;90mMaster Launch\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mcode-start\033[0m \033[0;90mCode Server [$_code_status\033[0;90m]\033[0m"
    echo "\033[0;90m  |\033[0m"
    echo "\033[0;90m  +-- NAVIGATION -----------------------------------+\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mev\033[0m \033[0;90mEverlight  \033[1;37mllp\033[0m \033[0;90mLast Light  \033[1;37mcontent\033[0m \033[0;90mContent Factory\033[0m"
    echo "\033[0;90m  |\033[0m  \033[1;37mdev\033[0m \033[0;90mDevelopment  \033[1;37mmedia\033[0m \033[0;90mMedia  \033[1;37mauto\033[0m \033[0;90mAutomation  \033[1;37mdrive\033[0m \033[0;90mRoot\033[0m"
    echo "\033[0;90m  |\033[0m"
    echo "\033[0;90m  +-- TOOLS ----------------------------------------+\033[0m"
    echo "\033[0;90m     \033[1;37mide\033[0m \033[0;90mtmux   \033[1;37mv\033[0m \033[0;90mnvim   \033[1;37mspace\033[0m \033[0;90mdisk usage   \033[1;37mws\033[0m \033[0;90morchestrator\033[0m"
    echo ""
fi
