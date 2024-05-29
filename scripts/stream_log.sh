#!/bin/bash
# This script watches a log file and uses mdcat to render the lines that were added since the last change in Markdown to the terminal.
# Usage: watchlog.sh <logfile>

LOGFILE=$1

if [ ! -f "$LOGFILE" ]; then
    echo "File not found: $LOGFILE"
    exit 1
fi

LINES_BEFORE=$(wc -l <"$LOGFILE")

while true; do
    inotifywait -e modify "$LOGFILE" >/dev/null 2>&1
    LINES_AFTER=$(wc -l <"$LOGFILE")
    LINES_ADDED=$((LINES_AFTER - LINES_BEFORE))

    # Piping output to mdcat results in mdcat needing image links relative to project root rather than relative to the log file. This is mostly what we want anyway.
    tail -n "$LINES_ADDED" "$LOGFILE" | mdcat
    LINES_BEFORE=$LINES_AFTER
done
