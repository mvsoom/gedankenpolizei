# Use venv Python
PYTHON=$(which python)

# Terminal window's widthxheight
SIZE=300x990

SETTLETIME=2

RUNCMD="$PYTHON -u -m seer.narrate.stream --monitor --jsonl | $PYTHON -u -m seer.thoughts.stream"

FULLCMD="(cd \"$(pwd)\"; clear; sleep $SETTLETIME; $RUNCMD)"

cool-retro-term \
    -geometry ${SIZE}+0+0 \
    --profile "Camera Lucida" \
    -e /bin/bash -c "$FULLCMD" &
term_pid=$!