"""Narrate MJPEG stdin input to stdout"""

import json
import sys
import threading
from threading import Lock
from time import sleep

from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame, Memory, narrate
from src.log import debug, error, info, verbose

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


def valid_narration(past, output):
    current_narration = output["narration"]
    if not current_narration:
        return False

    last_narration = past.last_narration()
    if not last_narration:
        return True

    return current_narration.lower() != last_narration.lower()


def writeout(output, frame, args):
    if args.jsonl:
        if args.output_frames:
            s = json.dumps(
                {"frame": frame.encode64(), "timestamp": frame.timestamp, **output}
            )
        else:
            s = json.dumps(output)
    else:
        s = output["narration"]
    print(s, flush=True)


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

        # Write out if the narration is novel enough and log output
        # Note: repeated narrations do not break the system in any way, but filtering them out saves on costs and latency
        # In addition, this prevents clogging the memory with very similar frames
        def logreply(level):
            level(f"Narration: {output}", extra={"image": now})

        conditions = [
            output["novelty"] >= NOVELTY_THRESHOLD,
            valid_narration(past, output),
        ]

        if all(conditions):
            writeout(output, now, args)
            past.log(verbose)
            past.remember(now, output)
            logreply(info)
        else:
            logreply(verbose)

    return EXITCODE


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output narrations with metadata in JSONL format(default: %(default)s)",
    )
    parser.add_argument(
        "--output-frames",
        action="store_true",
        help="Output last frame together with narration (requires --jsonl, default: %(default)s)",
    )

    args = parser.parse_args()
    if args.output_frames and not args.jsonl:
        raise ValueError("--output-frames requires --jsonl")

    debug(f"Running main({args})")

    exit(main(args))
