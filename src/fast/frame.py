
import os
import re
from pprint import pformat

import dotenv
from anthropic import Anthropic

from src.config import CONFIG
from src.cost import APICosts
from src.image.frame import encode_image
from src.log import debug, error, info, verbose
from src.util import (
    mask_base64_messages,
    read_prompt_file,
    replace_variables_in_prompt,
)

IMAGE_MAX_SIZE = (1024, 1024)  #  Claude API will downsize if larger than this
MAX_TOKENS = 300  # Max tokens to generate before stopping
RESPONSE_TIMEOUT = 10  # seconds


MEMORY_MAX_IMAGES = CONFIG("fast.memory.max_images")
MEMORY_NOVELTY_THRESHOLD = CONFIG("fast.memory.novelty_threshold")
MEMORY_SIZE = CONFIG("fast.memory.size")
MODEL_NAME = CONFIG("fast.model.name")
MODEL_TEMPERATURE = CONFIG("fast.model.temperature")
NOVELTY_THRESHOLD = CONFIG("fast.novelty_threshold")
SYSTEM_PROMPT_FILE = CONFIG("fast.system_prompt_file")
TILE_NUM_FRAMES = CONFIG("fast.tile.num_frames")


dotenv.load_dotenv()


CLIENT = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
SYSTEM_PROMPT = read_prompt_file(SYSTEM_PROMPT_FILE)
SYSTEM_PROMPT = replace_variables_in_prompt(
    SYSTEM_PROMPT, {"TILE_NUM_FRAMES": TILE_NUM_FRAMES}
)

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
        narration = match.group(2).strip()
        d = {"novelty": novelty, "narration": narration}
        return d
    else:
        return None


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

    debug(
        f"Sending {len(MESSAGES)} messages:\n{pformat(mask_base64_messages(MESSAGES), width=40)}"
    )

    verbose(f"Sending {len(MESSAGES)} messages")

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

    # Sometimes happens
    if (novelty > NOVELTY_THRESHOLD) and (not text):
        error("Empty text despite sufficient novelty")

    if novelty > NOVELTY_THRESHOLD:
        info(f"[{novelty}] {text}", extra={"image": tile})
    else:
        verbose(f"[{novelty}] {text}", extra={"image": tile})

    # Insert the answer into the messages
    last = MESSAGES[-1]
    assert last["role"] == "assistant"
    last["content"][0]["text"] = narration

    # If not novel enough, forget the current interaction
    if not (novelty > MEMORY_NOVELTY_THRESHOLD):
        MESSAGES = MESSAGES[:-2]

    # Limit the number of messages in memory
    max_messages = 2 * MEMORY_SIZE
    MESSAGES = MESSAGES[-max_messages:] if max_messages else []

    # Limit the number of images in memory
    running_count = MEMORY_MAX_IMAGES
    for message in reversed(MESSAGES):
        if message["role"] == "user":
            running_count -= 1
            if running_count < 0:
                message["content"] = [
                    {"type": "text", "text": "<image>"}
                ]  # FIXME: add time stamp like "3 seconds ago"

    return text if novelty > NOVELTY_THRESHOLD else ""