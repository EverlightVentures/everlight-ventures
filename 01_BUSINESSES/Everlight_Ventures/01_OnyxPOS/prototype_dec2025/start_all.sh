#!/usr/bin/env bash
#
# OnyxPOS - Start All Services
# Starts backend API, frontend POS app, and marketing site
#

set -e

# Kill any existing processes on our ports
echo "==> Stopping existing dev servers (ports 5000, 3000, 5173)"
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Create logs directory
mkdir -p run_logs

# Start backend
echo "==> Starting backend (port 5000)"
cd backend
if [ -d "venv" ]; then
    nohup venv/bin/python app.py > ../run_logs/backend.log 2>&1 &
else
    nohup python3 app.py > ../run_logs/backend.log 2>&1 &
fi
echo $! > ../run_logs/backend.pid
cd ..

# Start POS frontend
if [ -d "frontend" ]; then
    echo "==> Starting POS frontend (port 3000)"
    cd frontend
    nohup npm run dev > ../run_logs/frontend.log 2>&1 &
    echo $! > ../run_logs/frontend.pid
    cd ..
fi

# Start marketing site
if [ -d "onyxpos-web" ]; then
    echo "==> Starting marketing site (port 5173)"
    cd onyxpos-web
    nohup npm run dev > ../run_logs/onyxpos-web.log 2>&1 &
    echo $! > ../run_logs/onyxpos-web.pid
    cd ..
fi

sleep 2

echo ""
echo "✅ Running:"
echo "  API:        http://localhost:5000"
echo "  POS App:    http://localhost:3000"
echo "  Marketing:  http://localhost:5173"
echo ""
echo "Logs: $(pwd)/run_logs"
