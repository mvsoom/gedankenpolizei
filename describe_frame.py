import base64
import warnings
from io import BytesIO
from xml.etree import ElementTree

from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

IMAGE_QUALITY = 75
IMAGE_MAX_SIZE = (1024, 1024)

# MODEL_NAME = "claude-3-opus-20240229"
# MODEL_NAME = "claude-3-sonnet-20240229"
MODEL_NAME = "claude-3-haiku-20240307"

MAX_TOKENS = 1000
TEMPERATURE = 0.0
CLIENT = Anthropic()  #  Uses ANTHROPIC_API_KEY env variable


def read_prompt_file(filename):
    with open(filename, "r") as file:
        lines = file.readlines()
    text = ""
    for line in lines:
        if not line.strip().startswith("#"):
            text += line
    return text


SYSTEM_PROMPT = read_prompt_file("prompts/system_prompt")


def encode_image(image, quality=IMAGE_QUALITY, max_size=IMAGE_MAX_SIZE):
    # Resize the image if it exceeds the maximum size
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    image_data = BytesIO()
    image.save(image_data, format="PNG", optimize=True, quality=quality)
    image_data.seek(0)
    base64_encoded = base64.b64encode(image_data.getvalue()).decode("utf-8")

    return base64_encoded


def extract_narration(response):
    try:
        root = ElementTree.fromstring(response)
        narration = next(root.iter("narration"))
        if narration.text:
            return narration.text
    except (ElementTree.ParseError, StopIteration):
        pass

    warnings.warn(f"Invalid narration string: {response}")
    return ""


MESSAGES = []


def describe(i, start, end, tile, stream_text=True):
    global MESSAGES
    encoded_png = encode_image(tile)

    prefill = f'<narration i="{i}" startTime="{start}" endTime="{end}">'

    MESSAGES = MESSAGES + [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": encoded_png,
                    },
                }
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": prefill}]},
    ]

    if stream_text:
        print(prefill)
        narration = prefill

        with CLIENT.messages.stream(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=MESSAGES,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                narration += text
    else:
        response = CLIENT.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=MESSAGES,
        )

        narration = prefill + response.content[0].text

        print(extract_narration(narration))

    # Insert the answer into the messages
    last = MESSAGES[-1]
    assert last["role"] == "assistant"
    last["content"][0]["text"] = narration

    if len(MESSAGES) > 4:
        # Retain last 4 messages
        MESSAGES = MESSAGES[-4:]

    return narration
