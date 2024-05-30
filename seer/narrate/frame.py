import base64
import warnings
from io import BytesIO
from time import time
from xml.etree import ElementTree

from anthropic import Anthropic
from PIL import Image

import seer.env as env
from seer.log import debug, info
from seer.util import mask_base64_messages, read_prompt_file

IMAGE_MAX_SIZE = (1024, 1024)  # Restriction from the Claude API
MAX_TOKENS = 300
# MODEL_NAME = "claude-3-opus-20240229"
# MODEL_NAME = "claude-3-sonnet-20240229"
MODEL_NAME = env.NARRATE_MODEL_NAME
MODEL_TEMPERATURE = env.NARRATE_MODEL_TEMPERATURE
SYSTEM_PROMPT = read_prompt_file(env.NARRATE_SYSTEM_PROMPTFILE)

CLIENT = Anthropic(api_key=env._ANTHROPIC_API_KEY)


def encode_image(image, max_size=IMAGE_MAX_SIZE):
    # Resize the image if it exceeds the maximum size
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    image_data = BytesIO()
    image.save(image_data, format="JPEG")
    image_data.seek(0)
    base64_encoded = base64.b64encode(image_data.getvalue()).decode("utf-8")

    return base64_encoded


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


MESSAGES = []

# Pricing:
# Haiku
# Input: $0.25 / MTok
# Output: $1.25 / MTok
INPUT_TOKENS = []
OUTPUT_TOKENS = []
PRICE = (0.25 / 1e6, 1.25 / 1e6)


def calculate_average_cost():
    if "haiku" not in MODEL_NAME:
        return float("nan")

    if len(INPUT_TOKENS) <= 1:
        return float("nan")

    totalcost = 0.0
    dt = 0.0

    for usage, price in zip((INPUT_TOKENS, OUTPUT_TOKENS), PRICE):
        t, tok = zip(*usage)
        dt += t[-1] - t[0]
        totalcost += sum(tok) * price

    dt /= 2

    # Convert to hourly rate as dt is in seconds
    return totalcost / dt * 3600


def describe(i, start, end, tile, stream_text=True):
    global MESSAGES
    encoded_jpeg = encode_image(tile)

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

    debug(mask_base64_messages(MESSAGES))

    # print(MESSAGES)

    response = CLIENT.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        temperature=MODEL_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=MESSAGES,
        stop_sequences=["</narration>"],
    )

    narration = prefill + response.content[0].text + "</narration>"

    INPUT_TOKENS.append((time(), response.usage.input_tokens))
    OUTPUT_TOKENS.append((time(), response.usage.output_tokens))

    cost = calculate_average_cost()

    print(f"Cost: ${cost:.2f}/hour")
    text, novelty = extract_narration_and_novelty(narration)

    if int(novelty) > 0:
        info(f"[{novelty}] {text}", extra={"image": tile})

    debug(narration)

    # Insert the answer into the messages
    last = MESSAGES[-1]
    assert last["role"] == "assistant"
    last["content"][0]["text"] = narration

    if len(MESSAGES) > 4:
        # Retain last 4 messages
        MESSAGES = MESSAGES[-4:]

    return narration
