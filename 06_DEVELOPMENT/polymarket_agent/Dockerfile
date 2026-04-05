# Polymarket Prediction Agent - Everlight Ventures
# 5-Agent Pipeline on Oracle E5 ARM64
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyyaml

COPY config.yaml .
COPY main.py .

RUN mkdir -p logs data

CMD ["python3", "main.py"]
