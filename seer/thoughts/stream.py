import functools
import json
import sys
import threading
from collections import deque
from copy import copy
from queue import LifoQueue
from time import time

import anthropic

from seer import env
from seer.thoughts import USER_PROMPTFILE
from seer.util import read_prompt_file, replace_variables_in_prompt

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)

CLIENT = anthropic.Anthropic(api_key=env.ANTHROPIC_API_KEY)

TEMPERATURE = 1.0

USER_PROMPT = read_prompt_file(USER_PROMPTFILE)


def user_text(data):
    narration = ""
    for event in data:
        text = event["text"].strip()  # Remove trailing newline
        dt = time() - event["t"]
        narration += f"({dt:.1f}s ago) {text}\n"

    user_text = replace_variables_in_prompt(USER_PROMPT, {"NARRATION": narration})

    return user_text


def convert_ansi_codes(text):
    return text.replace("[", "\033[")


def stream(q):
    PREFILL = "Here is the video narration as a stream of consciousness between <soc>...</soc> tags:\n\n<soc>"

    thoughts = copy(PREFILL)

    natural_end = 0

    while True:
        data = q.get(block=True)  # Get the most recent item from the LIFO queue

        if not q.empty():
            print("LIFO queue held multiple items!")

        # print("GOT", user_text(data))

        with CLIENT.messages.stream(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=TEMPERATURE,
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

                natural_end = 0

                if q.empty():
                    print("\033[94m" + chunk + "\033[0m", end="", flush=True)
                else:
                    # If we get a new update, break the loop
                    print(chunk, end="|", flush=True)
                    break
        del stream

        if q.empty():
            # Ended thought naturally
            print("*", end="", flush=True)

            natural_end += 1
            if natural_end > 3:
                # Reset thoughts
                print("/", end="", flush=True)
                thoughts = copy(PREFILL)


def main():
    print("START")

    q = LifoQueue(maxsize=2)  # 2 to detect if queue overloads

    streaming_thread = threading.Thread(target=stream, args=(q,))

    streaming_thread.daemon = True
    streaming_thread.start()

    # When a new item is appended to a full deque, the item at the opposite end is automatically removed
    narration = deque(maxlen=10)

    # Echo lines from stdin
    for line in sys.stdin:
        data = json.loads(line)
        narration.append(data)

        # print("INTO QUEUE:", user_text(narration))
        # print("\nPUT:", data["text"])
        q.put(narration)

    print("DONE")


if __name__ == "__main__":
    main()