#!/data/data/com.termux/files/usr/bin/bash
# voice_mic_test.sh -- one-shot: is the phone actually delivering mic audio?
# Records 3s two independent ways and prints the level. Non-zero / louder than
# ~-80 dB = mic is LIVE. Exact 0.000000 / -91 dB = device is muting the mic
# (fix: global Mic-access toggle, unplug AR glasses, or free the mic from another app).
# Safe to run repeatedly after each device-side change.
set -u
export PATH=$PATH:/data/data/com.termux/files/usr/bin
PA=/data/data/com.termux/files/usr/bin/pulseaudio
PACTL=/data/data/com.termux/files/usr/bin/pactl
HOME_T=/data/data/com.termux/files/home

# --- Ensure the PulseAudio bridge + mic source are up (idempotent) ---
if ! timeout 3 env PULSE_SERVER=127.0.0.1 "$PACTL" info >/dev/null 2>&1; then
  "$PA" -k 2>/dev/null; pkill -9 pulseaudio 2>/dev/null
  env -u PULSE_SERVER "$PA" --daemonize=yes -n --exit-idle-time=-1 \
    --load="module-aaudio-sink" \
    --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" \
    --log-target="file:/root/pa_diag.log" -v
fi
timeout 10 env PULSE_SERVER=127.0.0.1 "$PACTL" list sources short 2>/dev/null | grep -q OpenSL_ES_source \
  || timeout 10 env PULSE_SERVER=127.0.0.1 "$PACTL" load-module module-sles-source >/dev/null 2>&1
timeout 4 env PULSE_SERVER=127.0.0.1 "$PACTL" set-default-source OpenSL_ES_source 2>/dev/null

echo "############################################################"
echo "#  SPEAK NOW -- recording 3 seconds...                      #"
echo "############################################################"

# --- Path 1: PulseAudio / OpenSL (what Claude Code /voice uses) ---
timeout 8 env PULSE_SERVER=127.0.0.1 rec -q -c 1 -r 16000 -b 16 /root/mic_pa.wav trim 0 3 2>/dev/null
PA_MAX=$(sox /root/mic_pa.wav -n stat 2>&1 | awk -F: '/Maximum amplitude/{gsub(/ /,"",$2);print $2}')

# --- Path 2: Android MediaRecorder (termux-api) ---
termux-microphone-record -f "$HOME_T/mic_api.m4a" -l 3 >/dev/null 2>&1
read -t 5 _ </dev/null 2>/dev/null
termux-microphone-record -q >/dev/null 2>&1
API_DB=$(ffmpeg -hide_banner -i "$HOME_T/mic_api.m4a" -af volumedetect -f null /dev/null 2>&1 \
         | awk -F: '/max_volume/{gsub(/ /,"",$2);print $2}')

echo ""
echo "RESULTS:"
echo "  PulseAudio/OpenSL peak amplitude : ${PA_MAX:-?}   (0.000000 = muted; >0.01 = LIVE)"
echo "  Android MediaRecorder peak volume: ${API_DB:-?}   (-91 dB = muted; louder = LIVE)"
echo ""
if [ "${PA_MAX:-0.000000}" != "0.000000" ]; then
  echo "  ==> MIC IS LIVE. /voice + spacebar push-to-talk are ready to use."
else
  echo "  ==> STILL MUTED at the device. Turn ON global Mic access, unplug AR"
  echo "      glasses, and confirm the mic works in a normal recorder app."
fi
