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

if [[ -n "${EV_SHELL_INIT_DONE:-}" ]]; then
    return 0
fi
export EV_SHELL_INIT_DONE=1

# Truecolor palette -- matches /root/.config/starship.toml so prompt and banner
# share the same brand identity. Updated 2026-04-30.
typeset -gr _EV_RESET=$'\033[0m'
typeset -gr _EV_BOLD=$'\033[1m'
typeset -gr _EV_DIM=$'\033[2m'
typeset -gr _EV_ITALIC=$'\033[3m'

# Foreground colors (truecolor, not 256)
typeset -gr _EV_GOLD=$'\033[38;2;212;168;67m'         # #D4A843 brand gold
typeset -gr _EV_GOLD_HOT=$'\033[38;2;255;205;60m'     # #FFCD3C bright gold
typeset -gr _EV_NAVY=$'\033[38;2;26;45;92m'           # #1A2D5C path-zone navy
typeset -gr _EV_NAVY_DEEP=$'\033[38;2;15;27;61m'      # #0F1B3D deep navy
typeset -gr _EV_NAVY_PALE=$'\033[38;2;45;63;112m'     # #2D3F70 lighter navy
typeset -gr _EV_TURQUOISE=$'\033[38;2;0;229;255m'     # #00E5FF hot accent
typeset -gr _EV_TURQUOISE_PALE=$'\033[38;2;125;249;255m' # #7DF9FF pale pop
typeset -gr _EV_SILVER=$'\033[38;2;199;201;209m'      # #C7C9D1 silver
typeset -gr _EV_SILVER_DIM=$'\033[38;2;122;126;140m'  # #7A7E8C dim grey
typeset -gr _EV_DARK=$'\033[38;2;10;10;10m'           # #0A0A0A canvas black
typeset -gr _EV_GREEN=$'\033[38;2;0;255;157m'         # #00FF9D live indicator
typeset -gr _EV_RED=$'\033[38;2;255;0;60m'            # #FF003C error
typeset -gr _EV_AMBER=$'\033[38;2;255;179;0m'         # #FFB300 warning

# Background colors
typeset -gr _EV_BG_NAVY=$'\033[48;2;26;45;92m'        # navy panel bg
typeset -gr _EV_BG_NAVY_DEEP=$'\033[48;2;15;27;61m'   # deeper panel bg
typeset -gr _EV_BG_GOLD=$'\033[48;2;212;168;67m'      # gold badge bg
typeset -gr _EV_BG_TURQUOISE=$'\033[48;2;0;229;255m'  # turquoise hot bg
typeset -gr _EV_BG_RED=$'\033[48;2;255;0;60m'         # red alert bg

# Aliases for backward compatibility with existing function bodies
typeset -gr _EV_CYAN=$_EV_TURQUOISE
typeset -gr _EV_WHITE=$_EV_SILVER

