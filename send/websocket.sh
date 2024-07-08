#/bin/bash
# Send stdin text stream over websocket
PORT=8766

websocat --exit-on-eof --text ws-l:127.0.0.1:$PORT -