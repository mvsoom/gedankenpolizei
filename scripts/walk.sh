#!/bin/bash
google-chrome http://127.0.0.1:8050 &
grab/webcam | \
python -m src.fast.narrate \
    --config fast.novelty_threshold:10 \
    --jsonl \
    --output-frames | \
python -m src.raw.stream \
    --config raw.memory_size:128 \
    --config slow.pace:0.5 \
    --config raw.pace:16 \
    --roll-tape \
    2> >(python -m src.slow.walk \
                --show_globe --track)