#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/../../06_DEVELOPMENT/everlight_os/deploy_oracle_observability.sh"

echo "Deploying bot-host observability footprint..."
OBS_PROFILE=bot "$DEPLOY_SCRIPT" netdata

echo "Deploying core-host tracing footprint..."
OBS_PROFILE=core "$DEPLOY_SCRIPT" langfuse

echo "Observability topology deployment finished."
