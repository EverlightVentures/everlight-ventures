# ============================================================
# EVERLIGHT BRAND LAYER  --  host-portable
# ============================================================
# The shared Lucrex identity: palette, logo, banner, dashboard
# bands. Designed to be sourced by ANY host (phone proot, Arch
# PC, e5) as the LAST line of that host's .zshrc.
#
# Contract, deliberately narrow so it can never clobber a host:
#   * NEVER touches PROMPT / RPROMPT. Each host keeps its own
#     prompt engine (phone = starship, AceMagician = p10k).
#   * NEVER overrides an alias or function that already exists.
#     Every definition is guarded. Host-local shortcuts win.
#   * All paths derive from $EL_HOME, so the same file works at
#     /mnt/sdcard/AA_MY_DRIVE and at /AA_MY_DRIVE.
#   * No termux/proot assumptions. URL opening is auto-detected.
#
# Created 2026-08-06 by splitting the portable half out of
# everlight_shell.zsh so the PC could adopt the brand without
# inheriting phone internals.
# ============================================================

# ---- single-source guard ----
if [[ -n "${EV_BRAND_LOADED:-}" ]]; then
    return 0
fi
export EV_BRAND_LOADED=1

# ---- workspace root, host-agnostic ----
if [[ -z "${EL_HOME:-}" ]]; then
    for _c in /AA_MY_DRIVE /mnt/sdcard/AA_MY_DRIVE "$HOME/AA_MY_DRIVE"; do
        [[ -d "$_c" ]] && export EL_HOME="$_c" && break
    done
    unset _c
fi

export COLORTERM="${COLORTERM:-truecolor}"

# ============================================================
# PALETTE  --  the gold-and-blue. Truecolor, not 256.
# Single source of truth is content_tools/report_template.py;
# these are the terminal mirror of that palette.
# ============================================================
typeset -gr _EV_RESET=$'\033[0m'
typeset -gr _EV_BOLD=$'\033[1m'
typeset -gr _EV_DIM=$'\033[2m'
typeset -gr _EV_ITALIC=$'\033[3m'

typeset -gr _EV_GOLD=$'\033[38;2;212;168;67m'            # #D4AF37 brand gold
typeset -gr _EV_GOLD_HOT=$'\033[38;2;255;205;60m'        # #FFCD3C bright gold
typeset -gr _EV_NAVY=$'\033[38;2;26;45;92m'              # #1A2D5C path navy
typeset -gr _EV_NAVY_DEEP=$'\033[38;2;15;27;61m'         # #0F1B3D deep navy
typeset -gr _EV_NAVY_PALE=$'\033[38;2;45;63;112m'        # #2D3F70 light navy
typeset -gr _EV_TURQUOISE=$'\033[38;2;0;229;255m'        # #00E5FF hot accent
typeset -gr _EV_TURQUOISE_PALE=$'\033[38;2;125;249;255m' # #7DF9FF pale pop
typeset -gr _EV_SILVER=$'\033[38;2;199;201;209m'         # #C7C9D1 silver
typeset -gr _EV_SILVER_DIM=$'\033[38;2;122;126;140m'     # #7A7E8C dim grey
typeset -gr _EV_DARK=$'\033[38;2;10;10;10m'              # #0A0A0A canvas black
typeset -gr _EV_GREEN=$'\033[38;2;0;255;157m'            # #00FF9D live
typeset -gr _EV_RED=$'\033[38;2;255;0;60m'               # #FF003C error
typeset -gr _EV_AMBER=$'\033[38;2;255;179;0m'            # #FFB300 warning

typeset -gr _EV_BG_NAVY=$'\033[48;2;26;45;92m'
typeset -gr _EV_BG_NAVY_DEEP=$'\033[48;2;15;27;61m'
typeset -gr _EV_BG_GOLD=$'\033[48;2;212;168;67m'

typeset -gr _EV_CYAN=$_EV_TURQUOISE
typeset -gr _EV_WHITE=$_EV_SILVER

# ============================================================
# PRIMITIVES
# ============================================================