_ev_prompt_init() {
    export COLORTERM="${COLORTERM:-truecolor}"

    # Starship owns the prompt now. If Starship's zsh init ran, bail out --
    # do not touch PROMPT/RPROMPT or load p10k. Starship sets STARSHIP_SHELL=zsh.
    # (Removed: legacy fallback branch had an unescaped backtick in PROMPT
    #  that loop-broke zsh under PROMPT_SUBST -- 2026-04-30.)
    if [[ -n "${STARSHIP_SHELL:-}" ]] || command -v starship >/dev/null 2>&1; then
        return 0
    fi

    typeset -g POWERLEVEL9K_SHORTEN_STRATEGY=none
    typeset -g POWERLEVEL9K_DIR_TRUNCATE_BEFORE_MARKER=false
    typeset -g POWERLEVEL9K_DIR_MAX_LENGTH=0
    typeset -g POWERLEVEL9K_DIR_MIN_COMMAND_COLUMNS=0
    typeset -g POWERLEVEL9K_DIR_PATH_HIGHLIGHT_FOREGROUND=39

    if (( ! $+functions[p10k] )) && [[ -t 1 && -r /root/powerlevel10k/powerlevel10k.zsh-theme ]]; then
        (( $+functions[p10k] )) || source /root/powerlevel10k/powerlevel10k.zsh-theme
    fi

    if (( $+functions[p10k] )); then
        typeset -g POWERLEVEL9K_MODE=compatible
        typeset -g POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(os_icon dir vcs newline prompt_char)
        typeset -g POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status command_execution_time background_jobs context time newline)
        typeset -g POWERLEVEL9K_PROMPT_ADD_NEWLINE=false
        typeset -g POWERLEVEL9K_BACKGROUND=
        typeset -g POWERLEVEL9K_LEFT_PROMPT_FIRST_SEGMENT_START_SYMBOL=
        typeset -g POWERLEVEL9K_LEFT_PROMPT_LAST_SEGMENT_END_SYMBOL=
        typeset -g POWERLEVEL9K_RIGHT_PROMPT_FIRST_SEGMENT_START_SYMBOL=
        typeset -g POWERLEVEL9K_RIGHT_PROMPT_LAST_SEGMENT_END_SYMBOL=
        typeset -g POWERLEVEL9K_LEFT_SUBSEGMENT_SEPARATOR='%240F|%f'
        typeset -g POWERLEVEL9K_RIGHT_SUBSEGMENT_SEPARATOR='%240F|%f'
        typeset -g POWERLEVEL9K_LEFT_SEGMENT_SEPARATOR=
        typeset -g POWERLEVEL9K_RIGHT_SEGMENT_SEPARATOR=
        typeset -g POWERLEVEL9K_OS_ICON_CONTENT_EXPANSION='EV'
        typeset -g POWERLEVEL9K_OS_ICON_FOREGROUND=179
        typeset -g POWERLEVEL9K_MULTILINE_FIRST_PROMPT_PREFIX='%240F|%f '
        typeset -g POWERLEVEL9K_MULTILINE_NEWLINE_PROMPT_PREFIX='%240F|%f '
        typeset -g POWERLEVEL9K_MULTILINE_LAST_PROMPT_PREFIX='%240F`-%f '
        typeset -g POWERLEVEL9K_MULTILINE_FIRST_PROMPT_SUFFIX=
        typeset -g POWERLEVEL9K_MULTILINE_NEWLINE_PROMPT_SUFFIX=
        typeset -g POWERLEVEL9K_MULTILINE_LAST_PROMPT_SUFFIX=
        typeset -g POWERLEVEL9K_MULTILINE_FIRST_PROMPT_GAP_CHAR=' '
        typeset -g POWERLEVEL9K_DIR_FOREGROUND=252
        typeset -g POWERLEVEL9K_DIR_SHORTENED_FOREGROUND=247
        typeset -g POWERLEVEL9K_DIR_ANCHOR_FOREGROUND=179
        typeset -g POWERLEVEL9K_DIR_ANCHOR_BOLD=true
        typeset -g POWERLEVEL9K_VCS_BRANCH_ICON='git:'
        typeset -g POWERLEVEL9K_VCS_CLEAN_FOREGROUND=150
        typeset -g POWERLEVEL9K_VCS_UNTRACKED_FOREGROUND=179
        typeset -g POWERLEVEL9K_VCS_MODIFIED_FOREGROUND=216
        typeset -g POWERLEVEL9K_STATUS_OK_FOREGROUND=84
        typeset -g POWERLEVEL9K_STATUS_ERROR_FOREGROUND=203
        typeset -g POWERLEVEL9K_STATUS_OK_VISUAL_IDENTIFIER_EXPANSION='ok'
        typeset -g POWERLEVEL9K_STATUS_ERROR_VISUAL_IDENTIFIER_EXPANSION='!!'
        typeset -g POWERLEVEL9K_CONTEXT_ROOT_TEMPLATE='root@everlight'
        typeset -g POWERLEVEL9K_CONTEXT_TEMPLATE='%n@%m'
        typeset -g POWERLEVEL9K_CONTEXT_FOREGROUND=247
        typeset -g POWERLEVEL9K_CONTEXT_ROOT_FOREGROUND=247
        typeset -g POWERLEVEL9K_COMMAND_EXECUTION_TIME_FOREGROUND=244
        typeset -g POWERLEVEL9K_TIME_FOREGROUND=179
        typeset -g POWERLEVEL9K_TIME_FORMAT='%D{%b %d %I:%M %p}'
        typeset -g POWERLEVEL9K_INSTANT_PROMPT=off
        typeset -g POWERLEVEL9K_PROMPT_CHAR_OK_VIINS_CONTENT_EXPANSION='>'
        typeset -g POWERLEVEL9K_PROMPT_CHAR_ERROR_VIINS_CONTENT_EXPANSION='>'
        typeset -g POWERLEVEL9K_PROMPT_CHAR_OK_VIINS_FOREGROUND=179
        typeset -g POWERLEVEL9K_PROMPT_CHAR_ERROR_VIINS_FOREGROUND=203
        p10k reload >/dev/null 2>&1 || true
    else
        # Last-resort fallback if both Starship and p10k are unavailable.
        # NOTE: backtick MUST be escaped (\\\`) -- under PROMPT_SUBST a literal
        # backtick opens command substitution and zsh throws parse error every redraw.
        PROMPT=$'%F{240}|%f %F{252}%~%f\n%F{240}\\\`-%f %F{179}>%f '
        RPROMPT=$'%F{247}%n@%m%f %F{179}%*%f'
    fi
}

