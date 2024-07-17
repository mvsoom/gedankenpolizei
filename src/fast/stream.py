"""Narrate MJPEG stdin input to stdout"""

import argparse
import functools
import io
import json
import sys
import threading
from threading import Lock
from time import sleep, time

from PIL import Image

from src.fast import TILE_NUM_FRAMES, TILE_SIZE
from src.fast.frame import narrate
from src.image.frame import format_time, sample_frames, timestamp
from src.image.tile import concatenate_images_grid
from src.log import debug, error

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)


RAWFRAMES = []
EXITCODE = 1
LOCK = Lock()


def findjpeg(buffer):
    # Find the first complete JPEG image in the buffer
    i = buffer.find(b"\xff\xd9")
    if i != -1:
        i += 2
        return buffer[:i]


def stream():
    buffer = bytearray()
    chunksize = 4096

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
                RAWFRAMES.append((time(), jpeg))


def main(args):
    streaming_thread = threading.Thread(target=stream)
    streaming_thread.daemon = True
    streaming_thread.start()

    global RAWFRAMES

    while streaming_thread.is_alive():
        if len(RAWFRAMES) < TILE_NUM_FRAMES:
            sleep(0.01)
            continue

        with LOCK:
            ts, rawframes = zip(*RAWFRAMES)
            RAWFRAMES.clear()

        ts, rawframes = sample_frames(ts, rawframes, TILE_NUM_FRAMES)

        frames = [Image.open(io.BytesIO(rawframe)) for rawframe in rawframes]

        for t, frame in zip(ts, frames):
            timestamp(t, frame)

        tile = concatenate_images_grid(frames, 0, TILE_SIZE)

        start = format_time(ts[0])
        end = format_time(ts[-1])

        # FIXME
        try:
            narration = narrate(tile, start, end)

            # Replace all newlines with spaces and trim
            narration = narration.replace("\n", " ").strip()
            if len(narration) > 0:
                if not args.jsonl:
                    print(narration, flush=True)
                else:
                    output = {"t": time(), "text": narration}
                    print(json.dumps(output), flush=True)

        except Exception as e:
            error(f"Error narrating: {e}")
            raise e

    return EXITCODE


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output narrations with metadata in JSONL format(default: %(default)s)",
    )

    args = parser.parse_args()

    debug(f"Running main({args})")

    exit(main(args))
