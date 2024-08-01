#!/bin/bash
grab/websocket | python -m src.fast.narrate --jsonl --output-frames | python -m src.raw.stream --config raw.memory_size:128 --roll-tape 2> >(emit/websocket)