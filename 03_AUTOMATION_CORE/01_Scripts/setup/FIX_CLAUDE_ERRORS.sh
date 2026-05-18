#!/bin/bash
# CLAUDE CLI REPAIR SCRIPT
# This script addresses "dual instance" and "billing/session" errors.

echo "🔥 IT FIRE TEAM: Starting Claude CLI Repair..."

# 1. Kill any orphaned Claude processes
echo "Checking for running Claude processes..."
PIDS=$(ps aux | grep -i "claude" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Killing processes: $PIDS"
    kill -9 $PIDS 2>/dev/null
else
    echo "No orphaned Claude processes found."
fi

# 2. Clear lock files
echo "Clearing lock files..."
# Check common locations
LOCK_FILES=$(find /home/richgee/.claude/ -name "*.lock" 2>/dev/null)
if [ -n "$LOCK_FILES" ]; then
    echo "Removing lock files: $LOCK_FILES"
    rm -f $LOCK_FILES
fi

# Check tmp locks
if [ -d "/tmp/claude-1000" ]; then
    echo "Cleaning up /tmp/claude-1000/..."
    rm -rf /tmp/claude-1000/*
fi

# 3. Handle session confusion
echo "Checking session status..."
if command -v claude >/dev/null; then
    echo "To resolve 'usage confusion' with the web account, we recommend a fresh login."
    echo "Command to run manually if errors persist: 'claude logout && claude'"
else
    echo "Claude command not found in PATH."
fi

# 4. Check API Key
if [ -f "/AA_MY_DRIVE/.env" ]; then
    echo "Verifying .env keys..."
    if grep -q "LUCREX_ANTHROPIC_KEY" /AA_MY_DRIVE/.env; then
        echo "Note: LUCREX_ANTHROPIC_KEY found. If you get billing errors, ensure this key is active at console.anthropic.com"
    fi
fi

echo "✅ Repair attempt complete. Please try running 'cl' or 'claude' now."