# EV logo with gold "E" + navy "V" + drop-shadow-feel via dim navy below.
# Navy matches the path-zone color in the prompt -- visual continuity.
_ev_brand_logo() {
    printf "%b\n" \
        "  ${_EV_BOLD}${_EV_GOLD}███████╗${_EV_NAVY}██╗   ██╗${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}██╔════╝${_EV_NAVY}██║   ██║${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}█████╗  ${_EV_NAVY}██║   ██║${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}██╔══╝  ${_EV_NAVY}╚██╗ ██╔╝${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}███████╗${_EV_NAVY} ╚████╔╝${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}╚══════╝${_EV_NAVY}  ╚═══╝${_EV_RESET}" \
        "  ${_EV_NAVY_DEEP}░░░░░░░░░░░░░░░░░░░${_EV_RESET}"
}

# Section header: emoji + bold gold text + navy underline (gradient feel).
# Usage: _ev_section "TITLE" "🤖 "
_ev_section() {
    local title="$1"
    local emoji="${2:-} "
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}  ${emoji}${_EV_BOLD}${_EV_GOLD}${title}${_EV_RESET}"
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}  ${_EV_NAVY}━━━━━━━━━━━━━━━━━━━━${_EV_RESET}"
}

# Indent rows under the section spine, navy ┃ on the left as a vertical accent.
_ev_row() {
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}    $1"
}

# Spine-only spacer (keeps the vertical line continuous between sections).
_ev_spine() {
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}"
}

# Status dots: ● green for live, ○ red for off. Stays compact and scannable.
_ev_service_status() {
    typeset -g _ev_bot_status="${_EV_RED}○ off${_EV_RESET}"
    typeset -g _ev_dash_status="${_EV_RED}○ off${_EV_RESET}"
    typeset -g _ev_django_status="${_EV_RED}○ off${_EV_RESET}"
    typeset -g _ev_ws_status="${_EV_RED}○ off${_EV_RESET}"
    typeset -g _ev_hive_status="${_EV_RED}○ off${_EV_RESET}"
    typeset -g _ev_code_status="${_EV_RED}○ off${_EV_RESET}"

    pgrep -f "xpb-fg|main.py.*xlm_bot" &>/dev/null && _ev_bot_status="${_EV_GREEN}● live${_EV_RESET}"
    pgrep -f "streamlit.*dashboard" &>/dev/null && _ev_dash_status="${_EV_GREEN}● :8502${_EV_RESET}"
    pgrep -f "manage.py runserver.*8503" &>/dev/null && _ev_django_status="${_EV_GREEN}● :8503${_EV_RESET}"
    pgrep -f "xws-fg|live_ws.py" &>/dev/null && _ev_ws_status="${_EV_GREEN}● live${_EV_RESET}"
    pgrep -f "manage.py runserver.*8504" &>/dev/null && _ev_hive_status="${_EV_GREEN}● :8504${_EV_RESET}"
    pgrep -f "code-server" &>/dev/null && _ev_code_status="${_EV_GREEN}● :8080${_EV_RESET}"
}

# Optional: render a wallpaper-style image at top of banner via chafa.
# Drop any image at /root/.config/lucrex/banner.* and it'll show on shell open.
_ev_banner_image() {
    if ! command -v chafa >/dev/null 2>&1; then
        return 0
    fi
    local img
    for img in /root/.config/lucrex/banner.png /root/.config/lucrex/banner.jpg /root/.config/lucrex/banner.jpeg /root/.config/lucrex/banner.webp; do
        if [[ -r "$img" ]]; then
            chafa --size=72x18 --symbols=block --colors=256 --dither=ordered "$img" 2>/dev/null
            return 0
        fi
    done
}

