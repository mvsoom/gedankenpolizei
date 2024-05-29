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
    tail -n "$LINES_ADDED" "$LOGFILE" | mdcat
    LINES_BEFORE=$LINES_AFTER
done
