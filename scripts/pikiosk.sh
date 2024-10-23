#!/bin/bash

# Set up a trap to kill all child processes when the script exits or when CTRL-C is pressed
trap "kill 0" EXIT SIGINT

# Start the pipeline in the background
grab/webcam | \
python -m src.fast.narrate \
    --config-file piconfig.yaml \
    --jsonl \
    --output-frames | \
python -m src.raw.stream \
    --config-file piconfig.yaml | \
emit/websocket &

# Start chromium-browser in the foreground
chromium-browser client/pi.html \
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
  --disable-pinch \
  --autoplay-policy=no-user-gesture-required \
  --remote-debugging-port=9222

# When chromium-browser exits, the script exits, triggering the trap which kills all child processes