_ev_print_banner() {
    _ev_service_status
    # Chafa "wallpaper" image first (acts as the title splash). Drop any
    # image at /root/.config/lucrex/banner.{png,jpg,jpeg,webp} to swap.
    _ev_banner_image
    echo ""
    _ev_brand_logo
    echo ""

    # Glass-card header bar: navy bg, gold text, gold/turquoise diamond separators.
    local _ts="$(date '+%b %d, %Y %H:%M')"
    local _bar_top="${_EV_GOLD}╭───────────────────────────────────────────────────────╮${_EV_RESET}"
    local _bar_mid="${_EV_GOLD}│${_EV_RESET} ${_EV_BG_NAVY}${_EV_BOLD}${_EV_GOLD_HOT} ✨ EVERLIGHT VENTURES${_EV_RESET}${_EV_BG_NAVY} ${_EV_TURQUOISE}◆${_EV_RESET}${_EV_BG_NAVY} ${_EV_SILVER}LUCREX OS${_EV_RESET}${_EV_BG_NAVY} ${_EV_TURQUOISE}◆${_EV_RESET}${_EV_BG_NAVY} ${_EV_GOLD}${_ts}${_EV_RESET} ${_EV_GOLD}│${_EV_RESET}"
    local _bar_bot="${_EV_GOLD}╰───────────────────────────────────────────────────────╯${_EV_RESET}"
    printf "%b\n" "  $_bar_top"
    printf "%b\n" "  $_bar_mid"
    printf "%b\n" "  $_bar_bot"
    echo ""

    _ev_row "${_EV_TURQUOISE}command center${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_SILVER_DIM}cyberluxe terminal${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_GREEN}● live deploy${_EV_RESET}"
    _ev_spine

    _ev_section "AI WORKERS" "🤖"
    _ev_row "${_EV_BOLD}${_EV_GOLD}ai${_EV_RESET} ${_EV_SILVER_DIM}GPT${_EV_RESET}    ${_EV_BOLD}${_EV_GOLD}cx${_EV_RESET} ${_EV_SILVER_DIM}Codex${_EV_RESET}    ${_EV_BOLD}${_EV_GOLD}ppx${_EV_RESET} ${_EV_SILVER_DIM}Perplexity${_EV_RESET}    ${_EV_BOLD}${_EV_GOLD}ask${_EV_RESET} ${_EV_SILVER_DIM}Auto-route${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}gm${_EV_RESET} ${_EV_SILVER_DIM}Gemini${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}cl${_EV_RESET} ${_EV_SILVER_DIM}Claude${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}hive${_EV_RESET} ${_EV_SILVER_DIM}Hive Mind${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}evdoctor${_EV_RESET} ${_EV_SILVER_DIM}terminal audit${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}sysinfo${_EV_RESET} ${_EV_SILVER_DIM}system view${_EV_RESET}"
    _ev_spine

    _ev_section "XLM BOT" "⚡"
    _ev_row "${_EV_BOLD}${_EV_GOLD}xon${_EV_RESET} ${_EV_SILVER_DIM}Start all${_EV_RESET}    ${_EV_BOLD}${_EV_GOLD}xpb${_EV_RESET} ${_EV_SILVER_DIM}Bot${_EV_RESET} ${_ev_bot_status}    ${_EV_BOLD}${_EV_GOLD}xws${_EV_RESET} ${_EV_SILVER_DIM}WS feed${_EV_RESET} ${_ev_ws_status}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}xdr${_EV_RESET} ${_EV_SILVER_DIM}Streamlit${_EV_RESET} ${_ev_dash_status}  ${_EV_BOLD}${_EV_GOLD}ddr${_EV_RESET} ${_EV_SILVER_DIM}Django${_EV_RESET} ${_ev_django_status}  ${_EV_BOLD}${_EV_GOLD}rdx${_EV_RESET} ${_EV_SILVER_DIM}restart${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}rxl${_EV_RESET} ${_EV_SILVER_DIM}logs${_EV_RESET}"
    _ev_spine

    # ── live service health (one curl per port, ~70ms each cached) ──────────
    local _h_2000 _h_2200 _h_2300 _h_2301 _h_2302 _h_2400 _h_2500 _h_2700 _h_2701
    _h_2000=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2000/ 2>/dev/null)
    _h_2200=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2200/ 2>/dev/null)
    _h_2300=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2300/ 2>/dev/null)
    _h_2301=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2301/healthz 2>/dev/null)
    _h_2302=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2302/healthz 2>/dev/null)
    _h_2400=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2400/ 2>/dev/null)
    _h_2500=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2500/ 2>/dev/null)
    _h_2700=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2700/health 2>/dev/null)
    _h_2701=$(curl -s -o /dev/null -w "%{http_code}" -m 1 http://127.0.0.1:2701/healthz 2>/dev/null)
    _pill() { case "$1" in 200|404) echo "${_EV_GREEN}●${_EV_RESET}" ;; *) echo "${_EV_RED}○${_EV_RESET}" ;; esac; }

    _ev_section "SERVICE HEALTH  ::  watchdog cron 1 min" "🩺"
    _ev_row "  $(_pill $_h_2000) :2000 hub  $(_pill $_h_2200) :2200 reports  $(_pill $_h_2300) :2300 intel  $(_pill $_h_2301) :2301 intel-api"
    _ev_row "  $(_pill $_h_2302) :2302 esign  $(_pill $_h_2400) :2400 apps  $(_pill $_h_2500) :2500 mma   $(_pill $_h_2700) :2700 blinko  $(_pill $_h_2701) :2701 mcp-bridge"
    _ev_row "  ${_EV_SILVER_DIM}(any ○ → watchdog auto-heals next cron)${_EV_RESET}"
    _ev_spine

    _ev_section "DASHBOARDS  ::  hub > band > sub-page" "📊"
    _ev_row "${_EV_BOLD}${_EV_GOLD_HOT}hub${_EV_RESET}  ${_EV_BOLD}2000${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2000/${_EV_RESET}  ${_EV_SILVER_DIM}master tree, start here${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}markets${_EV_RESET}  ${_EV_BOLD}2100${_EV_RESET}  ${_EV_SILVER_DIM}Markets / Trading${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2100${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2100/${_EV_RESET}                ${_EV_SILVER_DIM}XLM Bot dashboard${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}reports${_EV_RESET}  ${_EV_BOLD}2200${_EV_RESET}  ${_EV_SILVER_DIM}Reports / Ops${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2200${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2200/${_EV_RESET}                ${_EV_SILVER_DIM}band root${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2200.1${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/${_EV_RESET}        ${_EV_SILVER_DIM}76+ generated reports${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2200.2${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/dashboards/${_EV_RESET}     ${_EV_SILVER_DIM}index page${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}intel${_EV_RESET}    ${_EV_BOLD}2300${_EV_RESET}  ${_EV_SILVER_DIM}Intel Center${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2300${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2300/${_EV_RESET}                ${_EV_SILVER_DIM}static dashboard${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2300.1${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2300/clients.html${_EV_RESET}    ${_EV_SILVER_DIM}clients view${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2300.2${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2300/resources.html${_EV_RESET}  ${_EV_SILVER_DIM}resources catalog${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2301${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2301/${_EV_RESET}                ${_EV_SILVER_DIM}OSINT FastAPI${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2301.1${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2301/api/docs${_EV_RESET}        ${_EV_SILVER_DIM}swagger ui${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}apps${_EV_RESET}     ${_EV_BOLD}2400${_EV_RESET}  ${_EV_SILVER_DIM}Consumer / Apps${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2400${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2400/game_v6.html${_EV_RESET}    ${_EV_SILVER_DIM}Alley Kingz prototype${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}health${_EV_RESET}   ${_EV_BOLD}2500${_EV_RESET}  ${_EV_SILVER_DIM}Personal / Health${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2500${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2500/${_EV_RESET}                ${_EV_SILVER_DIM}MMA Fight Camp${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2500.1${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2500/05_Fitness/${_EV_RESET}     ${_EV_SILVER_DIM}fitness mirror${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}memory${_EV_RESET}   ${_EV_BOLD}2700${_EV_RESET}  ${_EV_SILVER_DIM}Memory + MCP${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2700${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2700/${_EV_RESET}                ${_EV_SILVER_DIM}Blinko RAG (614+ notes)${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_BOLD}2701${_EV_RESET}    ${_EV_TURQUOISE}http://127.0.0.1:2701/healthz${_EV_RESET}         ${_EV_SILVER_DIM}MCP HTTP bridge${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_BOLD}2701.1${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2701/list_tools${_EV_RESET}      ${_EV_SILVER_DIM}28 tools across 3 services${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_BOLD}${_EV_GOLD}dashboards${_EV_RESET}  ${_EV_SILVER_DIM}branded HTML (Master Hub tiles)${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/RICH_TODO_LIVE.html${_EV_RESET}      ${_EV_SILVER_DIM}master TODO${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/RESOURCES_HUB.html${_EV_RESET}       ${_EV_SILVER_DIM}745 free tools, categorized${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/HIVE_MIND.html${_EV_RESET}           ${_EV_SILVER_DIM}94 agents, 28 tools${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}├${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/SERVICES_REGISTRY.html${_EV_RESET}   ${_EV_SILVER_DIM}24 external services${_EV_RESET}"
    _ev_row "  ${_EV_GOLD}└${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/xlm_honest_dashboard.html${_EV_RESET} ${_EV_SILVER_DIM}XLM bot truth layer${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_SILVER_DIM}usage:  <band> [list|recent|search|api|...]   ${_EV_RESET}${_EV_GOLD}dashboards${_EV_RESET}${_EV_SILVER_DIM} = print this map${_EV_RESET}"
    _ev_spine

    _ev_section "NAVIGATION" "🌐"
    _ev_row "${_EV_BOLD}${_EV_GOLD}cdw${_EV_RESET} ${_EV_SILVER_DIM}workspace root${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}ev${_EV_RESET} ${_EV_SILVER_DIM}Everlight${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}llp${_EV_RESET} ${_EV_SILVER_DIM}Last Light${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}content${_EV_RESET} ${_EV_SILVER_DIM}Content${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}dev${_EV_RESET} ${_EV_SILVER_DIM}Development${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}media${_EV_RESET} ${_EV_SILVER_DIM}Media${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}auto${_EV_RESET} ${_EV_SILVER_DIM}Automation${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}drive${_EV_RESET} ${_EV_SILVER_DIM}Root${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}menu${_EV_RESET} ${_EV_SILVER_DIM}rerun menu${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}links${_EV_RESET} ${_EV_SILVER_DIM}dash URLs${_EV_RESET}"
    _ev_spine

    _ev_section "TOOLS" "🔧"
    _ev_row "${_EV_BOLD}${_EV_GOLD}ide${_EV_RESET} ${_EV_SILVER_DIM}tmux${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}v${_EV_RESET} ${_EV_SILVER_DIM}nvim${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}space${_EV_RESET} ${_EV_SILVER_DIM}disk usage${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}ws${_EV_RESET} ${_EV_SILVER_DIM}orchestrator${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}cb${_EV_RESET} ${_EV_SILVER_DIM}crypto bot${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}organize${_EV_RESET} ${_EV_SILVER_DIM}sync run${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}sync-status${_EV_RESET} ${_EV_SILVER_DIM}status${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}code-start${_EV_RESET} ${_EV_SILVER_DIM}Code Server${_EV_RESET} ${_ev_code_status}  ${_EV_BOLD}${_EV_GOLD}code-stop${_EV_RESET}  ${_EV_BOLD}${_EV_GOLD}code-status${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}palette${_EV_RESET} ${_EV_SILVER_DIM}color test${_EV_RESET}"
    _ev_spine

    _ev_section "EXTERNAL  ::  not yet rehomed" "🔗"
    _ev_row "${_EV_BOLD}${_EV_GOLD}site${_EV_RESET}    ${_EV_TURQUOISE}https://everlightventures.io/${_EV_RESET}                       ${_EV_SILVER_DIM}public site${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}lucrex${_EV_RESET}  ${_EV_DIM}http://129.159.38.250:8080/lucrex/${_EV_RESET}                  ${_EV_SILVER_DIM}DEAD, awaits 2700 rehome${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}blinko${_EV_RESET}  ${_EV_DIM}http://129.159.38.250:1111/${_EV_RESET}                         ${_EV_SILVER_DIM}DEAD, planned for e5-mother${_EV_RESET}"
    _ev_spine

    _ev_section "NEW THIS ROUND" "✨"
    _ev_row "${_EV_BOLD}${_EV_GOLD}/trade-history${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}/taskboard${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}/sessions${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}/reports${_EV_RESET}   ${_EV_BOLD}${_EV_GOLD}/settings${_EV_RESET}"
    _ev_row "${_EV_SILVER_DIM}splash plays once per session${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}╰─${_EV_RESET} ${_EV_GOLD_HOT}⚡ ready${_EV_RESET}"
    echo ""
}

