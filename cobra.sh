!/bin/bash

# Start CobraPinger in continuous mode and launch the web interface.

PINGER_SCRIPT="cobrapinger.py"
WEB_SCRIPT="./web_nonprod.sh"

# Start the pinger
python3 "$PINGER_SCRIPT" --auto &
PINGER_PID=$!

# Start the web application
"$WEB_SCRIPT" &
WEB_PID=$!

trap "kill $PINGER_PID $WEB_PID" SIGINT SIGTERM

wait $PINGER_PID $WEB_PID
