import warnings
from xml.etree import ElementTree

from anthropic import Anthropic

import seer.env as env
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
from seer.narrate.cost import APICosts
from seer.util import mask_base64_messages, read_prompt_file

CLIENT = Anthropic(api_key=env._ANTHROPIC_API_KEY)
SYSTEM_PROMPT = read_prompt_file(SYSTEM_PROMPTFILE)

MESSAGES = []
APICOSTS = APICosts(MODEL_NAME)

def extract_narration_and_novelty(response):
    # FIXME
    try:
        root = ElementTree.fromstring(response)
        narration = next(root.iter("narration"))
        text = narration.text if narration.text else ""
        novelty = narration.get("novelty") if "novelty" in narration.attrib else None
        return text, int(novelty)
    except (ElementTree.ParseError, StopIteration):
        pass

    warnings.warn(f"Invalid narration string: {response}")
    return "", None


def narrate(tile, start, end):
    global MESSAGES, APICOSTS

    # prefill = f'<narration i="{i}" startTime="{start}" endTime="{end}">'

    prefill = '<narration novelty="'
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

    text, novelty = extract_narration_and_novelty(narration)

    if novelty > NOVELTY_THRESHOLD:
        info(f"[{novelty}] {text}", extra={"image": tile})

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