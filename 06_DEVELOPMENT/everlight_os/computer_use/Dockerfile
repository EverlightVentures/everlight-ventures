# Computer Use Agent - Headless Linux Desktop for Claude API
# Based on Anthropic's reference implementation, adapted for ARM64/Podman
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV WIDTH=1280
ENV HEIGHT=720

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    mutter \
    tint2 \
    xdotool \
    scrot \
    imagemagick \
    firefox-esr \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .
COPY server.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Data directories
RUN mkdir -p /app/data /app/screenshots

EXPOSE 8501 5900

ENTRYPOINT ["/app/entrypoint.sh"]
