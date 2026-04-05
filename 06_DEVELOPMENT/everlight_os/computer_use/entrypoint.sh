#!/bin/bash
# Start virtual display + window manager + VNC + API server

# Start Xvfb (virtual framebuffer)
Xvfb :99 -screen 0 ${WIDTH}x${HEIGHT}x24 -ac &
sleep 1

# Start window manager
mutter --replace --display=:99 &
sleep 1

# Start panel
tint2 &

# Start VNC server (password-less, localhost only)
x11vnc -display :99 -forever -nopw -listen 127.0.0.1 -rfbport 5900 &

# Start the HTTP API server
exec python3 /app/server.py
