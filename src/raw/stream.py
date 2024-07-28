"""Stream RAWness conditioned on SLOW and FAST thoughts to stdout"""

import base64
import functools
import json
import sys
import threading
from collections import deque
from queue import LifoQueue
from sys import exit
from time import time

_TIME_OFFSET = time()  # Need this here for accurate --time-offset

from src.config import CONFIG, ConfigArgumentParser
from src.fast.frame import Frame
from src.gemini import gemini, read_prompt_file, replace_variables
from src.log import debug, error, info

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)

SYSTEM_PROMPT = read_prompt_file(CONFIG("raw.model.system_prompt_file"))
PROMPT = read_prompt_file(CONFIG("raw.model.prompt_file"))

MODEL_NAME = CONFIG("raw.model.name")
MODEL_TEMPERATURE = CONFIG("raw.model.temperature")
MODEL = gemini(
    MODEL_NAME,
    generation_config={"temperature": MODEL_TEMPERATURE, "stop_sequences": ["```"]},
    system_instruction=SYSTEM_PROMPT,
)

MAX_INPUTS = CONFIG("raw.max_inputs")


def fast_thoughts(inputs):
    def gather():
        for input in inputs:
            dt = time() - input["timestamp"]
            narration = input["narration"]
            yield f"({dt:.2f}s ago) {narration}"

    return "\n".join(gather())


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


def stream(q, args):
    from src.slow.thoughts import sample_slow_thought  # Import takes a while

    slow_thought = sample_slow_thought()
    raw_thoughts = ""

    while True:
        inputs = q.get(block=True)

        optional_frame = maybe_last_frame(inputs, args.ignore_frames)

        prompt = replace_variables(
            PROMPT,
            SLOW_THOUGHT=slow_thought,
            FAST_THOUGHTS=fast_thoughts(inputs),
            OPTIONAL_FRAME=optional_frame,
            RAW_THOUGHTS=raw_thoughts,
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
                raw_thoughts += text
                print(text, end="")
                debug(text)

                if not q.empty():
                    # Break the loop and regenerate content conditioned on newly received inputs
                    stream.close()
                    continue

        except Exception as e:
            error(f"Exception during generate_content or streaming: {e}", exc_info=True)
            continue

        # If we reach this point, the stream of thought has ended naturally
        slow_thought = sample_slow_thought()


def main(args):
    q = LifoQueue(1)

    streaming_thread = threading.Thread(target=stream, args=(q, args))
    streaming_thread.daemon = True
    streaming_thread.start()

    inputs = deque(maxlen=MAX_INPUTS)

    for line in sys.stdin:
        try:
            input = json.loads(line)
        except json.JSONDecodeError:
            error(f"Invalid JSON input: `{line}`")
            continue

        if args.time_offset:
            input["timestamp"] -= args.time_offset - _TIME_OFFSET

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