menu() {
    _ev_print_banner
}

links() {
    printf "%b\n" \
        "  ${_EV_GOLD_HOT}hub${_EV_RESET}     2000   ${_EV_TURQUOISE}http://127.0.0.1:2000/${_EV_RESET}" \
        "  ${_EV_GOLD}markets${_EV_RESET} 2100   ${_EV_TURQUOISE}http://127.0.0.1:2100/${_EV_RESET}" \
        "  ${_EV_GOLD}reports${_EV_RESET} 2200   ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/${_EV_RESET}" \
        "  ${_EV_GOLD}intel${_EV_RESET}   2300   ${_EV_TURQUOISE}http://127.0.0.1:2300/${_EV_RESET}    ${_EV_DIM}(api 2301)${_EV_RESET}" \
        "  ${_EV_GOLD}apps${_EV_RESET}    2400   ${_EV_TURQUOISE}http://127.0.0.1:2400/game_v6.html${_EV_RESET}" \
        "  ${_EV_GOLD}health${_EV_RESET}  2500   ${_EV_TURQUOISE}http://127.0.0.1:2500/${_EV_RESET}" \
        "  ${_EV_DIM}--${_EV_RESET}" \
        "  ${_EV_GOLD}site${_EV_RESET}           ${_EV_TURQUOISE}https://everlightventures.io/${_EV_RESET}"
}

