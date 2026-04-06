#!/bin/bash
# Claude Chat Bridge Guardian -- keeps the bridge alive + tunnel connected
# Runs every 30s, restarts bridge if dead, re-establishes tunnel if broken

BRIDGE_SCRIPT="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_chat_bridge.py"
BRIDGE_PORT=8510
ORACLE_HOST="opc@129.159.38.250"
ORACLE_KEY="/root/.ssh/oracle_key.pem"
LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/claude_bridge_guardian.log"
BRIDGE_LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/claude_bridge.log"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }

# Check bridge health
if curl -s --connect-timeout 3 http://localhost:$BRIDGE_PORT/health > /dev/null 2>&1; then
    : # bridge alive, do nothing
else
    echo "[$(ts)] Bridge DOWN -- restarting" >> "$LOG"
    # Kill any zombie processes
    pkill -f "claude_chat_bridge.py" 2>/dev/null
    sleep 1
    # Restart
    nohup python3 "$BRIDGE_SCRIPT" >> "$BRIDGE_LOG" 2>&1 &
    sleep 3
    if curl -s --connect-timeout 3 http://localhost:$BRIDGE_PORT/health > /dev/null 2>&1; then
        echo "[$(ts)] Bridge RECOVERED (PID $!)" >> "$LOG"
    else
        echo "[$(ts)] Bridge FAILED to restart" >> "$LOG"
    fi
fi

# Check tunnel (can Oracle reach us?)
TUNNEL_ALIVE=$(ssh -F /root/.ssh/config -o ConnectTimeout=5 oracle-bot "curl -s --connect-timeout 3 http://localhost:$BRIDGE_PORT/health 2>/dev/null" 2>/dev/null)
if echo "$TUNNEL_ALIVE" | grep -q '"ok"'; then
    : # tunnel alive
else
    echo "[$(ts)] Tunnel DOWN -- re-establishing" >> "$LOG"
    # Kill old tunnel
    pkill -f "ssh.*-R $BRIDGE_PORT" 2>/dev/null
    sleep 1
    # Re-establish
    ssh -o ConnectTimeout=15 -f -N -R $BRIDGE_PORT:localhost:$BRIDGE_PORT -i "$ORACLE_KEY" "$ORACLE_HOST" 2>/dev/null
    sleep 2
    # Verify
    RETRY=$(ssh -F /root/.ssh/config -o ConnectTimeout=5 oracle-bot "curl -s --connect-timeout 3 http://localhost:$BRIDGE_PORT/health 2>/dev/null" 2>/dev/null)
    if echo "$RETRY" | grep -q '"ok"'; then
        echo "[$(ts)] Tunnel RECOVERED" >> "$LOG"
    else
        echo "[$(ts)] Tunnel FAILED to recover" >> "$LOG"
    fi
fi
