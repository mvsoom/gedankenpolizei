#!/usr/bin/env python
"""Undecorate asciinema output of RAW thoughts to simple text stream"""

import sys

CLEAR_SCREEN_SEQ = "\033[H\033[J"


def read_and_echo():
    buffer = ""

    while True:
        try:
            # Read one character at a time ASAP
            char = sys.stdin.read(1)
            buffer += char

            if buffer.endswith(CLEAR_SCREEN_SEQ):
                keep = buffer.split("↪")
                print(keep[0][-1], end="", flush=True)
                buffer = ""

        except KeyboardInterrupt:
            break
        except EOFError:
            break


if __name__ == "__main__":
    read_and_echo()
