"""Stream RAWness conditioned on SLOW and FAST thoughts to stdout"""

import base64
import json
import queue
import random
import sys
import threading
from collections import deque
from math import exp, floor
from sys import exit
from time import sleep, time

import pandas as pd

from src import STARTTIME
from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame
from src.gemini import gemini, read_prompt_file, replace_variables
from src.log import debug, error, info, verbose
from src.raw.slot import BidirectionalSlot, Slot
from src.raw.tape import Tape

SYSTEM_PROMPT = read_prompt_file(CONFIG("raw.model.system_prompt_file"))
PROMPT = read_prompt_file(CONFIG("raw.model.prompt_file"))

MODEL = gemini(
    CONFIG("raw.model.name"),
    generation_config={
        "stop_sequences": CONFIG("raw.model.stop_sequences"),
        "top_p": CONFIG("raw.model.top_p"),
        "top_k": CONFIG("raw.model.top_k"),
        "temperature": CONFIG("raw.model.temperature"),
    },
    system_instruction=SYSTEM_PROMPT,
)

MAX_FAST_INPUTS = CONFIG("raw.max_fast_inputs")

SLOW_PACE = CONFIG("slow.pace")

RAW_MEMORY_SIZE = CONFIG("raw.memory_size")
RAW_PACE = CONFIG("raw.pace")
RAW_JITTER = CONFIG("raw.jitter")


def jitter(x):
    u = random.gauss(0, 1) * RAW_JITTER
    return x * exp(u)


def print_rolling_tape(raw_tape):
    # Clear the screen
    print("\033[H\033[J", end="", flush=True)

    # Output the rolling tape
    text = str(raw_tape)
    written, buffered = text.rsplit("↪", 1)
    buffered = f"\033[3m{buffered}\033[0m"  # Italics

    print(written + "↪" + buffered, end="", flush=True)


def raw_stream(args, raw_tape):
    last = time()
    while True:
        c = raw_tape.getchar()

        dt = time() - last
        target = 1.0 / RAW_PACE
        if dt < target:
            sleep(jitter(target - dt))

        if not args.roll_tape:
            print(c, end="", flush=True)
        else:
            print_rolling_tape(raw_tape)

        last = time()


def slow_stream(args, slowq):
    if args.no_slow_thoughts:
        return

    # Cold start; takes a while to load
    from src.slow.thought import (
        sample_nearby_thought,
        sample_random_thought,
    )

    walk = sample_random_thought()
    slowq.put_downwards(walk.iloc[-1].text, block=False)

    while True:
        start, end = slowq.get_from_below(block=True)

        if args.random_slow_thoughts:
            thought = sample_random_thought(walk)
        else:
            thought = sample_nearby_thought(walk, start, end)

        slowq.put_downwards(thought.iloc[0].text, block=False)
        walk = pd.concat([walk, thought])


def fast_thoughts_from(inputs):
    def gather():
        for input in inputs:
            dt = time() - input["timestamp"]
            narration = input["narration"]
            yield f"({dt:.1f}s ago) {narration}"

    return "\n".join(gather())


def raw_thoughts_from(raw_tape, ttft=float("inf")):
    """Get the stream of RAW thoughts from the running `raw_tape`

    If the tape is running ahead with respect to output(), we go ahead and return RAW thoughts that include the past but also a small amount of future characters
    These will be output() during the time it takes for the next request from the MODEL (this time is `ttft` or time to first token)
    This go-ahead strategy tries to simulate a continuous stream of thought without hiccups caused by finite `ttft`s
    """
    with raw_tape.lock:
        nbuffered = len(raw_tape[0:])
        nttft = ttft * RAW_PACE
        ncontinue = floor(min(nbuffered, nttft))

        info(f"RAW tape nbuffered: {nbuffered}, nttft: {nttft:.0f}")

        raw_tape.cut(+ncontinue, keep="left")
        raw_tape.cut(-RAW_MEMORY_SIZE, keep="right")

        return "".join(raw_tape[:])


def maybe_new_slow_thought(slowq):
    try:
        thought = slowq.get_from_above(block=False)
        info("Received new SLOW thought")
        return thought
    except queue.Empty:
        return None


def maybe_new_fast_inputs(fastq):
    try:
        inputs = fastq.get(block=False)
        info("Received new FAST inputs")
        return inputs
    except queue.Empty:
        return None


def maybe_last_frame(inputs):
    last = inputs[-1]

    if "frame" in last:
        rawjpeg = base64.b64decode(last["frame"])
        frame = Frame(rawjpeg)
        return frame.gemini_image()
    else:
        return None


def log(prompt, optional_frame, raw_tape):
    if optional_frame:
        prompt_text = "".join(str(p) for p in prompt)
        verbose(prompt_text, extra={"image": optional_frame._pil_image})
    else:
        verbose(prompt)

    debug(repr(raw_tape))


