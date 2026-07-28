#!/data/data/com.termux/files/usr/bin/bash
# voice_audio_bridge.sh -- bring up the PulseAudio mic+playback bridge that
# Claude Code /voice (SoX `rec`/`play`) needs from inside proot Debian/Ubuntu.
#
# DEVICE-LOCAL ONLY. Do NOT deploy to Oracle/e5 -- those are headless servers
# with no microphone. This wires the phone's mic through to proot.
#
# Architecture:
#   Android mic --OpenSL ES--> pulseaudio (module-sles-source)
#                              pulseaudio (module-aaudio-sink) --> Android speaker
#                              pulseaudio (module-native-protocol-tcp @127.0.0.1:4713)
#   proot SoX `rec`/`play`  --TCP--> pulseaudio   (via PULSE_SERVER=127.0.0.1)
#
# Prereq (one-time, manual on device): grant Termux the Microphone permission
#   Settings > Apps > Termux > Permissions > Microphone > Allow
# Without it, module-sles-source fails with "OpenSL ES: error 9".

set -u
PA=/data/data/com.termux/files/usr/bin/pulseaudio
PACTL=/data/data/com.termux/files/usr/bin/pactl
LOG=/root/pa_diag.log

echo "[voice-bridge] stopping any stale daemon..."
"$PA" -k 2>/dev/null

echo "[voice-bridge] starting daemon (skip default.pa, load explicit modules)..."
# PULSE_SERVER must be UNSET for the daemon, or it refuses to start (thinks it's a client).
env -u PULSE_SERVER "$PA" --daemonize=yes -n --exit-idle-time=-1 \
  --load="module-aaudio-sink" \
  --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" \
  --log-target="file:$LOG" -v

# Add the microphone source separately so a permission failure can't kill the daemon.
if PULSE_SERVER=127.0.0.1 "$PACTL" load-module module-sles-source >/dev/null 2>&1; then
  echo "[voice-bridge] microphone source loaded OK."
else
  echo "[voice-bridge] WARNING: module-sles-source failed to load."
  echo "[voice-bridge] -> Grant Termux the Microphone permission, then re-run this script."
fi

echo "[voice-bridge] sources (need a real mic, not just *.monitor):"
PULSE_SERVER=127.0.0.1 "$PACTL" list sources short 2>&1

echo "[voice-bridge] done. Clients use PULSE_SERVER=127.0.0.1"
