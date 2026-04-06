#!/bin/bash
set -euo pipefail

OBS_PROFILE="${OBS_PROFILE:-bot}"
BOT_ORACLE_HOST="${BOT_ORACLE_HOST:-163.192.19.196}"
CORE_ORACLE_HOST="${CORE_ORACLE_HOST:-129.159.38.250}"
if [ -z "${ORACLE_HOST:-}" ]; then
  case "$OBS_PROFILE" in
    core|tracing|langfuse)
      ORACLE_HOST="$CORE_ORACLE_HOST"
      ;;
    *)
      ORACLE_HOST="$BOT_ORACLE_HOST"
      ;;
  esac
else
  ORACLE_HOST="$ORACLE_HOST"
fi
ORACLE_USER="${ORACLE_USER:-opc}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oracle_key.pem}"
WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
OBS_DIR="$WORKSPACE/06_DEVELOPMENT/everlight_os"
REMOTE_BASE="/home/$ORACLE_USER/everlight"
SERVICES=("$@")
REMOTE_ENGINE="sudo docker"
REMOTE_COMPOSE="sudo docker compose"

if [ ${#SERVICES[@]} -eq 0 ]; then
  case "$OBS_PROFILE" in
    core|tracing|langfuse)
      SERVICES=(langfuse)
      ;;
    *)
      # The free-tier XLM bot host is only 1 GB RAM. Keep this host lean.
      SERVICES=(netdata)
      if [ "${DEPLOY_LANGFUSE:-0}" = "1" ]; then
        SERVICES+=(langfuse)
      fi
      ;;
  esac
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 -o ServerAliveInterval=5)

ssh_run() {
  ssh "${SSH_OPTS[@]}" "$ORACLE_USER@$ORACLE_HOST" "$@"
}

scp_run() {
  scp "${SSH_OPTS[@]}" "$@"
}

detect_remote_runtime() {
  local runtime=""
  runtime="$(ssh_run "if command -v docker >/dev/null 2>&1 && sudo docker compose version >/dev/null 2>&1; then echo docker; elif command -v podman-compose >/dev/null 2>&1; then printf 'podman-compose:%s\n' \"\$(command -v podman-compose)\"; else echo missing; fi" | tail -n 1)"
  case "$runtime" in
    docker)
      REMOTE_ENGINE="sudo docker"
      REMOTE_COMPOSE="sudo docker compose"
      ;;
    podman-compose:*)
      REMOTE_ENGINE="sudo podman"
      REMOTE_COMPOSE="sudo ${runtime#podman-compose:}"
      ;;
    *)
      REMOTE_ENGINE=""
      REMOTE_COMPOSE=""
      ;;
  esac
  [ -n "$REMOTE_ENGINE" ]
}

ensure_remote_runtime() {
  if detect_remote_runtime; then
    echo "Remote container runtime ready: $REMOTE_ENGINE"
    return 0
  fi

  echo "Bootstrapping native Oracle Linux container runtime..."
  ssh_run "if [ -f /tmp/everlight_runtime_bootstrap.pid ] && kill -0 \$(cat /tmp/everlight_runtime_bootstrap.pid) >/dev/null 2>&1; then echo 'runtime install already in progress'; exit 0; fi; nohup sudo sh -lc 'dnf -y install podman podman-docker python3-pip >/tmp/everlight_runtime_install.log 2>&1 && if ! command -v podman-compose >/dev/null 2>&1; then python3 -m pip install --upgrade pip >>/tmp/everlight_runtime_install.log 2>&1 && python3 -m pip install podman-compose >>/tmp/everlight_runtime_install.log 2>&1; fi' >/tmp/everlight_runtime_bootstrap.out 2>&1 < /dev/null & echo \$! >/tmp/everlight_runtime_bootstrap.pid; echo 'started runtime bootstrap'" || return 1

  for _ in $(seq 1 20); do
    sleep 10
    if detect_remote_runtime; then
      echo "Remote container runtime became ready: $REMOTE_ENGINE"
      return 0
    fi
    ssh_run "tail -n 5 /tmp/everlight_runtime_install.log 2>/dev/null || true" >/dev/null 2>&1 || true
  done

  echo "Runtime bootstrap did not finish within the wait window."
  echo "Check /tmp/everlight_runtime_install.log on the Oracle host."
  return 1
}

ensure_remote_dirs() {
  ssh_run "mkdir -p '$REMOTE_BASE' '$REMOTE_BASE/netdata' '$REMOTE_BASE/langfuse'"
}

ensure_remote_prereqs() {
  ssh_run "$REMOTE_ENGINE network create everlight >/dev/null 2>&1 || true"
}