palette() {
    printf "%b\n" \
        "  ${_EV_GOLD}gold${_EV_RESET}  ${_EV_WHITE}platinum${_EV_RESET}  ${_EV_GREEN}live${_EV_RESET}  ${_EV_RED}alert${_EV_RESET}  ${_EV_DIM}graphite${_EV_RESET}"
}

unalias sysinfo 2>/dev/null
sysinfo() {
    local _os _kernel _uptime _shell _memory _disk _ip _font _prompt
    _os="$(. /etc/os-release 2>/dev/null; printf '%s' "${PRETTY_NAME:-Ubuntu}")"
    _kernel="$(uname -r 2>/dev/null)"
    _uptime="$(uptime -p 2>/dev/null | sed 's/^up //')"
    _shell="${SHELL:t} ${ZSH_VERSION:-}"
    _memory="$(free -h 2>/dev/null | awk '/^Mem:/ {print $3 " / " $2 " (" $5 ")"}')"
    _disk="$(df -h / 2>/dev/null | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')"
    _ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    _font="$(fc-match monospace 2>/dev/null | head -n 1)"
    _prompt="fallback"
    (( $+functions[p10k] )) && _prompt="powerlevel10k"

    echo ""
    _ev_brand_logo
    echo ""
    printf "%b\n" "  ${_EV_GOLD}EVERLIGHT TERMINAL${_EV_RESET} ${_EV_DIM}|${_EV_RESET} ${_EV_CYAN}system view${_EV_RESET}"
    printf "%b\n" "  ${_EV_DIM}-------------------------------------------------------${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}OS${_EV_RESET}       ${_EV_DIM}${_os}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Kernel${_EV_RESET}   ${_EV_DIM}${_kernel}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Uptime${_EV_RESET}   ${_EV_DIM}${_uptime:-unknown}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Shell${_EV_RESET}    ${_EV_DIM}${_shell}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Prompt${_EV_RESET}   ${_EV_DIM}${_prompt}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Memory${_EV_RESET}   ${_EV_DIM}${_memory:-unknown}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Disk${_EV_RESET}     ${_EV_DIM}${_disk:-unknown}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}IP${_EV_RESET}       ${_EV_DIM}${_ip:-offline}${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}Font${_EV_RESET}     ${_EV_DIM}${_font:-unknown}${_EV_RESET}"
    echo ""
}

