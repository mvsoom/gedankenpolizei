#!/usr/bin/env sh
# Setup screens and launch gedankenpolizei pi app

# Disable screen blanking and power management
xset -dpms
xset s off
xset s noblank

# Hide the mouse cursor when not in use
unclutter &

# Rotate the SDI-1 screen 90 degrees counterclockwise, set as primary
xrandr --output DSI-1 --primary --rotate left --auto

# Mirror primary to secondary HDMI outputs
xrandr --output HDMI-1 --same-as DSI-1 --auto
xrandr --output HDMI-2 --same-as DSI-1 --auto

# Center secondary HDMI outputs
python center_display.py --primary DSI-1 --secondary HDMI-1
python center_display.py --primary DSI-1 --secondary HDMI-2

# Start script within activated project dir (like dev environment)
cd /home/pi/gedankenpolizei
source .venv/bin/activate
scripts/pikiosk.sh