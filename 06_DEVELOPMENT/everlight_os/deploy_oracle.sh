#!/bin/bash
# ===========================================================================
# Everlight Ventures -- Oracle Cloud Master Deployment Script
# ===========================================================================
#
# Deploys all services to Oracle ARM64 free tier VM:
#   - n8n (workflow automation) -- port 5678
#   - Netdata (server monitoring) -- port 19999
#   - Langfuse (AI observability) -- port 3100
#   - Metabase (BI dashboards) -- port 3200
#
# Prerequisites:
#   - SSH access to Oracle VM
#   - Docker + Docker Compose v2 installed on VM
#   - Ports 5678, 19999, 3100, 3200 open in OCI security list
#
# Usage:
#   ./deploy_oracle.sh              # Deploy all services
#   ./deploy_oracle.sh n8n          # Deploy only n8n
#   ./deploy_oracle.sh netdata      # Deploy only Netdata
#   ./deploy_oracle.sh langfuse     # Deploy only Langfuse
#   ./deploy_oracle.sh metabase     # Deploy only Metabase
#   ./deploy_oracle.sh status       # Check status of all services
#   ./deploy_oracle.sh firewall     # Open required ports
#
# ===========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

# Create shared network if it doesn't exist
ensure_network() {
    if ! docker network inspect everlight >/dev/null 2>&1; then
        log "Creating shared 'everlight' Docker network..."
        docker network create everlight
    fi
}

deploy_service() {
    local service="$1"
    local dir="$SERVICES_DIR/$service"

    if [ ! -f "$dir/docker-compose.yml" ]; then
        err "No docker-compose.yml found in $dir"
        return 1
    fi

    log "Deploying $service..."
    cd "$dir"
    docker compose pull
    docker compose up -d
    log "$service deployed successfully!"
}

stop_service() {
    local service="$1"
    local dir="$SERVICES_DIR/$service"

    if [ ! -f "$dir/docker-compose.yml" ]; then
        err "No docker-compose.yml found in $dir"
        return 1
    fi

    warn "Stopping $service..."
    cd "$dir"
    docker compose down
    log "$service stopped."
}

check_status() {
    log "Service Status:"
    echo ""
    for svc in n8n netdata langfuse metabase blinko; do
        if [ -f "$SERVICES_DIR/$svc/docker-compose.yml" ]; then
            cd "$SERVICES_DIR/$svc"
            local running=$(docker compose ps --format json 2>/dev/null | grep -c '"running"' || echo "0")
            local total=$(docker compose ps --format json 2>/dev/null | wc -l || echo "0")
            if [ "$running" -gt 0 ]; then
                echo -e "  ${GREEN}[UP]${NC}   $svc ($running/$total containers)"
            else
                echo -e "  ${RED}[DOWN]${NC} $svc"
            fi
        fi
    done
    echo ""

    # Port check
    log "Port Availability:"
    for port in 5678 19999 3100 3200 1111; do
        if ss -tlnp 2>/dev/null | grep -q ":$port " || netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            echo -e "  ${GREEN}[OPEN]${NC}  :$port"
        else
            echo -e "  ${RED}[CLOSED]${NC} :$port"
        fi
    done
}

open_firewall() {
    log "Opening firewall ports for Everlight services..."

    # iptables (Oracle Linux / Ubuntu)
    for port in 5678 19999 3100 3200; do
        sudo iptables -I INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || true
        log "  Opened port $port"
    done

    # Save iptables rules
    if command -v netfilter-persistent >/dev/null 2>&1; then
        sudo netfilter-persistent save
    elif [ -f /etc/iptables/rules.v4 ]; then
        sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null
    fi

    warn "IMPORTANT: You also need to add ingress rules in OCI Console:"
    echo "  1. Go to OCI Console -> Networking -> Virtual Cloud Networks"
    echo "  2. Click your VCN -> Security Lists -> Default Security List"
    echo "  3. Add Ingress Rules for TCP ports: 5678, 19999, 3100, 3200"
    echo "  4. Source CIDR: 0.0.0.0/0 (or restrict to your IP)"
}

deploy_all() {
    ensure_network

    log "Deploying ALL Everlight services..."
    echo ""

    deploy_service "netdata"    # Fastest, deploy first for monitoring
    deploy_service "n8n"
    deploy_service "langfuse"
    deploy_service "metabase"

    echo ""
    log "All services deployed!"
    echo ""
    check_status
    echo ""
    log "Access your services:"
    echo "  n8n:      http://<your-oracle-ip>:5678"
    echo "  Netdata:  http://<your-oracle-ip>:19999"
    echo "  Langfuse: http://<your-oracle-ip>:3100"
    echo "  Metabase: http://<your-oracle-ip>:3200"
    echo ""
    warn "Remember to open firewall ports: ./deploy_oracle.sh firewall"
}

# ===========================================================================
# Main
# ===========================================================================

case "${1:-all}" in
    n8n|netdata|langfuse|metabase|blinko)
        ensure_network
        deploy_service "$1"
        ;;
    stop)
        if [ -n "${2:-}" ]; then
            stop_service "$2"
        else
            err "Usage: $0 stop <service>"
        fi
        ;;
    status)
        check_status
        ;;
    firewall)
        open_firewall
        ;;
    all)
        deploy_all
        ;;
    *)
        echo "Usage: $0 {all|n8n|netdata|langfuse|metabase|status|firewall|stop <service>}"
        exit 1
        ;;
esac