ensure_langfuse_env() {
  ssh_run "ENV_FILE='$REMOTE_BASE/langfuse/.env'; \
    if [ -f \"\$ENV_FILE\" ]; then . \"\$ENV_FILE\"; fi; \
    DB_PASS=\${POSTGRES_PASSWORD:-\${LANGFUSE_DB_PASSWORD:-\$(openssl rand -hex 16)}}; \
    CLICKHOUSE_PASS=\${CLICKHOUSE_PASSWORD:-\$(openssl rand -hex 16)}; \
    REDIS_PASS=\${REDIS_AUTH:-\$(openssl rand -hex 16)}; \
    MINIO_PASS=\${MINIO_ROOT_PASSWORD:-\$(openssl rand -hex 16)}; \
    NEXTAUTH_SECRET_VAL=\${NEXTAUTH_SECRET:-\${LANGFUSE_SECRET:-\$(openssl rand -hex 32)}}; \
    SALT_VAL=\${SALT:-\${LANGFUSE_SALT:-\$(openssl rand -hex 32)}}; \
    ENCRYPTION_KEY_VAL=\${ENCRYPTION_KEY:-\$(openssl rand -hex 32)}; \
    cat > \"\$ENV_FILE\" <<EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=\$DB_PASS
POSTGRES_DB=postgres
DATABASE_URL=postgresql://postgres:\$DB_PASS@postgres:5432/postgres
NEXTAUTH_URL=http://$ORACLE_HOST:3100
NEXTAUTH_SECRET=\$NEXTAUTH_SECRET_VAL
SALT=\$SALT_VAL
ENCRYPTION_KEY=\$ENCRYPTION_KEY_VAL
CLICKHOUSE_USER=clickhouse
CLICKHOUSE_PASSWORD=\$CLICKHOUSE_PASS
CLICKHOUSE_MIGRATION_URL=clickhouse://clickhouse:9000
CLICKHOUSE_URL=http://clickhouse:8123
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_AUTH=\$REDIS_PASS
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=\$MINIO_PASS
LANGFUSE_S3_EVENT_UPLOAD_BUCKET=langfuse
LANGFUSE_S3_EVENT_UPLOAD_REGION=auto
LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID=minio
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=\$MINIO_PASS
LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT=http://minio:9000
LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE=true
LANGFUSE_S3_EVENT_UPLOAD_PREFIX=events/
LANGFUSE_S3_MEDIA_UPLOAD_BUCKET=langfuse
LANGFUSE_S3_MEDIA_UPLOAD_REGION=auto
LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID=minio
LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY=\$MINIO_PASS
LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT=http://minio:9000
LANGFUSE_S3_MEDIA_UPLOAD_FORCE_PATH_STYLE=true
LANGFUSE_S3_MEDIA_UPLOAD_PREFIX=media/
LANGFUSE_S3_BATCH_EXPORT_ENABLED=false
LANGFUSE_S3_BATCH_EXPORT_BUCKET=langfuse
LANGFUSE_S3_BATCH_EXPORT_PREFIX=exports/
LANGFUSE_S3_BATCH_EXPORT_REGION=auto
LANGFUSE_S3_BATCH_EXPORT_ENDPOINT=http://minio:9000
LANGFUSE_S3_BATCH_EXPORT_EXTERNAL_ENDPOINT=http://$ORACLE_HOST:9090
LANGFUSE_S3_BATCH_EXPORT_ACCESS_KEY_ID=minio
LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY=\$MINIO_PASS
LANGFUSE_S3_BATCH_EXPORT_FORCE_PATH_STYLE=true
TELEMETRY_ENABLED=false
LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=false
EOF"
}

ensure_netdata_env() {
  ssh_run "if [ ! -f '$REMOTE_BASE/netdata/.env' ]; then \
    cat > '$REMOTE_BASE/netdata/.env' <<EOF
TZ=America/Los_Angeles
NETDATA_CLAIM_TOKEN=
NETDATA_CLAIM_URL=https://app.netdata.cloud
EOF
  fi"
}

deploy_service() {
  local service="$1"
  local source_dir="$OBS_DIR/$service"
  if [ ! -f "$source_dir/docker-compose.yml" ]; then
    echo "Missing docker-compose.yml for $service"
    exit 1
  fi

  echo "Uploading $service assets..."
  scp_run "$source_dir/docker-compose.yml" "$ORACLE_USER@$ORACLE_HOST:$REMOTE_BASE/$service/docker-compose.yml"
  if [ -f "$source_dir/.env.example" ]; then
    scp_run "$source_dir/.env.example" "$ORACLE_USER@$ORACLE_HOST:$REMOTE_BASE/$service/.env.example"
  fi
  if [ -f "$source_dir/README.md" ]; then
    scp_run "$source_dir/README.md" "$ORACLE_USER@$ORACLE_HOST:$REMOTE_BASE/$service/README.md"
  fi

  if [ "$service" = "langfuse" ]; then
    ensure_langfuse_env
  fi
  if [ "$service" = "netdata" ]; then
    ensure_netdata_env
  fi

  echo "Deploying $service..."
  ssh_run "cd '$REMOTE_BASE/$service' && $REMOTE_COMPOSE --env-file .env pull && $REMOTE_COMPOSE --env-file .env up -d"
}

verify_service() {
  local service="$1"
  local port=""
  case "$service" in
    netdata) port="19999" ;;
    langfuse) port="3100" ;;
  esac

  echo "Verifying $service..."
  ssh_run "$REMOTE_ENGINE ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E '$service|NAMES' || true"
  if [ -n "$port" ]; then
    ssh_run "curl -s -o /dev/null -w '$service HTTP %{http_code}\n' http://localhost:$port/ || true"
  fi
}

echo "Testing Oracle connectivity..."
ssh_run "echo 'Oracle SSH OK:' \$(hostname) 'profile=$OBS_PROFILE host=$ORACLE_HOST'"
ensure_remote_runtime
ensure_remote_dirs
ensure_remote_prereqs

for service in "${SERVICES[@]}"; do
  deploy_service "$service"
done

for service in "${SERVICES[@]}"; do
  verify_service "$service"
done

echo "Observability deployment complete."
