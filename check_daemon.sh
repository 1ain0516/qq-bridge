#!/bin/bash
PID_FILE="$HOME/qq-bridge/napcat_data/daemon.pid"
DAEMON_CMD='"/c/Program Files/Python314/python" $HOME/qq-bridge/qq_daemon.py'

# Check if daemon is actually running
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE" 2>/dev/null)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    exit 0
  fi
  # Stale PID file
  rm -f "$PID_FILE"
fi

# Restart
sleep 1
eval "$DAEMON_CMD" &
sleep 2
exit 0
