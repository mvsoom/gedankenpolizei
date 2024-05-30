import warnings
from xml.etree import ElementTree

from anthropic import Anthropic

import seer.env as env
from seer.image.frame import encode_image
from seer.log import debug, info
from seer.narrate import (
    IMAGE_MAX_SIZE,
    MAX_TOKENS,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    SYSTEM_PROMPT,
)
from seer.narrate.cost import APICosts
from seer.util import mask_base64_messages

CLIENT = Anthropic(api_key=env._ANTHROPIC_API_KEY)

MESSAGES = []
APICOSTS = APICosts(MODEL_NAME)


def extract_narration_and_novelty(response):
    try:
        root = ElementTree.fromstring(response)
        narration = next(root.iter("narration"))
        text = narration.text if narration.text else ""
        novelty = narration.get("novelty") if "novelty" in narration.attrib else None
        return text, novelty
    except (ElementTree.ParseError, StopIteration):
        pass

    warnings.warn(f"Invalid narration string: {response}")
    return "", None


def describe(i, start, end, tile, stream_text=True):
    global MESSAGES, APICOSTS

    encoded_jpeg = encode_image(tile, max_size=IMAGE_MAX_SIZE)

    # prefill = f'<narration i="{i}" startTime="{start}" endTime="{end}">'

    prefill = '<narration novelty="'

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

    debug(f"Sending: {mask_base64_messages(MESSAGES)}")

    # print(MESSAGES)

    print(len(MESSAGES))

    response = CLIENT.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        temperature=MODEL_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=MESSAGES,
        stop_sequences=["</narration>"],
    )

    APICOSTS.ingest(response)
    APICOSTS.log_current_costs(info)

    narration = prefill + response.content[0].text + "</narration>"

    text, novelty = extract_narration_and_novelty(narration)

    if int(novelty) > 20:
        info(f"[{novelty}] {text}", extra={"image": tile})

    debug(narration)

    # Insert the answer into the messages
    last = MESSAGES[-1]
    assert last["role"] == "assistant"
    last["content"][0]["text"] = narration

    # If not novel enough, forget the current interaction
    if int(novelty) <= 20:
        MESSAGES = MESSAGES[:-2]

    IMAGE_MEMORY_SIZE = 1
    max_messages = 2 * IMAGE_MEMORY_SIZE

    if len(MESSAGES) > max_messages:  # fails for memoriy size = 0
        MESSAGES = MESSAGES[-max_messages:]

    return narration