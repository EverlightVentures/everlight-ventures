#!/bin/bash
# stop_services.sh -- Gracefully stop Nextcloud stack inside PRoot-Ubuntu

echo "Stopping Apache..."
apache2ctl stop 2>/dev/null || pkill -x apache2 2>/dev/null || true

echo "Stopping MariaDB..."
mysqladmin -u root shutdown 2>/dev/null || pkill -x mysqld 2>/dev/null || true

echo "Stopping ngrok..."
pkill -x ngrok 2>/dev/null || true

echo "All services stopped."
