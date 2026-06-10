#!/usr/bin/env bash
# install_oracle_watchdog.sh -- idempotent cron installer for the
# phone-side Oracle reachability watchdog.
#
# Author: Elias Varga (Iron Stack -- Verifier)
#
# Adds a cron entry that runs oracle_reachability_watchdog.py every 5 min.
# Safe to run repeatedly: detects the existing line and refuses to double-add.

set -euo pipefail

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
SCRIPT="${WORKSPACE}/03_AUTOMATION_CORE/01_Scripts/oracle_reachability_watchdog.py"
LOG_DIR="${WORKSPACE}/_logs"
LOG_FILE="${LOG_DIR}/oracle_watchdog_cron.log"

# marker the installer recognizes itself by
MARKER="# oracle_reachability_watchdog -- managed by install_oracle_watchdog.sh"

# every 5 minutes, suppress non-fatal stdout, append stderr to log
CRON_LINE="*/5 * * * * /usr/bin/env python3 ${SCRIPT} >> ${LOG_FILE} 2>&1"

# ── preflight ────────────────────────────────────────────────────────
if [[ ! -f "${SCRIPT}" ]]; then
    echo "[install] ERROR: watchdog script missing at ${SCRIPT}"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "[install] ERROR: python3 not on PATH"
    exit 1
fi

if ! command -v crontab >/dev/null 2>&1; then
    echo "[install] ERROR: crontab not available -- this device cannot host the watchdog cron"
    exit 1
fi

mkdir -p "${LOG_DIR}"
chmod +x "${SCRIPT}" || true

# ── idempotency check ───────────────────────────────────────────────
EXISTING="$(crontab -l 2>/dev/null || true)"
if echo "${EXISTING}" | grep -F -q "${SCRIPT}"; then
    echo "[install] watchdog already installed in crontab -- nothing to do"
    echo "[install] existing entry:"
    echo "${EXISTING}" | grep -F "${SCRIPT}" | sed 's/^/    /'
    exit 0
fi

# ── install ──────────────────────────────────────────────────────────
TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT
{
    if [[ -n "${EXISTING}" ]]; then
        echo "${EXISTING}"
    fi
    echo ""
    echo "${MARKER}"
    echo "${CRON_LINE}"
} > "${TMP}"

crontab "${TMP}"

# ── verify ───────────────────────────────────────────────────────────
echo "[install] cron entry added:"
echo "    ${CRON_LINE}"
echo ""
echo "[install] verifying it landed in crontab..."
if crontab -l 2>/dev/null | grep -F -q "${SCRIPT}"; then
    echo "[install] verified -- watchdog will run every 5 min"
else
    echo "[install] WARNING: post-install verify failed"
    exit 1
fi

# kick off one immediate run so we have a baseline observation in the log
echo "[install] running one priming probe now..."
/usr/bin/env python3 "${SCRIPT}" || true
echo "[install] priming probe complete -- check log:"
echo "    ${LOG_FILE}"
echo "    ${LOG_DIR}/oracle_watchdog.log"

echo ""
echo "[install] done. To uninstall: crontab -l | grep -v '${SCRIPT}' | crontab -"
