#!/bin/sh
set -eu
umask 077

# One bot worker per container: this sink cannot receive another worker's audio.
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
pulseaudio --daemonize=yes --exit-idle-time=-1 --log-target=stderr
pactl load-module module-null-sink sink_name=kenes rate=48000 channels=2 >/dev/null
pactl set-default-sink kenes
export PULSE_SINK=kenes
export PULSE_SOURCE=kenes.monitor
export PULSE_SERVER="unix:$XDG_RUNTIME_DIR/pulse/native"

Xvfb "$DISPLAY" -screen 0 1280x720x24 -nolisten tcp &
exec "$@"
