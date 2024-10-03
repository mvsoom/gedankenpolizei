#!/bin/bash
echo $(date)
grab/websocket | \
python -m src.fast.narrate \
    --config fast.novelty_threshold:10 \
    --config log.level:DEBUG \
    --jsonl \
    --output-frames | \
python -m src.raw.stream \
    --config raw.memory_size:128 \
    --config slow.pace:0.5 \
    --config raw.pace:16 \
    --config log.level:DEBUG | \
monitor/text | \
tee long_test_output.txt | \
monitor/record long_test_output.jsonl --echo | \
emit/websocket