#!/bin/bash

# Start Xvfb
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -nolisten unix &
sleep 2

# Start the application
exec uv run main.py
