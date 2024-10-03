#!/bin/bash
# Settings used for the demo; open client/client.html in a browser for fancy output
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
    --config log.level:DEBUG \
    --roll-tape \
    2> >(tee long_test_output.txt | emit/websocket)