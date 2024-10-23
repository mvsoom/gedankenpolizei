#!/bin/bash

python -m http.server --directory client &
server_pid=$!

sleep 3

# Must be localhost (not 0.0.0.0), otherwise untrusted connection
chromium-browser http://localhost:8000/client.html

kill $server_pid