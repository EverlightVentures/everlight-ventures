# Polymarket Live Trader -- Everlight Ventures
# Real py-clob-client execution. Runs on e5-mother (Ampere ARM64).
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gcc \
    && rm -rf /var/lib/apt/lists/*

# Install deps from the canonical manifest (web3 / eth-account / py-clob-client / feedparser / pyyaml)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole package so absolute imports (from polymarket_agent...) resolve.
# WORKDIR /app is on sys.path; package lives at /app/polymarket_agent (.dockerignore
# trims .venv/data/logs/tests/__pycache__).
COPY . /app/polymarket_agent/

RUN mkdir -p /app/polymarket_agent/logs /app/polymarket_agent/data

# Default: PAPER cycle loop. Live trading requires LIVE_TRADING=true env AND
# config live_trading.enabled=true (two-factor). Switch command to the live
# entrypoint only after paper calibration passes + wallet funded.
CMD ["python3", "-m", "polymarket_agent.main"]
