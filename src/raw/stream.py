"""Stream RAWness conditioned on SLOW and FAST thoughts to stdout"""

import base64
import json
import queue
import random
import sys
import threading
from collections import deque
from math import exp, floor
from queue import LifoQueue
from sys import exit
from time import sleep, time

from src import STARTTIME
from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame
from src.gemini import gemini, read_prompt_file, replace_variables
from src.log import debug, error, info, verbose
from src.raw.tape import Tape
from src.slow.thoughts import sample_thought

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
MAX_RAW_MEMORY = CONFIG("raw.max_raw_memory")
OUTPUT_RATE = CONFIG("raw.output.rate")
OUTPUT_JITTER = CONFIG("raw.output.jitter")


def jitter(x):
    u = random.gauss(0, 1) * OUTPUT_JITTER
    return x * exp(u)


def output(raw_tape, args):
    last = time()
    while True:
        c = raw_tape.getchar()

        dt = time() - last
        target = 1.0 / OUTPUT_RATE
        if dt < target:
            sleep(jitter(target - dt))

        if not args.roll_tape:
            print(c, end="", flush=True)
        else:
            # Clear the screen
            print("\033[H\033[J", end="", flush=True)

            # Output the rolling tape
            text = str(raw_tape)
            written, buffered = text.rsplit("↪", 1)
            buffered = f"\033[3m{buffered}\033[0m"  # Italics

            print(written + "↪" + buffered, end="", flush=True)

        last = time()


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
        nttft = ttft * OUTPUT_RATE
        ncontinue = floor(min(nbuffered, nttft))

        info(f"Tape nbuffered: {nbuffered}, nttft: {nttft:.0f}")

        raw_tape.cut(+ncontinue, keep="left")
        raw_tape.cut(-MAX_RAW_MEMORY, keep="right")

        return "".join(raw_tape[:])


def maybe_last_frame(inputs):
    last = inputs[-1]

    if "frame" in last:
        rawjpeg = base64.b64decode(last["frame"])
        frame = Frame(rawjpeg)
        return frame.gemini_image()
    else:
        return None


def sample_slow_thought():
    return sample_thought()  # FIXME


def stream(raw_tape, q, args):
    ttft = float("inf")  # Expected time to first token

    fast_thoughts = ""
    optional_frame = None
    slow_thought = sample_slow_thought()

    while True:
        try:
            # If new inputs, update FAST stream
            inputs = q.get_nowait()

            info("Received new inputs")

            fast_thoughts = fast_thoughts_from(inputs)
            optional_frame = maybe_last_frame(inputs)
        except queue.Empty:
            pass

        raw_thoughts = raw_thoughts_from(raw_tape, ttft)

        prompt = replace_variables(
            PROMPT,
            SLOW_THOUGHT=slow_thought,
            FAST_THOUGHTS=fast_thoughts,
            OPTIONAL_FRAME=optional_frame,
            RAW_THOUGHTS=raw_thoughts,
        )

        if optional_frame:
            prompt_text = "".join(str(p) for p in prompt)
            verbose(prompt_text, extra={"image": optional_frame._pil_image})
        else:
            verbose(prompt)

        debug(repr(raw_tape))

        try:
            t = time()
            recondition = False

            stream = MODEL.generate_content(prompt, stream=True)

            for i, chunk in enumerate(stream):
                if i == 0:
                    ttft = time() - t
                    info(f"Time to first token: {ttft:.2f}s")

                text = chunk.text
                raw_tape.puts(text)

                debug(f"Chunk {i}: {repr(text)}")

                if not q.empty():
                    # Break the loop immediately to recondition on newly received inputs in `q`
                    stream.close()
                    del stream
                    recondition = True
                    info("Stopped stream for reconditioning")
                    break

            if recondition:
                continue

        except Exception as e:
            error(f"Exception during generate_content or streaming: {e}", exc_info=True)
            ttft = float("inf")
            continue

        # WHAT TO DO HERE WITH TOKEN PREDICITON?
        # If we reach this point, the stream of thought has ended naturally

        info("Stream ended naturally")

        slow_thought = sample_slow_thought() if not args.no_slow_thoughts else ""

        info("Sampled new slow thought")


def main(args):
    raw_tape = Tape()

    output_thread = threading.Thread(target=output, args=(raw_tape, args))
    output_thread.daemon = True
    output_thread.start()

    q = LifoQueue(1)

    streaming_thread = threading.Thread(target=stream, args=(raw_tape, q, args))
    streaming_thread.daemon = True
    streaming_thread.start()

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
        q.put(inputs)

    streaming_thread.join()
    output_thread.join()

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
        help="Disable SLOW thoughts",
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

    if args.no_slow_thoughts:
        sample_slow_thought = lambda: ""

    exit(main(args))
