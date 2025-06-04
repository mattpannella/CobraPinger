#!/bin/bash

# Path to your script (adjust as needed)
SCRIPT_PATH="/cobra/cobrapingerTEST.py"

# Log file just for restarts
LOG_FILE="/cobra/cobrapinger_restart.log"

# Delay before restart (seconds)
RESTART_DELAY=5

echo "Starting COBRAPINGER in auto mode..."

while true
do
    echo "[$(date)] COBRAPINGER starting..." >> "$LOG_FILE"
    
    # Run Python script and show output live in terminal
    python3 "$SCRIPT_PATH" --auto