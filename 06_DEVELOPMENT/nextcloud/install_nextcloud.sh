#!/bin/bash
# =============================================================================
# Nextcloud Install Script -- Run INSIDE PRoot-Ubuntu
# Everlight Node: Mobile-01 | Samsung Z Fold / Termux / PRoot-Distro
#
# Usage: Run this after entering PRoot:
#   proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard -- bash \
#     /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/install_nextcloud.sh
#
# Installs: Apache2 (port 8080) + MariaDB + PHP + Nextcloud
# Data dir:  /mnt/sdcard/AA_MY_DRIVE/.system/nextcloud_data
# =============================================================================

set -e

NC_DATA_DIR="/mnt/sdcard/AA_MY_DRIVE/.system/nextcloud_data"
NC_WEB_DIR="/var/www/nextcloud"
NC_LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud"
NC_PORT="8080"
NC_DB="nextcloud"
NC_DB_USER="nextcloud"
# CHANGE THIS before running
NC_DB_PASS="changeme_secure_password_here"

echo ""
echo "========================================"
echo "  Nextcloud Install -- Everlight Mobile-01"
echo "========================================"
echo ""

# ---- Phase 1: Dependencies --------------------------------------------------
echo "[1/6] Installing dependencies..."
apt-get update -qq
apt-get install -y \
    apache2 \
    mariadb-server \
    php \
    libapache2-mod-php \
    php-mysql \
    php-gd \
    php-json \
    php-curl \
    php-mbstring \
    php-intl \
    php-imagick \
    php-xml \
    php-zip \
    php-bz2 \
    php-apcu \
    php-bcmath \
    php-gmp \
    wget \
    unzip \
    curl \
    2>/dev/null

echo "  [OK] Dependencies installed."

# ---- Phase 2: Apache config -------------------------------------------------
echo "[2/6] Configuring Apache on port $NC_PORT..."

# Change port from 80 to 8080
sed -i 's/^Listen 80$/Listen 8080/' /etc/apache2/ports.conf 2>/dev/null || true
sed -i 's/<VirtualHost \*:80>/<VirtualHost *:8080>/' \
    /etc/apache2/sites-enabled/000-default.conf 2>/dev/null || true

# In PRoot, www-data cannot write sdcard; run Apache as root
# (PRoot root = Termux user on the outside -- no actual privilege escalation)
sed -i 's/^export APACHE_RUN_USER=www-data/export APACHE_RUN_USER=root/' \
    /etc/apache2/envvars
sed -i 's/^export APACHE_RUN_GROUP=www-data/export APACHE_RUN_GROUP=root/' \
    /etc/apache2/envvars

# Enable required modules
a2enmod rewrite headers env dir mime 2>/dev/null || true

# Write Nextcloud VirtualHost
cat > /etc/apache2/sites-available/nextcloud.conf << 'APACHECONF'
<VirtualHost *:8080>
    DocumentRoot /var/www/nextcloud/
    ServerName localhost

    <Directory /var/www/nextcloud/>
        Require all granted
        AllowOverride All
        Options FollowSymLinks MultiViews
        <IfModule mod_dav.c>
            Dav off
        </IfModule>
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/nextcloud_error.log
    CustomLog ${APACHE_LOG_DIR}/nextcloud_access.log combined
</VirtualHost>
APACHECONF

a2dissite 000-default.conf 2>/dev/null || true
a2ensite nextcloud.conf 2>/dev/null || true

# PHP settings optimized for Nextcloud
PHP_INI=$(php --ini | grep "Loaded Configuration" | awk '{print $NF}')
if [ -f "$PHP_INI" ]; then
    sed -i 's/^memory_limit = .*/memory_limit = 512M/'          "$PHP_INI"
    sed -i 's/^upload_max_filesize = .*/upload_max_filesize = 1G/' "$PHP_INI"
    sed -i 's/^post_max_size = .*/post_max_size = 1G/'           "$PHP_INI"
    sed -i 's/^max_execution_time = .*/max_execution_time = 300/' "$PHP_INI"
fi

echo "  [OK] Apache configured on port $NC_PORT."

# ---- Phase 3: MariaDB setup -------------------------------------------------
echo "[3/6] Configuring MariaDB..."

