"""Narrate MJPEG stdin input to stdout"""

import functools
import json
import sys
import threading
from threading import Lock
from time import sleep

from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame, Memory, narrate
from src.log import debug, error, info, verbose

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)

MAX_SIZE = CONFIG("fast.max_size")
NOVELTY_THRESHOLD = CONFIG("fast.novelty_threshold")

LASTJPEG = None
EXITCODE = 1
LOCK = Lock()


def findjpeg(buffer):
    # Find the first complete JPEG image in the buffer
    # TODO: can also use Stream.readuntil() together with aioconsole package (https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamReader.readuntil)
    i = buffer.find(b"\xff\xd9")
    if i != -1:
        i += 2
        return buffer[:i]


def stream():
    buffer = bytearray()
    chunksize = 4096

    global LASTJPEG

    while True:
        data = sys.stdin.buffer.read(chunksize)
        if not data:
            break

        buffer.extend(data)

        if jpeg := findjpeg(buffer):
            n = len(jpeg)
            buffer = buffer[n:]
            chunksize = (chunksize + n) // 2

            with LOCK:
                LASTJPEG = jpeg.copy()


def writeout(output, as_jsonl):
    if as_jsonl:
        print(json.dumps(output))
    else:
        print(output["narration"])


def main(args):
    streaming_thread = threading.Thread(target=stream)
    streaming_thread.daemon = True
    streaming_thread.start()

    past = Memory(CONFIG)

    global LASTJPEG

    while streaming_thread.is_alive():
        if not LASTJPEG:
            sleep(0.01)
            continue

        with LOCK:
            lastjpeg = LASTJPEG
            LASTJPEG = None

        # Narrate the last JPEG frame (`now`)
        now = Frame(lastjpeg, MAX_SIZE)

        try:
            output = narrate(past, now)
        except Exception as e:
            error(f"Exception during narrate: {e}", exc_info=True)
            continue

        # Write out if novel enough and log output
        past.log(verbose)

        def logreply(level):
            level(f"Narration: {output['reply']}", extra={"image": now})

        if output["novelty"] < NOVELTY_THRESHOLD:
            logreply(verbose)
        else:
            if output["narration"]:
                writeout(output, args.jsonl)
            past.remember(now, output)
            logreply(info)

    return EXITCODE


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output narrations with metadata in JSONL format(default: %(default)s)",
    )

    args = parser.parse_args()

    debug(f"Running main({args})")

    exit(main(args))
