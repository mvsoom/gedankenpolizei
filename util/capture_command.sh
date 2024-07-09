#!/bin/bash
# This script executes a single command string and records the monitor at $DISPLAY and $MONITOR while the command is running.
# After the command finishes, it prompts the user to keep, move to the gallery, or delete the recording.
# Example usage:
# $ ./scripts/capture_command.sh "python -u -m seer.narrate.stream --monitor --jsonl | python -u -m seer.thoughts.stream"
# NOTE: The command string should be quoted to prevent the shell from interpreting special characters!

# Saving logic
SCRIPT_NAME=$(basename "$0" .sh)
OUTPUT_NAME="${SCRIPT_NAME}_$(date +%Y%m%d%H%M%S).mp4"
OUTPUT_FILE="/tmp/$OUTPUT_NAME"

save() {
    echo -n "Keep $OUTPUT_NAME? y(es)/n(o)/g(allery) "
    read -r -n 1 ACTION
    echo

    case $ACTION in
        yes|y)
            mkdir -p assets/keep
            mv "$OUTPUT_FILE" "assets/keep/$(basename "$OUTPUT_FILE")"
            echo "Moved to assets/keep/$(basename "$OUTPUT_FILE")"
            ;;
        gallery|g)
            mkdir -p assets/gallery
            mv "$OUTPUT_FILE" "assets/gallery/$(basename "$OUTPUT_FILE")"
            echo "Moved to assets/gallery/$(basename "$OUTPUT_FILE")"
            ;;
        no|n|*)
            echo "Left file in place at: $OUTPUT_FILE"
            ;;
    esac
}

# Cleanup logic
cleanup_and_save() {
    kill -SIGINT "$RECORD_PID"
    kill -SIGTERM "$CMD_PID" # SIGINT not powerful enough

    wait "$RECORD_PID"
    wait "$CMD_PID"

    save

    exit 0
}

trap cleanup_and_save SIGINT

# Start recording the screen
scripts/capture_monitor.sh -o "$OUTPUT_FILE" >/dev/null 2>&1 &
RECORD_PID=$!

# Execute the command string
bash -c "$*" &
CMD_PID=$!

# Wait for the command to finish
wait $CMD_PID

# Stop recording
kill $RECORD_PID
wait $RECORD_PID

save
