#!/bin/bash
# morning_brief.sh - Everlight Daily Startup Routine
# Owner: 02_ops_deputy
# Run: 9:00 AM PT daily (cron), or manually: bash morning_brief.sh
#
# What it does:
#   1. Prints current date/time in PT
#   2. Shows pending + active tasks from task queue
#   3. Checks staging inbox for unprocessed files
#   4. Shows last 5 hive session summaries
#   5. Prints today's cadence reminders
#   6. Optionally broadcasts to war room tmux session

BASE="${EVERLIGHT_BASE:-/mnt/sdcard/AA_MY_DRIVE}"
QUEUE="$BASE/_logs/task_queue.jsonl"
INBOX="$BASE/07_STAGING/Inbox"
HIVE_LOG="$BASE/_logs/hive_sessions.jsonl"
BRIEF_LOG="$BASE/_logs/daily_briefs.jsonl"

PT_DATE=$(TZ="America/Los_Angeles" date "+%A, %B %d %Y - %I:%M %p PT")
DAY_OF_WEEK=$(TZ="America/Los_Angeles" date "+%A")

divider() { printf '%0.s-' {1..60}; echo; }

log_brief() {
    mkdir -p "$BASE/_logs"
    echo "{\"ts\":\"$(TZ='America/Los_Angeles' date -Iseconds)\",\"type\":\"morning_brief\",\"day\":\"$DAY_OF_WEEK\"}" >> "$BRIEF_LOG"
}

# ── Header ──────────────────────────────────────────────────────────────────
clear
echo ""
echo "  EVERLIGHT OS - MORNING BRIEF"
echo "  $PT_DATE"
divider

# ── Task Queue Status ────────────────────────────────────────────────────────
echo ""
echo "TASK QUEUE"
if [ -f "$QUEUE" ] && [ -s "$QUEUE" ]; then
    PENDING=$(grep -c '"status": "pending"' "$QUEUE" 2>/dev/null; true)
    ACTIVE=$(grep -c '"status": "active"' "$QUEUE" 2>/dev/null; true)
    BLOCKED=$(grep -c '"status": "blocked"' "$QUEUE" 2>/dev/null; true)
    PENDING=${PENDING:-0}
    ACTIVE=${ACTIVE:-0}
    BLOCKED=${BLOCKED:-0}
    echo "  Pending: $PENDING  |  Active: $ACTIVE  |  Blocked: $BLOCKED"
    if [ "$BLOCKED" -gt "0" ]; then
        echo ""
        echo "  [!] BLOCKED TASKS (need attention):"
        python3 "$BASE/03_AUTOMATION_CORE/01_Scripts/task_router.py" list --status blocked 2>/dev/null \
            || grep '"status": "blocked"' "$QUEUE" | python3 -c "
import sys, json
for line in sys.stdin:
    t = json.loads(line.strip())
    print(f'  {t[\"task_id\"]:8}  {t[\"description\"][:55]}')
"
    fi
    if [ "$PENDING" -gt "0" ]; then
        echo ""
        echo "  Top pending tasks:"
        python3 "$BASE/03_AUTOMATION_CORE/01_Scripts/task_router.py" run-pending 2>/dev/null | head -30
    fi
else
    echo "  Queue empty. Use: python3 03_AUTOMATION_CORE/01_Scripts/task_router.py route \"your task\""
fi

# ── Staging Inbox ────────────────────────────────────────────────────────────
echo ""
divider
echo "STAGING INBOX"
if [ -d "$INBOX" ]; then
    INBOX_COUNT=$(find "$INBOX" -maxdepth 1 -type f ! -name ".*" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INBOX_COUNT" -gt "0" ]; then
        echo "  [!] $INBOX_COUNT unprocessed file(s) in inbox:"
        find "$INBOX" -maxdepth 1 -type f ! -name ".*" -exec basename {} \; | sed 's/^/    - /'
        echo ""
        echo "  Auto-route with: python3 03_AUTOMATION_CORE/01_Scripts/staging_inbox_watcher.py --once"
    else
        echo "  Inbox clear."
    fi
else
    echo "  Inbox directory not found: $INBOX"
fi

# ── Recent Hive Sessions ─────────────────────────────────────────────────────
echo ""
divider
echo "RECENT HIVE SESSIONS (last 3)"
if [ -f "$HIVE_LOG" ] && [ -s "$HIVE_LOG" ]; then
    tail -3 "$HIVE_LOG" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        s = json.loads(line.strip())
        ts = s.get('ts', s.get('created', 'unknown'))[:16]
        prompt = s.get('prompt', s.get('query', 'unknown'))[:50]
        status = s.get('status', '?')
        print(f'  [{ts}] {status:6}  {prompt}')
    except:
        pass
" 2>/dev/null || echo "  (could not parse sessions log)"
else
    echo "  No hive sessions logged yet."
fi

# ── Today's Cadence ──────────────────────────────────────────────────────────
echo ""
divider
echo "TODAY'S CADENCE ($DAY_OF_WEEK)"
echo "  09:00 PT - Perplexity scouts post trend digests to #ai-war-room"
echo "  10:00 PT - Chief Operator sets priorities, Ops Deputy assigns tasks"
echo "  14:00 PT - Sync Coordinator checks launch dependencies"
echo "  17:00 PT - EOD status: Status / Next Action / Owner / ETA"
echo ""

case "$DAY_OF_WEEK" in
    Monday)
        echo "  [MONDAY] Set weekly campaign goals (Strategy Director + Showrunner)"
        ;;
    Wednesday)
        echo "  [WEDNESDAY] KPI review - Analytics Auditor presents experiment results"
        echo "  Run: python3 task_router.py route \"Weekly KPI review\" --priority 2"
        ;;
    Friday)
        echo "  [FRIDAY] SOP review - Automation Architect checks workflow health"
        echo "  Run: python3 task_router.py route \"Weekly SOP and workflow review\" --priority 2"
        ;;
esac

# ── Quick Commands ────────────────────────────────────────────────────────────
echo ""
divider
echo "QUICK COMMANDS"
echo "  hive \"query\"                       - Full hive mind deliberation"
echo "  python3 task_router.py route \"task\" - Add task to queue"
echo "  python3 task_router.py list          - List all tasks"
echo "  python3 staging_inbox_watcher.py --once - Route inbox files"
echo "  ws                                   - Open War Room (tmux)"
divider
echo ""

# ── Log this brief ────────────────────────────────────────────────────────────
log_brief

# ── Optionally broadcast to tmux war room ─────────────────────────────────────
if tmux has-session -t everlight_hive 2>/dev/null; then
    echo "  [War Room active - session: everlight_hive]"
fi