evdoctor() {
    local _theme="missing" _prompt="fallback" _font="unknown"
    [[ -r /root/powerlevel10k/powerlevel10k.zsh-theme ]] && _theme="installed"
    (( $+functions[p10k] )) && _prompt="loaded"
    _font="$(fc-match monospace 2>/dev/null | head -n 1)"

    printf "%b\n" \
        "  ${_EV_GOLD}Theme${_EV_RESET}    ${_EV_DIM}${_theme}${_EV_RESET}" \
        "  ${_EV_GOLD}Prompt${_EV_RESET}   ${_EV_DIM}${_prompt}${_EV_RESET}" \
        "  ${_EV_GOLD}Colors${_EV_RESET}   ${_EV_DIM}${COLORTERM:-unset}${_EV_RESET}" \
        "  ${_EV_GOLD}Font${_EV_RESET}     ${_EV_DIM}${_font}${_EV_RESET}"
}

export LS_COLORS='di=38;5;179:ln=38;5;247:so=38;5;145:pi=38;5;145:ex=38;5;150:bd=38;5;179:cd=38;5;179:su=38;5;203:sg=38;5;216:ow=38;5;216:tw=38;5;216:fi=38;5;252:*.md=38;5;250:*.sh=38;5;180:*.py=38;5;223:*.json=38;5;247:*.yaml=38;5;247:*.yml=38;5;247:*.ts=38;5;223:*.tsx=38;5;223'

