#!/bin/bash
set -euo pipefail

ORACLE_HOST="${ORACLE_HOST:-163.192.19.196}"
ORACLE_USER="${ORACLE_USER:-opc}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oracle_key.pem}"
WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
OBS_DIR="$WORKSPACE/06_DEVELOPMENT/everlight_os"
REMOTE_BASE="/home/$ORACLE_USER/everlight"
SERVICES=("$@")

if [ ${#SERVICES[@]} -eq 0 ]; then
  SERVICES=(netdata langfuse)
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 -o ServerAliveInterval=5)

ssh_run() {
  ssh "${SSH_OPTS[@]}" "$ORACLE_USER@$ORACLE_HOST" "$@"
}

scp_run() {
  scp "${SSH_OPTS[@]}" "$@"
}

ensure_remote_dirs() {
  ssh_run "mkdir -p '$REMOTE_BASE' '$REMOTE_BASE/netdata' '$REMOTE_BASE/langfuse'"
}

ensure_remote_prereqs() {
  ssh_run "sudo docker network create everlight >/dev/null 2>&1 || true"
}

ensure_langfuse_env() {
  ssh_run "if [ ! -f '$REMOTE_BASE/langfuse/.env' ]; then \
    DB_PASS=\$(openssl rand -hex 16); \
    AUTH_SECRET=\$(openssl rand -hex 32); \
    SALT=\$(openssl rand -hex 32); \
    cat > '$REMOTE_BASE/langfuse/.env' <<EOF
LANGFUSE_DB_PASSWORD=\$DB_PASS
LANGFUSE_SECRET=\$AUTH_SECRET
LANGFUSE_SALT=\$SALT
LANGFUSE_URL=http://$ORACLE_HOST:3100
EOF
  fi"
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
  ssh_run "cd '$REMOTE_BASE/$service' && sudo docker compose --env-file .env pull && sudo docker compose --env-file .env up -d"
}

verify_service() {
  local service="$1"
  local port=""
  case "$service" in
    netdata) port="19999" ;;
    langfuse) port="3100" ;;
  esac

  echo "Verifying $service..."
  ssh_run "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E '$service|NAMES' || true"
  if [ -n "$port" ]; then
    ssh_run "curl -s -o /dev/null -w '$service HTTP %{http_code}\n' http://localhost:$port/ || true"
  fi
}

echo "Testing Oracle connectivity..."
ssh_run "echo 'Oracle SSH OK: ' \$(hostname)"
ensure_remote_dirs
ensure_remote_prereqs

for service in "${SERVICES[@]}"; do
  deploy_service "$service"
done

for service in "${SERVICES[@]}"; do
  verify_service "$service"
done

echo "Observability deployment complete."
