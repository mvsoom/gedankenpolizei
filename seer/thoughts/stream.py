import argparse
import functools
import json
import sys
import threading
from collections import deque
from copy import copy
from queue import LifoQueue
from sys import exit
from time import time

import anthropic

from seer import env
from seer.cost import APICosts
from seer.log import error, info, warning
from seer.thoughts import MODEL_NAME, MODEL_TEMPERATURE, TERMINAL_WIDTH, USER_PROMPTFILE
from seer.util import read_prompt_file, replace_variables_in_prompt

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)

CLIENT = anthropic.Anthropic(api_key=env.ANTHROPIC_API_KEY)

USER_PROMPT = read_prompt_file(USER_PROMPTFILE)

APICOSTS = APICosts(MODEL_NAME)


def user_text(data):
    narration = ""
    for event in data:
        text = event["text"].strip()  # Remove trailing newline
        dt = time() - event["t"]
        narration += f"({dt:.1f}s ago) {text}\n"

    user_text = replace_variables_in_prompt(
        USER_PROMPT, {"NARRATION": narration, "TERMINAL_WIDTH": TERMINAL_WIDTH}
    )

    return user_text


def stream(q, args):
    PREFILL = f"Here is the video narration as a stream of consciousness between <soc>...</soc> tags:\n\n<soc terminal_width={TERMINAL_WIDTH}>\n"

    thoughts = copy(PREFILL)
    reboot = 0

    while True:
        data = q.get(block=True)  # Get the most recent item from the LIFO queue

        if not q.empty():
            pass
            # print("LIFO queue saturated")

        # print("GOT", user_text(data))

        # Separate the PREFILL from the rest of the thoughts
        prefill_length = len(PREFILL)
        prefill = thoughts[:prefill_length]
        rest_of_thoughts = thoughts[prefill_length:]

        # Format the rest of the thoughts in 16 character chunks
        # rest_of_thoughts = textwrap.fill(rest_of_thoughts, width=TERMINAL_WIDTH)

        # Join the PREFILL and the formatted thoughts back together
        thoughts = prefill + rest_of_thoughts

        info(thoughts)

        try:
            with CLIENT.messages.stream(
                model=MODEL_NAME,
                max_tokens=1000,
                temperature=MODEL_TEMPERATURE,
                stop_sequences=["</soc>"],
                # system="Use ANSI codes to color your responses.",
                messages=[
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": user_text(data)}],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": thoughts.strip(),  # Final assistant content cannot end with trailing whitespace
                            }
                        ],
                    },
                ],
            ) as stream:
                for chunk in stream.text_stream:
                    thoughts += chunk

                    if q.empty():
                        # print("\033[94m" + chunk + "\033[0m", end="", flush=True)
                        print(chunk, end="", flush=True)
                    else:
                        # If we get a new update, break the loop
                        if args.annotate:
                            print(chunk, end="|", flush=True)
                        else:
                            # print("\033[94m" + chunk + "\033[0m", end="", flush=True)
                            print(chunk, end="", flush=True)
                        break
        # Except exceptions from anthropic
        except Exception as e:
            error(f"Anthropic error: {e}")
            continue

        # Anthropic supports stream cancellation to save tokens
        stream.close()

        APICOSTS.ingest(stream.current_message_snapshot)
        APICOSTS.log_current_costs(warning)

        if q.empty():
            # Ended thought naturally
            if args.annotate:
                print("*", end="", flush=True)

            reboot += 1

            if reboot % 3 == 0:
                if args.annotate:
                    print("°", end="", flush=True)
                thoughts += f"\n</soc>\n\n<soc terminal_width={TERMINAL_WIDTH}>\n"


def main(args):
    q = LifoQueue(maxsize=2)  # 2 to detect if queue overloads

    streaming_thread = threading.Thread(target=stream, args=(q, args))

    streaming_thread.daemon = True
    streaming_thread.start()

    # When a new item is appended to a full deque, the item at the opposite end is automatically removed
    narration = deque(maxlen=10)

    # Echo lines from stdin
    for line in sys.stdin:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            error(f"Invalid JSON input: '{data}'")

        narration.append(data)

        # print("INTO QUEUE:", user_text(narration))
        # print("\nPUT:", data["text"])
        q.put(narration)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--annotate", action="store_true", help="Annotate output for debugging"
    )
    args = parser.parse_args()

    exit(main(args))