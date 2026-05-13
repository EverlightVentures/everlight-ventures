#!/bin/bash
# Hive Mind Sync (compat shim).
# The real work lives in hive_sync_v2.sh which adds: doctrine compile (Lucrex
# shared-protocol), global agents, plugin skills, command translation, and a
# parity verifier. This shim preserves muscle memory for the old command.
exec "$(dirname "$0")/hive_sync_v2.sh" "$@"
