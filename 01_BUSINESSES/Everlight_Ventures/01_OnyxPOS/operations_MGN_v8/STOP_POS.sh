#!/bin/bash
echo "Stopping POS..."
pkill -f "python.*MGN_APP.py" 2>/dev/null
lsof -ti:5000 | xargs kill -9 2>/dev/null
echo "Stopped."
