#!/bin/bash
# ===========================================================================
# Everlight Live Status Viewer
# ===========================================================================
# Watch all automation activity in real time.
#
# Usage:
#   bash live_status.sh           # Live dashboard (updates every 10s)
#   bash live_status.sh log       # Tail the bootstrap log
#   bash live_status.sh oracle    # Watch Oracle Docker containers
# ===========================================================================

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
ORACLE_IP="163.192.19.196"
LOG_FILE="$WORKSPACE/_logs/bootstrap.log"

G='\033[0;32m'
Y='\033[1;33m'
R='\033[0;31m'
B='\033[1;34m'
C='\033[0;36m'
N='\033[0m'

case "${1:-dash}" in
    log)
        echo -e "${B}Tailing bootstrap log. Ctrl+C to stop.${N}"
        tail -f "$LOG_FILE" 2>/dev/null || echo "No log yet. Run bootstrap first."
        ;;
    oracle)
        echo -e "${B}Watching Oracle Docker. Ctrl+C to stop.${N}"
        watch -n 10 "ssh -o ConnectTimeout=10 -o BatchMode=yes -i /root/.ssh/oracle_key.pem -o AddressFamily=inet -o GSSAPIAuthentication=no opc@$ORACLE_IP 'docker ps --format \"table {{.Names}}\t{{.Status}}\t{{.Ports}}\" 2>/dev/null || echo Docker not running'"
        ;;
    dash|*)
        while true; do
            clear
            echo -e "${B}============================================================${N}"
            echo -e "${B}  EVERLIGHT VENTURES -- LIVE STATUS${N}"
            echo -e "${B}  $(date '+%Y-%m-%d %H:%M:%S PT')${N}"
            echo -e "${B}============================================================${N}"
            echo ""

            # Oracle connectivity
            echo -e "${C}ORACLE CLOUD${N}"
            if ssh -o ConnectTimeout=5 -o BatchMode=yes -i /root/.ssh/oracle_key.pem -o AddressFamily=inet -o GSSAPIAuthentication=no opc@$ORACLE_IP "echo ok" >/dev/null 2>&1; then
                echo -e "  ${G}[CONNECTED]${N} $ORACLE_IP"
                # Docker containers
                ssh -o ConnectTimeout=5 -o BatchMode=yes -i /root/.ssh/oracle_key.pem -o AddressFamily=inet -o GSSAPIAuthentication=no opc@$ORACLE_IP "
                    docker ps --format '  {{.Names}}: {{.Status}}' 2>/dev/null || echo '  Docker not installed'
                " 2>/dev/null
            else
                echo -e "  ${R}[OFFLINE]${N} Cannot reach Oracle"
            fi
            echo ""

            # Local services
            echo -e "${C}LOCAL SERVICES${N}"
            if nc -z -w 2 127.0.0.1 8502 2>/dev/null; then
                echo -e "  ${G}[UP]${N}   Django Dashboard :8502"
            else
                echo -e "  ${R}[DOWN]${N} Django Dashboard :8502"
            fi
            echo ""

            # Recent log activity
            echo -e "${C}LAST 5 LOG ENTRIES${N}"
            tail -5 "$LOG_FILE" 2>/dev/null | sed 's/^/  /' || echo "  No log file yet"
            echo ""

            # Google Docs queue
            local queue_count=$(ls "$WORKSPACE/09_DASHBOARD/reports/gdocs_queue/" 2>/dev/null | wc -l)
            echo -e "${C}GOOGLE DOCS QUEUE${N}"
            echo -e "  Pending uploads: $queue_count"
            echo ""

            # Calendar events today
            echo -e "${C}FILES CHANGED (last hour)${N}"
            find "$WORKSPACE/03_AUTOMATION_CORE" -name "*.py" -mmin -60 2>/dev/null | head -5 | sed 's/^/  /' || echo "  None"
            echo ""

            echo -e "${Y}Refreshing in 10s... Ctrl+C to stop${N}"
            sleep 10
        done
        ;;
esac
