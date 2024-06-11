
import re

from anthropic import Anthropic

import seer.env as env
from seer.cost import APICosts
from seer.image.frame import encode_image
from seer.log import debug, info, verbose
from seer.narrate import (
    IMAGE_MAX_SIZE,
    MAX_TOKENS,
    MEMORY_NOVELTY_THRESHOLD,
    MEMORY_SIZE,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    NOVELTY_THRESHOLD,
    RESPONSE_TIMEOUT,
    SYSTEM_PROMPTFILE,
)
from seer.util import mask_base64_messages, read_prompt_file

CLIENT = Anthropic(api_key=env.ANTHROPIC_API_KEY)
SYSTEM_PROMPT = read_prompt_file(SYSTEM_PROMPTFILE)

MESSAGES = []
APICOSTS = APICosts(MODEL_NAME)


RESPONSE_PATTERN = r"<narration novelty=(\d{1,3})>(.*?)</narration>"


def parse_response(response, parser=re.compile(RESPONSE_PATTERN)):
    """Parse the response from the API

    An example `response`is:
    ```
    <narration novelty=40>He said "Hi!" & went away.</narration>
    ```
    Note that this is not true XML, as the `novely` attribute is not quoted and the text content is not escaped. This is in line with the Anthropic Cookbook exampe (multimodal/reading_charts_graphs_powerpoints.ipynb) and indeed Claude does not escape the text content itself. So we use simple RegEx to parse the response.
    """
    match = parser.match(response)
    if match:
        novelty = int(match.group(1))
        narration = match.group(2)
        d = {"novelty": novelty, "narration": narration}
        return d
    else:
        return None, None


def narrate(tile, start, end):
    global MESSAGES, APICOSTS

    # prefill = f'<narration i="{i}" startTime="{start}" endTime="{end}">'

    prefill = "<narration novelty="
    encoded_jpeg = encode_image(tile, max_size=IMAGE_MAX_SIZE)

    MESSAGES = MESSAGES + [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": encoded_jpeg,
                    },
                }
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": prefill}]},
    ]

    debug(f"Sending {len(MESSAGES)} messages: {mask_base64_messages(MESSAGES)}")

    response = CLIENT.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        temperature=MODEL_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=MESSAGES,
        stop_sequences=["</narration>"],
        timeout=RESPONSE_TIMEOUT,
    )

    APICOSTS.ingest(response)
    APICOSTS.log_current_costs(verbose)

    narration = prefill + response.content[0].text + "</narration>"

    data = parse_response(narration)
    novelty = data["novelty"]
    text = data["narration"]

    if novelty > NOVELTY_THRESHOLD:
        info(f"[{novelty}] {text}", extra={"image": tile})
    else:
        verbose(f"[{novelty}] {text}", extra={"image": tile})

    debug(narration)

    # Insert the answer into the messages
    last = MESSAGES[-1]
    assert last["role"] == "assistant"
    last["content"][0]["text"] = narration

    # If not novel enough, forget the current interaction
    if not (novelty > MEMORY_NOVELTY_THRESHOLD):
        MESSAGES = MESSAGES[:-2]

    max_messages = 2 * MEMORY_SIZE

    if len(MESSAGES) > max_messages:  # FIXME: fails for memoriy size = 0
        MESSAGES = MESSAGES[-max_messages:]

    return text if novelty > NOVELTY_THRESHOLD else ""