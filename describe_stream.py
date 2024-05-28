"""
Write descriptions of a video stream to stdout.

Usage to append to a file in realtime:

    python -u describe_stream.py [...] >> descriptions

The -u flag disables buffering.
"""

import argparse
import os
import threading
from threading import Lock
from time import sleep, time

import cv2

from describe_frame import describe
from frame import format_time, raw_to_image, sample_frames, timestamp
from logger import config_app_logger, debug
from tile import concatenate_images_grid

MONITOR = "monitor"
RAWFRAMES = []
EXITCODE = 1
LOCK = Lock()


TILESIZE = 4


def stream(name, monitor):
    global RAWFRAMES, EXITCODE

    cap = cv2.VideoCapture(name)
    if not cap.isOpened():
        raise RuntimeError(f"Error opening video stream: {name}")
    fps = cap.get(cv2.CAP_PROP_FPS)

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

    frameindex = 0

    global RAWFRAMES

    while streaming_thread.is_alive():
        if len(RAWFRAMES) < args.tilesize:
            sleep(0.01)
            continue

        with LOCK:
            ts, rawframes = zip(*RAWFRAMES)
            RAWFRAMES.clear()

        ts, rawframes = sample_frames(ts, rawframes, args.tilesize)
        frames = [raw_to_image(rawframe) for rawframe in rawframes]

        if args.timestamp:
            for t, frame in zip(ts, frames):
                timestamp(t, frame)

        # tile = concatenate_images_grid(frames, 0, (1024, 1024))
        # tile = concatenate_images_grid(frames, 0, (640, 480))
        tile = concatenate_images_grid(frames, 0, (320, 240))

        if args.dumpframes is not None:
            frameindex += 1
            tile.save(args.dumpframes % frameindex)

        start = format_time(ts[0])
        end = format_time(ts[-1])

        print(f"-------------- {frameindex}")

        # Execute shell command "timg"
        if args.timg:
            os.system("timg " + args.dumpframes % frameindex)

        t1 = time()
        narration = describe(frameindex, start, end, tile, stream_text=False)
        latency = time() - t1

        print(f"-------------- {latency:.2f} s")

    return EXITCODE


def parse_args():
    parser = argparse.ArgumentParser(
        description="Write descriptions of a video stream to stdout"
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=0,
        help="Name of the device to open with cv2. If not supplied, open device at %(default)s",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Whether to monitor the stream in realtime",
    )
    parser.add_argument(
        "--timg",
        action="store_true",
        help="Whether to use timg to display the current tile",
    )
    parser.add_argument(
        "--timestamp",
        action="store_true",
        default=True,
        help="Write timestamps of the described frames (default: %(default)s",
    )
    parser.add_argument(
        "--dumpframes",
        nargs="?",
        const="",
        help="Write out processed frames. If arg is given, use it as the basename",
    )
    parser.add_argument(
        "--tilesize",
        default=TILESIZE,
        type=int,
        help="Number of frames to sample per tile (default: %(default)s)",
    )

    parser.add_argument(
        "--stderr-level",
        default="INFO",
        help="Logging level for stderr (default: %(default)s)",
    )

    parser.add_argument(
        "--logfile-level",
        default="DEBUG",
        help="Logging level for log file (default: %(default)s)",
    )

    parser.add_argument(
        "--logfile",
        default=None,
        help="Log file (default: %(default)s)",
    )

    args = parser.parse_args()

    if args.dumpframes is not None:
        basename = args.dumpframes or str(args.name)
        args.dumpframes = basename + ".%.6i.jpg"

    return args


if __name__ == "__main__":
    args = parse_args()

    config_app_logger(args)

    debug(f"Running main({args})")

    exit(main(args))