# Start MariaDB without systemctl (PRoot has no init system)
mysqld_safe --user=root --skip-networking=0 --daemonize 2>/dev/null || true
sleep 3

mysql -u root 2>/dev/null <<SQLEOF
CREATE DATABASE IF NOT EXISTS \`${NC_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS '${NC_DB_USER}'@'localhost' IDENTIFIED BY '${NC_DB_PASS}';
GRANT ALL PRIVILEGES ON \`${NC_DB}\`.* TO '${NC_DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

echo "  [OK] MariaDB configured. DB: $NC_DB / User: $NC_DB_USER"

# ---- Phase 4: Download Nextcloud --------------------------------------------
echo "[4/6] Downloading Nextcloud..."
cd /tmp

NC_VERSION="30.0.0"
NC_URL="https://download.nextcloud.com/server/releases/nextcloud-${NC_VERSION}.tar.bz2"
echo "  Fetching Nextcloud $NC_VERSION..."
wget -q --show-progress -O nextcloud.tar.bz2 "$NC_URL" 2>&1 || {
    echo "  Trying latest release..."
    wget -q --show-progress -O nextcloud.tar.bz2 \
        "https://download.nextcloud.com/server/releases/latest.tar.bz2"
}

echo "  Extracting..."
tar -xjf nextcloud.tar.bz2

if [ -d "$NC_WEB_DIR" ]; then
    rm -rf "${NC_WEB_DIR}.bak"
    mv "$NC_WEB_DIR" "${NC_WEB_DIR}.bak"
fi
mv nextcloud "$NC_WEB_DIR"
rm -f nextcloud.tar.bz2

chown -R root:root "$NC_WEB_DIR"
chmod -R 755 "$NC_WEB_DIR"

echo "  [OK] Nextcloud extracted to $NC_WEB_DIR"

# ---- Phase 5: Data directory ------------------------------------------------
echo "[5/6] Setting up data directory..."
mkdir -p "$NC_DATA_DIR"
mkdir -p "$NC_LOG_DIR"
chmod 750 "$NC_DATA_DIR"
echo "  [OK] Data dir: $NC_DATA_DIR"

# ---- Phase 6: OCC install (command-line Nextcloud installer) ----------------
echo "[6/6] Running Nextcloud occ installer..."
PHONE_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' \
    || hostname -I | awk '{print $1}')

echo ""
echo "  Enter Nextcloud admin password (used for web login):"
read -r -s NC_ADMIN_PASS
echo ""

cd "$NC_WEB_DIR"
php occ maintenance:install \
    --database="mysql" \
    --database-host="localhost" \
    --database-name="$NC_DB" \
    --database-user="$NC_DB_USER" \
    --database-pass="$NC_DB_PASS" \
    --admin-user="admin" \
    --admin-pass="$NC_ADMIN_PASS" \
    --data-dir="$NC_DATA_DIR"

# Trusted domains: LAN + ngrok wildcard
php occ config:system:set trusted_domains 0 --value="localhost"
php occ config:system:set trusted_domains 1 --value="$PHONE_IP"
php occ config:system:set trusted_domains 2 --value="*.ngrok-free.app"
php occ config:system:set trusted_domains 3 --value="*.ngrok.io"

# Performance + logging
php occ config:system:set default_phone_region --value="US"
php occ config:system:set filelocking.enabled --value=true --type=boolean
php occ config:system:set memcache.local --value='\OC\Memcache\APCu'
php occ config:system:set logfile --value="$NC_LOG_DIR/nextcloud.log"
php occ config:system:set loglevel --value=2 --type=integer
php occ config:system:set overwriteprotocol --value="https"
php occ config:system:set overwrite.cli.url --value="http://${PHONE_IP}:8080"

# Use cron for background jobs
php occ background:cron

echo ""
echo "========================================"
echo "  INSTALL COMPLETE"
echo "========================================"
echo "  LAN URL:   http://${PHONE_IP}:${NC_PORT}"
echo "  Local URL: http://localhost:${NC_PORT}"
echo "  Admin:     admin"
echo "  Data dir:  $NC_DATA_DIR"
echo "  Logs:      $NC_LOG_DIR/nextcloud.log"
echo ""
echo "  Next step: run start_services.sh"
echo "========================================"
