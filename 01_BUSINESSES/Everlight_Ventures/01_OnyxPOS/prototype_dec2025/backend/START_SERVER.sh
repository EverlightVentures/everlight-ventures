#!/bin/bash

cd "$(dirname "$0")"

echo "Starting OnyxPOS Backend..."

# Check if already running
if pgrep -f "python3 app.py" > /dev/null; then
    echo "✅ Server is already running on http://localhost:5000"
    exit 0
fi

# Start server
./venv/bin/python3 app.py > /tmp/onyxpos.log 2>&1 &

# Wait for server to start
sleep 3

# Test if server is up
if curl -s http://localhost:5000/health > /dev/null; then
    echo "✅ OnyxPOS Backend is running!"
    echo ""
    echo "API: http://localhost:5000"
    echo "Health: http://localhost:5000/health"
    echo ""
    echo "Logs: tail -f /tmp/onyxpos.log"
    echo "Stop: pkill -f 'python3 app.py'"
else
    echo "❌ Failed to start server. Check logs: tail /tmp/onyxpos.log"
    exit 1
fi