# Portable URL opener. Falls back down the chain until something works.
_ev_open() {
    local url="$1"
    if command -v termux-open-url >/dev/null 2>&1; then
        termux-open-url "$url"
    elif command -v xdg-open >/dev/null 2>&1; then
        nohup xdg-open "$url" >/dev/null 2>&1 & disown
    elif [[ -n "${BROWSER:-}" ]] && command -v "${BROWSER%% *}" >/dev/null 2>&1; then
        nohup $BROWSER "$url" >/dev/null 2>&1 & disown
    else
        printf "%b\n" "  ${_EV_TURQUOISE}${url}${_EV_RESET}"
    fi
}

# Define an alias only if that name is not already taken. Host wins.
_ev_alias() {
    local name="$1" body="$2"
    (( $+aliases[$name] )) && return 0
    (( $+functions[$name] )) && return 0
    command -v "$name" >/dev/null 2>&1 && return 0
    alias "$name"="$body"
}

_ev_brand_logo() {
    printf "%b\n" \
        "  ${_EV_BOLD}${_EV_GOLD}███████╗${_EV_NAVY}██╗   ██╗${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}██╔════╝${_EV_NAVY}██║   ██║${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}█████╗  ${_EV_NAVY}██║   ██║${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}██╔══╝  ${_EV_NAVY}╚██╗ ██╔╝${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}███████╗${_EV_NAVY} ╚████╔╝${_EV_RESET}" \
        "  ${_EV_BOLD}${_EV_GOLD}╚══════╝${_EV_NAVY}  ╚═══╝${_EV_RESET}" \
        "  ${_EV_SILVER_DIM}E V E R L I G H T   V E N T U R E S${_EV_RESET}"
}

_ev_section() {
    local title="$1" emoji="${2:-} "
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}  ${emoji}${_EV_BOLD}${_EV_GOLD}${title}${_EV_RESET}"
    printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}  ${_EV_NAVY}━━━━━━━━━━━━━━━━━━━━${_EV_RESET}"
}

_ev_row()   { printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}    $1"; }
_ev_spine() { printf "%b\n" "  ${_EV_NAVY}┃${_EV_RESET}"; }

# Which prompt engine is actually DRIVING this shell.
# Order matters: STARSHIP_SHELL is only set once starship's init has really
# run, whereas `command -v starship` merely proves the binary is installed.
# The AceMagician has the starship binary but is driven by p10k, so testing
# the binary first mislabels that host.
_ev_prompt_engine() {
    if [[ -n "${STARSHIP_SHELL:-}" ]]; then
        echo "starship"
    elif (( $+functions[p10k] )) || [[ "${ZSH_THEME:-}" == *powerlevel10k* ]]; then
        echo "powerlevel10k"
    elif command -v starship >/dev/null 2>&1; then
        echo "starship"
    else
        echo "zsh"
    fi
}

# ============================================================
# DASHBOARD BANDS  --  2000 hub / 2100 markets / 2200 reports
# 2300 intel / 2400 apps / 2500 health / 2700 memory+lucrex
# ============================================================

hub() { _ev_open "http://127.0.0.1:2000/"; }

markets() {
    case "${1:-}" in
        list) echo "2100  XLM Bot dashboard" ;;
        *)    _ev_open "http://127.0.0.1:2100/" ;;
    esac
}

