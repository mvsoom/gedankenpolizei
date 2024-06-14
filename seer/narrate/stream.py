"""Narrate a video stream line by line to stdout"""

import argparse
import functools
import json
import threading
from threading import Lock
from time import sleep, time

import cv2

from seer.image.frame import format_time, raw_to_image, sample_frames, timestamp
from seer.image.tile import concatenate_images_grid
from seer.log import debug, error
from seer.narrate import TILE_NUM_FRAMES, TILE_SIZE
from seer.narrate.frame import narrate

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)


MONITOR = "monitor"
RAWFRAMES = []
EXITCODE = 1
LOCK = Lock()


def stream(name, monitor):
    global RAWFRAMES, EXITCODE

    cap = cv2.VideoCapture(name)
    if not cap.isOpened():
        raise RuntimeError(f"Error opening video stream: {name}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    debug(f"Opened video stream: {name} at {fps} fps with resolution {w}x{h}")

    try:
        while cap.isOpened():
            # Get the most recent frame (rather than the next frame in the stream)
            ret, rawframe = cap.read()
            if not ret:
                # Likely EOF or stream closed
                EXITCODE = 0
                break

            global RAWFRAMES
            with LOCK:
                RAWFRAMES.append((time(), rawframe))

            if monitor:
                cv2.imshow(MONITOR, rawframe)
                delay_msec = int(1000 / fps)
                if cv2.waitKey(delay_msec) & 0xFF == ord("q"):
                    # User pressed q
                    EXITCODE = 0
                    break
            else:
                delay_sec = float(1 / fps)
                sleep(delay_sec)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if monitor:
            cv2.destroyWindow(MONITOR)


def main(args):
    streaming_thread = threading.Thread(target=stream, args=(args.name, args.monitor))
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
        frames = [raw_to_image(rawframe) for rawframe in rawframes]

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
        "name",
        nargs="?",
        default=0,
        help="Name of the device to open with cv2. If not supplied, open device at %(default)s",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Open a window to monitor the stream in realtime (default: %(default)s)",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output narrations with metadata in JSONL format(default: %(default)s)",
    )

    args = parser.parse_args()

    debug(f"Running main({args})")

    exit(main(args))
