#!/usr/bin/env sh
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

# Launch Chromium in full-screen mode, pointing to mmu.ooo
chromium-browser https://mmu.ooo \
  --start-fullscreen \
  --kiosk \
  --incognito \
  --noerrdialogs \
  --disable-translate \
  --no-first-run \
  --fast \
  --fast-start \
  --disable-infobars \
  --disable-features=TranslateUI \
  --disk-cache-dir=/dev/null \
  --overscroll-history-navigation=0 \
  --disable-pinch