if command -v lsd &>/dev/null; then
    unalias ls ll la lt 2>/dev/null
    # Fancy icons = Nerd Font glyphs (folder, file-type, language icons).
    # Requires Nerd Font in Termux (~/.termux/font.ttf, JetBrainsMono Nerd Font).
    alias ls='lsd --group-dirs=first --icon=auto --icon-theme=fancy --blocks=name'
    alias ll='lsd -l --group-dirs=first --icon=auto --icon-theme=fancy --date=relative --size=short'
    alias la='lsd -la --group-dirs=first --icon=auto --icon-theme=fancy --date=relative --size=short'
    alias lt='lsd --tree --depth=3 --group-dirs=first --icon=auto --icon-theme=fancy'
    # Bonus: longer tree depth, all files, with git-status hints.
    alias ltree='lsd --tree --depth=5 --group-dirs=first --icon=auto --icon-theme=fancy -a'
fi

# ===========================================================
# nnn -- tap-friendly TUI file browser (replaces "tap to cd")
# ===========================================================
# Inside nnn:
#   - Tap a folder to enter it (mouse mode is on by default)
#   - Tap a file to open in default app (or press 'e' to edit)
#   - 'q' quits AND your shell follows you to the last folder you were in
#   - Backspace / Left arrow goes up a directory
#   - 'h' toggles hidden files, '/' to filter, 'd' for detail view
#   - '?' brings up the full help screen
#
# Aliases: `f` or `n` -- both launch nnn with cd-on-quit wired up.
if command -v nnn &>/dev/null; then
    # nnn config goes here. NNN_FCOLORS uses 12 hex pairs for file types;
    # default is fine. NNN_OPTS: a=auto-cd-on-quit, e=use $EDITOR for previews,
    # x=xdg-open default, H=show hidden, U=show user/group columns.
    export NNN_TMPFILE="${XDG_CONFIG_HOME:-$HOME/.config}/nnn/.lastd"
    export NNN_OPTS="aeU"
    export EDITOR="${EDITOR:-nvim}"

    n() {
        # Block nesting -- nnn-in-nnn breaks the cd-on-quit loop.
        [ "${NNNLVL:-0}" -eq 0 ] || { echo "nnn already running" >&2; return 1; }
        mkdir -p "$(dirname "$NNN_TMPFILE")"
        command nnn "$@"
        # If nnn wrote the last-dir file on quit, source it to cd this shell.
        if [ -f "$NNN_TMPFILE" ]; then
            . "$NNN_TMPFILE"
            rm -f "$NNN_TMPFILE"
        fi
    }
    alias f='n'
fi

if [[ -o interactive ]]; then
    _ev_prompt_init

    if [[ -z "${EV_BANNER_SHOWN:-}" ]]; then
        _ev_print_banner
        export EV_BANNER_SHOWN=1

        # On first interactive shell of the session: kick the dashboards watchdog
        # in the background. It restarts anything that's down (idempotent, safe).
        # Cron also runs it every minute, but this catches the gap between phone
        # power-on and the first cron tick.
        if [[ -x /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh ]]; then
            ( bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --quiet & ) >/dev/null 2>&1
        fi
    fi

    # Prevent the later fastfetch hook in ~/.zshrc from rendering a second startup block.
    export EV_FETCH_SHOWN=1
fi
