FROM python:3.11-slim

WORKDIR /app

# System deps + Node.js for claude CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @anthropic-ai/claude-code --quiet && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (cached layer, changes rarely)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire bot (includes vendor/utils/coinbase_api.py)
COPY . /app/

# Create data/logs/secrets dirs
RUN mkdir -p /app/data /app/logs /app/secrets

# Env defaults
ENV COINBASE_CONFIG_PATH=/app/secrets/config.json
ENV XLM_CONFIG_FILE=config.yaml
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles
# AI worker script paths (override phone paths)
ENV CLX_DELEGATE_BIN=/app/vendor/ai_workers/clx_delegate.py
ENV GMX_DELEGATE_BIN=/app/vendor/ai_workers/gemx_delegate.py

EXPOSE 8502

# Health check: main.py writes Unix float timestamp to data/.heartbeat
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python3 -c "import time; from pathlib import Path; \
    hb = Path('/app/data/.heartbeat'); \
    assert hb.exists(), 'no heartbeat'; \
    age = time.time() - float(hb.read_text().strip()); \
    assert age < 180, f'heartbeat stale: {age:.0f}s'" \
    || exit 1

# Default: run bot + dashboard + WS feed
CMD ["bash", "docker-entrypoint.sh"]
