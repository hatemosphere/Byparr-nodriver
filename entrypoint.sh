#!/bin/bash

echo "Starting Byparr with:"
echo "  USE_XVFB=$USE_XVFB"
echo "  USE_HEADLESS=$USE_HEADLESS"
echo "  LOG_LEVEL=$LOG_LEVEL"

# If USE_XVFB is set and we're not running headless, start Xvfb
if [[ "$USE_XVFB" == "true" || "$USE_XVFB" == "1" ]] && [[ "$USE_HEADLESS" != "true" && "$USE_HEADLESS" != "1" ]]; then
    echo "Starting Xvfb for non-headless mode..."
    Xvfb :99 -screen 0 1920x1080x24 -ac &
    export DISPLAY=:99
    
    # Wait for Xvfb to start
    sleep 2
    echo "Xvfb started on display :99"
fi

# Run the application
echo "Starting application..."
exec uv run python -u main.py