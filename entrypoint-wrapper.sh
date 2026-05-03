#!/bin/bash
# Start relay in background, then run original entrypoint
cd /app
python3 /app/relay.py &
exec bash /app/entrypoint.sh