def generate(args, raw_tape, slowq, fastq):
    ttft = float("inf")  # Expected time to first token

    slow_thought = None
    fast_thoughts = None
    optional_frame = None
    raw_thoughts = None

    while True:
        if new := maybe_new_slow_thought(slowq):
            slow_thought = new

        if new := maybe_new_fast_inputs(fastq):
            fast_thoughts = fast_thoughts_from(new)
            optional_frame = maybe_last_frame(new)

        raw_thoughts = raw_thoughts_from(raw_tape, ttft)

        prompt = replace_variables(
            PROMPT,
            SLOW_THOUGHT=slow_thought,
            FAST_THOUGHTS=fast_thoughts,
            OPTIONAL_FRAME=optional_frame,
            RAW_THOUGHTS=raw_thoughts,
        )

        log(prompt, optional_frame, raw_tape)

        interrupted = False

        try:
            t = time()

            stream = MODEL.generate_content(prompt, stream=True)

            for i, chunk in enumerate(stream):
                if i == 0:
                    ttft = time() - t
                    info(f"Time to first token: {ttft:.2f}s")

                text = chunk.text
                raw_tape.puts(text)

                debug(f"Chunk {i}: {repr(text)}")

                if not fastq.empty():
                    interrupted = True
                    info("Stopping generation for reconditioning on FAST")

                if not slowq.down.empty():
                    interrupted = True
                    info("Stopping generation for reconditioning on SLOW")

                if interrupted:
                    # Stop streaming immediately to recondition on newly available information from FAST and/or SLOW
                    stream.close()
                    break

        except Exception as e:
            error(f"Exception during generation or streaming: {e}", exc_info=True)
            ttft = float("inf")
            continue

        if interrupted:
            continue
        else:
            # Sample a new SLOW thought ...
            start = "".join(raw_tape[:0])
            end = "".join(raw_tape[:])
            slowq.put_upwards((start, end), block=False)

            # ... and optionally wait for the thought to be transferred from the `raw_tape` to stdout.
            nbuffered = len(raw_tape[0:])
            nttft = ttft * RAW_PACE
            nwait = max(nbuffered - nttft, 0.0)
            wait = (nwait / RAW_PACE) * (1.0 - SLOW_PACE)

            info(f"Generation completed, waiting max {wait:.1f}s")
            fastq.slumber(wait)  # Wake up on new FAST inputs
            continue


def sleep_forever():
    while True:
        sleep(60)


def fast_stream(args, fastq):
    if args.no_fast_thoughts:
        sleep_forever()

    inputs = deque(maxlen=MAX_FAST_INPUTS)

    for line in sys.stdin:
        try:
            input = json.loads(line)
        except json.JSONDecodeError:
            error(f"Invalid JSON input: `{line}`")
            continue

        if args.time_offset:
            input["timestamp"] -= args.time_offset - STARTTIME

        if args.ignore_frames and "frame" in input:
            del input["frame"]

        inputs.append(input)
        fastq.put(inputs, block=False)


def launch(stream, *args, **kwargs):
    thread = threading.Thread(target=stream, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread


def main(args):
    raw_tape = Tape()
    raw = launch(raw_stream, args, raw_tape)

    slowq = BidirectionalSlot()
    slow = launch(slow_stream, args, slowq)

    fastq = Slot()
    generator = launch(generate, args, raw_tape, slowq, fastq)

    fast_stream(args, fastq)  # Blocks on stdin

    generator.join()
    slow.join()
    raw.join()

    return 0


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Encourage ASCII art",  # TODO + specify terminal width together with this flag
    )
    parser.add_argument(
        "--time-offset",
        type=float,
        default=None,
        help="Rebase the timestamps using this offset",
    )
    parser.add_argument(
        "--ignore-frames",
        action="store_true",
        default=False,
        help="Ignore frame inputs",
    )
    parser.add_argument(
        "--no-slow-thoughts",
        action="store_true",
        default=False,
        help="Disable SLOW thought stream",
    )
    parser.add_argument(
        "--random-slow-thoughts",
        action="store_true",
        default=False,
        help="Always sample random SLOW thoughts instead of walking the embedding space",
    )
    parser.add_argument(
        "--no-fast-thoughts",
        action="store_true",
        default=False,
        help="Disable FAST thought stream",
    )
    parser.add_argument(
        "--roll-tape",
        action="store_true",
        default=False,
        help="Output the rolling tape of RAW thoughts. Requires a terminal that supports ANSI escape codes",
    )

    args = parser.parse_args()

    PROMPT = replace_variables(
        PROMPT, MAYBE_ASCII_ART="ASCII" + " " if args.ascii else None
    )

    exit(main(args))