reports() {
    case "${1:-}" in
        list)   echo "2200    band root"; echo "2200.1  /reports/"; echo "2200.2  /dashboards/" ;;
        recent) ls -t "$EL_HOME/09_DASHBOARD/reports/" 2>/dev/null | head -10 ;;
        search) shift; grep -l "$@" "$EL_HOME"/09_DASHBOARD/reports/*.html 2>/dev/null | head ;;
        *)      _ev_open "http://127.0.0.1:2200/reports/" ;;
    esac
}

intel() {
    case "${1:-}" in
        list)         echo "2300 static"; echo "2300.1 clients"; echo "2300.2 resources"; echo "2301 FastAPI"; echo "2301.1 swagger" ;;
        api)          _ev_open "http://127.0.0.1:2301/" ;;
        docs|swagger) _ev_open "http://127.0.0.1:2301/api/docs" ;;
        *)            _ev_open "http://127.0.0.1:2300/" ;;
    esac
}

apps() {
    case "${1:-}" in
        list)     echo "2400  Alley Kingz prototype (game_v6.html)" ;;
        ak|kingz) _ev_open "http://127.0.0.1:2400/game_v6.html" ;;
        *)        _ev_open "http://127.0.0.1:2400/" ;;
    esac
}

health() {
    case "${1:-}" in
        list)        echo "2500    MMA Fight Camp"; echo "2500.1  /05_Fitness/" ;;
        fitness|fit) _ev_open "http://127.0.0.1:2500/05_Fitness/" ;;
        *)           _ev_open "http://127.0.0.1:2500/" ;;
    esac
}

memory() {
    case "${1:-}" in
        list)   echo "2700 blinko lite"; echo "2701 mcp bridge"; echo "2702 lucrex" ;;
        mcp)    _ev_open "http://127.0.0.1:2701/list_tools" ;;
        lucrex) _ev_open "http://127.0.0.1:2702/" ;;
        *)      _ev_open "http://127.0.0.1:2700/" ;;
    esac
}

links() {
    printf "%b\n" \
        "  ${_EV_GOLD_HOT}hub${_EV_RESET}     2000   ${_EV_TURQUOISE}http://127.0.0.1:2000/${_EV_RESET}" \
        "  ${_EV_GOLD}markets${_EV_RESET} 2100   ${_EV_TURQUOISE}http://127.0.0.1:2100/${_EV_RESET}" \
        "  ${_EV_GOLD}reports${_EV_RESET} 2200   ${_EV_TURQUOISE}http://127.0.0.1:2200/reports/${_EV_RESET}" \
        "  ${_EV_GOLD}intel${_EV_RESET}   2300   ${_EV_TURQUOISE}http://127.0.0.1:2300/${_EV_RESET}    ${_EV_DIM}(api 2301)${_EV_RESET}" \
        "  ${_EV_GOLD}apps${_EV_RESET}    2400   ${_EV_TURQUOISE}http://127.0.0.1:2400/game_v6.html${_EV_RESET}" \
        "  ${_EV_GOLD}health${_EV_RESET}  2500   ${_EV_TURQUOISE}http://127.0.0.1:2500/${_EV_RESET}" \
        "  ${_EV_GOLD}memory${_EV_RESET}  2700   ${_EV_TURQUOISE}http://127.0.0.1:2700/${_EV_RESET}    ${_EV_DIM}(blinko lite)${_EV_RESET}" \
        "  ${_EV_GOLD}lucrex${_EV_RESET}  2702   ${_EV_TURQUOISE}http://127.0.0.1:2702/${_EV_RESET}" \
        "  ${_EV_DIM}--${_EV_RESET}" \
        "  ${_EV_GOLD}site${_EV_RESET}           ${_EV_TURQUOISE}https://everlightventures.io/${_EV_RESET}" \
        "  ${_EV_GOLD}blinko${_EV_RESET}         ${_EV_TURQUOISE}http://e5-mother:1111/${_EV_RESET}   ${_EV_DIM}(tailnet)${_EV_RESET}"
}

palette() {
    printf "%b\n" \
        "  ${_EV_GOLD}████${_EV_RESET} gold      #D4AF37" \
        "  ${_EV_GOLD_HOT}████${_EV_RESET} gold hot  #FFCD3C" \
        "  ${_EV_NAVY}████${_EV_RESET} navy      #1A2D5C" \
        "  ${_EV_NAVY_PALE}████${_EV_RESET} navy pale #2D3F70" \
        "  ${_EV_TURQUOISE}████${_EV_RESET} turquoise #00E5FF" \
        "  ${_EV_SILVER}████${_EV_RESET} silver    #C7C9D1" \
        "  ${_EV_GREEN}████${_EV_RESET} live      #00FF9D" \
        "  ${_EV_RED}████${_EV_RESET} error     #FF003C"
}

# ============================================================
# BANNER
# ============================================================
_ev_print_banner() {
    _ev_brand_logo
    echo ""

    local _ts _host
    _ts="$(date '+%b %d, %Y %H:%M')"
    _host="$(hostname 2>/dev/null || echo unknown)"
    printf "%b\n" "  ${_EV_GOLD}╭───────────────────────────────────────────────────────╮${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}│${_EV_RESET} ${_EV_BG_NAVY}${_EV_BOLD}${_EV_GOLD_HOT} ✨ EVERLIGHT VENTURES${_EV_RESET}${_EV_BG_NAVY} ${_EV_TURQUOISE}◆${_EV_RESET}${_EV_BG_NAVY} ${_EV_SILVER}LUCREX OS${_EV_RESET}${_EV_BG_NAVY} ${_EV_TURQUOISE}◆${_EV_RESET}${_EV_BG_NAVY} ${_EV_GOLD}${_ts}${_EV_RESET} ${_EV_GOLD}│${_EV_RESET}"
    printf "%b\n" "  ${_EV_GOLD}╰───────────────────────────────────────────────────────╯${_EV_RESET}"
    echo ""

    _ev_row "${_EV_TURQUOISE}command center${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_SILVER_DIM}cyberluxe terminal${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_GOLD_HOT}${_host}${_EV_RESET}"
    _ev_spine

    # SYSTEM, live on every open
    local _os _kr _up _ram _swp _dsk
    _os="$(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-Linux}")"
    _kr="$(uname -r 2>/dev/null)"
    _up="$(uptime -p 2>/dev/null | sed 's/^up //')"
    _ram="$(free -h 2>/dev/null | awk '/^Mem:/{print $3"/"$2}')"
    _swp="$(free -h 2>/dev/null | awk '/^Swap:/{print $3"/"$2}')"
    _dsk="$(df -h "$EL_HOME" 2>/dev/null | awk 'NR==2{print $5}')"
    _ev_section "SYSTEM" "🖥"
    _ev_row "${_EV_GOLD}${_os}${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_SILVER}Linux ${_kr}${_EV_RESET} ${_EV_SILVER_DIM}·${_EV_RESET} ${_EV_SILVER}$(uname -m 2>/dev/null) $(nproc 2>/dev/null)-core${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}RAM${_EV_RESET} ${_ram}  ${_EV_BOLD}${_EV_GOLD}swap${_EV_RESET} ${_swp}  ${_EV_BOLD}${_EV_GOLD}disk${_EV_RESET} ${_dsk}  ${_EV_BOLD}${_EV_GOLD}up${_EV_RESET} ${_up}"
    _ev_row "${_EV_SILVER_DIM}workspace ${EL_HOME} · zsh+$(_ev_prompt_engine)${_EV_RESET}"
    _ev_spine

    # Live service health, one short curl per port
    local p code out=""
    _ev_section "SERVICE HEALTH" "🩺"
    for p in 2000:hub 2100:markets 2200:reports 2300:intel 2400:apps 2500:health 2700:blinko 2702:lucrex; do
        code=$(curl -s -o /dev/null -w "%{http_code}" -m 1 "http://127.0.0.1:${p%%:*}/" 2>/dev/null)
        case "$code" in
            200|404|302) out+="${_EV_GREEN}●${_EV_RESET} :${p%%:*} ${p##*:}  " ;;
            *)           out+="${_EV_RED}○${_EV_RESET} :${p%%:*} ${p##*:}  " ;;
        esac
    done
    _ev_row "$out"
    _ev_spine

    _ev_section "DASHBOARDS  ::  band > sub-command" "📊"
    _ev_row "${_EV_BOLD}${_EV_GOLD_HOT}hub${_EV_RESET}      ${_EV_BOLD}2000${_EV_RESET}  ${_EV_TURQUOISE}http://127.0.0.1:2000/${_EV_RESET}  ${_EV_SILVER_DIM}master tree, start here${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}markets${_EV_RESET}  ${_EV_BOLD}2100${_EV_RESET}  ${_EV_SILVER_DIM}XLM bot / trading${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}reports${_EV_RESET}  ${_EV_BOLD}2200${_EV_RESET}  ${_EV_SILVER_DIM}generated reports  ${_EV_RESET}${_EV_DIM}(reports recent | reports search X)${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}intel${_EV_RESET}    ${_EV_BOLD}2300${_EV_RESET}  ${_EV_SILVER_DIM}Intel Center      ${_EV_RESET}${_EV_DIM}(intel api | intel docs)${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}apps${_EV_RESET}     ${_EV_BOLD}2400${_EV_RESET}  ${_EV_SILVER_DIM}Alley Kingz       ${_EV_RESET}${_EV_DIM}(apps ak)${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}health${_EV_RESET}   ${_EV_BOLD}2500${_EV_RESET}  ${_EV_SILVER_DIM}MMA Fight Camp    ${_EV_RESET}${_EV_DIM}(health fit)${_EV_RESET}"
    _ev_row "${_EV_BOLD}${_EV_GOLD}memory${_EV_RESET}   ${_EV_BOLD}2700${_EV_RESET}  ${_EV_SILVER_DIM}Blinko + Lucrex   ${_EV_RESET}${_EV_DIM}(memory lucrex | memory mcp)${_EV_RESET}"
    _ev_row ""
    _ev_row "${_EV_SILVER_DIM}${_EV_RESET}${_EV_GOLD}links${_EV_RESET}${_EV_SILVER_DIM} = url list   ${_EV_RESET}${_EV_GOLD}menu${_EV_RESET}${_EV_SILVER_DIM} = reprint this   ${_EV_RESET}${_EV_GOLD}palette${_EV_RESET}${_EV_SILVER_DIM} = color test${_EV_RESET}"
    _ev_spine

    # Host-local extras: only shown if that host defined them.
    local _extra=""
    (( $+aliases[jarvis] ))  && _extra+="${_EV_BOLD}${_EV_GOLD}jarvis${_EV_RESET} ${_EV_SILVER_DIM}stack health${_EV_RESET}  "
    (( $+aliases[md] ))      && _extra+="${_EV_BOLD}${_EV_GOLD}md${_EV_RESET} ${_EV_SILVER_DIM}media hub${_EV_RESET}  "
    (( $+aliases[hm] ))      && _extra+="${_EV_BOLD}${_EV_GOLD}hm${_EV_RESET} ${_EV_SILVER_DIM}homarr${_EV_RESET}  "
    (( $+functions[wsm] ))   && _extra+="${_EV_BOLD}${_EV_GOLD}wsm${_EV_RESET} ${_EV_SILVER_DIM}kde workspace${_EV_RESET}  "
    (( $+aliases[keys] ))    && _extra+="${_EV_BOLD}${_EV_GOLD}keys${_EV_RESET} ${_EV_SILVER_DIM}cheats${_EV_RESET}  "
    if [[ -n "$_extra" ]]; then
        _ev_section "THIS MACHINE" "🖧"
        _ev_row "$_extra"
        _ev_spine
    fi

    printf "%b\n" "  ${_EV_GOLD}╰─${_EV_RESET} ${_EV_GOLD_HOT}⚡ ready${_EV_RESET}"
    echo ""
}

menu() { _ev_print_banner; }

# ============================================================
# GUARDED ALIASES  --  host definitions always win
# ============================================================
_ev_alias cdw   "cd $EL_HOME"
_ev_alias drive "cd $EL_HOME"
_ev_alias ev    "cd $EL_HOME/01_BUSINESSES/Everlight_Ventures"
_ev_alias content "cd $EL_HOME/02_CONTENT_FACTORY"
_ev_alias auto  "cd $EL_HOME/03_AUTOMATION_CORE"
_ev_alias media "cd $EL_HOME/04_MEDIA_LIBRARY"
_ev_alias dev   "cd $EL_HOME/06_DEVELOPMENT"
_ev_alias dash  "cd $EL_HOME/09_DASHBOARD"
_ev_alias dashboards "menu"

# ============================================================
# BANNER ON INTERACTIVE OPEN
# Set EV_NO_BANNER=1 to suppress. Guarded so nested shells
# (tmux panes, exec zsh, Claude Bash calls) stay quiet.
# ============================================================
if [[ -o interactive && -t 1 && -z "${EV_BANNER_SHOWN:-}" && -z "${EV_NO_BANNER:-}" ]]; then
    export EV_BANNER_SHOWN=1
    _ev_print_banner
fi
