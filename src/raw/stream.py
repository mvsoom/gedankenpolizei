"""Stream RAWness conditioned on SLOW and FAST thoughts to stdout"""

import base64
import json
import random
import sys
import threading
from collections import deque
from math import exp
from queue import LifoQueue
from sys import exit
from time import sleep, time

from src import STARTTIME
from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame
from src.gemini import gemini, read_prompt_file, replace_variables
from src.log import debug, error, info, verbose
from src.raw.tape import Tape
from src.slow.thoughts import sample_slow_thought  # Import takes a while

SYSTEM_PROMPT = read_prompt_file(CONFIG("raw.model.system_prompt_file"))
PROMPT = read_prompt_file(CONFIG("raw.model.prompt_file"))

MODEL_NAME = CONFIG("raw.model.name")
MODEL_TEMPERATURE = CONFIG("raw.model.temperature")
MODEL = gemini(
    MODEL_NAME,
    generation_config={"temperature": MODEL_TEMPERATURE, "stop_sequences": ["```"]},
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

        print(c, end="", flush=True)

        last = time()

def fast_thoughts(inputs):
    def gather():
        for input in inputs:
            dt = time() - input["timestamp"]
            narration = input["narration"]
            yield f"({dt:.2f}s ago) {narration}"

    return "\n".join(gather())


def raw_thoughts(raw_tape):
    return "".join(raw_tape[:])  # TODO


def maybe_last_frame(inputs, ignore_frames):
    if ignore_frames:
        return None

    last = inputs[-1]

    if "frame" in last:
        rawjpeg = base64.b64decode(last["frame"])
        frame = Frame(rawjpeg)
        return frame.gemini_image()
    else:
        return None


def stream(raw_tape, q, args):
    slow_thought = sample_slow_thought()

    while True:
        inputs = q.get(block=True)

        optional_frame = maybe_last_frame(inputs, args.ignore_frames)

        raw_tape.cut(-MAX_RAW_MEMORY, keep="right")  # TODO: adjust to future chars

        prompt = replace_variables(
            PROMPT,
            SLOW_THOUGHT=slow_thought,
            FAST_THOUGHTS=fast_thoughts(inputs),
            OPTIONAL_FRAME=optional_frame,
            RAW_THOUGHTS=raw_thoughts(raw_tape),
        )

        if optional_frame:
            prompt_text = "".join(str(p) for p in prompt)
            info(prompt_text, extra={"image": optional_frame._pil_image})
        else:
            info(prompt)

        try:
            stream = MODEL.generate_content(
                prompt, stream=True
            )  # TODO: predict # tokens to ask for

            for chunk in stream:
                text = chunk.text
                raw_tape.puts(text)
                debug(text)

                if not q.empty():
                    # Break the loop and regenerate content conditioned on newly received inputs
                    verbose("Streaming stopped to recondition on new inputs")
                    stream.close()
                    continue

        except Exception as e:
            error(f"Exception during generate_content or streaming: {e}", exc_info=True)
            continue

        # If we reach this point, the stream of thought has ended naturally
        slow_thought = sample_slow_thought()


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

        inputs.append(input)
        q.put(inputs)


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

    args = parser.parse_args()

    PROMPT = replace_variables(
        PROMPT, MAYBE_ASCII_ART="ASCII art " if args.ascii else None
    )

    exit(main(args))
