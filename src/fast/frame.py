
"""Narrate frames"""

import json
from io import BytesIO
from time import time

from PIL import Image
from vertexai.generative_models import Content, Part
from vertexai.generative_models import Image as GeminiImage

from src.config import CONFIG
from src.gemini import (
    COST_PER_IMAGE,
    COST_PER_INPUT_CHAR,
    COST_PER_OUTPUT_CHAR,
    Costs,
    gemini,
    read_prompt_file,
)
from src.log import debug, info

SYSTEM_PROMPT = read_prompt_file(CONFIG("fast.model.system_prompt_file"))
TEMPERATURE = CONFIG("fast.model.temperature")

MODEL = gemini(
    generation_config={
        "temperature": TEMPERATURE,
        "response_mime_type": "application/json",
    },
    system_instruction=SYSTEM_PROMPT,
)

COSTS = Costs()


class Frame:  # Cannot subclass PIL.Image.Image directly, so wrap it awkwardly
    def __init__(self, rawjpeg, max_size=None, timestamp=None):
        self.timestamp = timestamp if timestamp else time()
        self.image = Image.open(BytesIO(rawjpeg))

        if max_size:
            if self.image.size[0] > max_size[0] or self.image.size[1] > max_size[1]:
                self.thumbnail(max_size)

    def save(self, path):
        self.image.save(path)

    def thumbnail(self, size):
        """Downscale to `size` in place"""
        self.image.thumbnail(size, Image.Resampling.LANCZOS)

    def downsize(self, factor):
        """Downsize by `factor` in place"""
        assert factor <= 1.0
        new_size = [int(x * factor) for x in self.image.size]
        self.thumbnail(new_size)

    def jpeg(self):
        with BytesIO() as f:
            self.image.save(f, "JPEG")
            return f.getvalue()

    def gemini_image(self):
        return GeminiImage.from_bytes(self.jpeg())

    def caption(self, t=None):
        dt = (t or time()) - self.timestamp
        caption = f"({dt:.1f} sec ago)"
        return caption

    def prompt(self, t=None):
        return [
            Part.from_image(self.gemini_image()),
            Part.from_text(self.caption(t)),
        ]

    def cost(self):
        """Cost of this frame in $ according to https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models"""
        return COST_PER_IMAGE + COST_PER_INPUT_CHAR * len(self.caption(None))


def _flatten(iteratable):
    return [item for sublist in iteratable for item in sublist]


class Memory:
    def __init__(self, config):
        self.max_size = config("fast.memory.max_size")
        self.scaling = config("fast.memory.scaling")
        self.memory = []

    def remember(self, frame, output):
        if self.scaling != 1.0:
            self.downsize_frames()

        # TODO: withholding the narrations of the memories on the chat prompt avoids the model getting stuck into a repetitive loop and appears to works equally well, so for now we only output novelties
        reply = json.dumps(
            {
                "novelty": output["novelty"],
            }
        )  # output["reply"]

        self.memory.append((frame, reply))

        if len(self.memory) > self.max_size:
            self.memory.pop(0)

    def downsize_frames(self):
        for frame, _ in self.memory:
            frame.downsize(self.scaling)

    def chat_history(self, t=None):
        return _flatten(
            [
                Content(
                    parts=frame.prompt(t),
                    role="user",
                ),
                Content(
                    parts=[Part.from_text(reply)],
                    role="model",
                ),
            ]
            for (frame, reply) in self.memory
        )

    def log(self, level=debug):
        try:
            frames, replies = zip(*self.memory)
            level("\n".join(("Memory contents:",) + replies), extra={"images": frames})
        except ValueError:
            level("Memory contents: empty")

    def cost(self):
        return sum(
            frame.cost() + COST_PER_INPUT_CHAR * len(reply)
            for frame, reply in self.memory
        )


def parse_reply(reply):
    output = json.loads(reply.text)

    allowed_keys = {"novelty", "narration"}

    if "novelty" not in output:
        raise KeyError(f"Reply is missing `novelty` key: {output}")
    if "narration" not in output:
        output["narration"] = None

    unexpected_keys = set(output.keys()) - allowed_keys
    if unexpected_keys:
        raise KeyError(f"Reply contains unexpected keys: {unexpected_keys}")

    output["reply"] = reply.text

    return output


def narrate(past, now):
    """Narrate the `now` frame conditioned on the `past` outputs of this function"""
    # Setup a multi-turn chat session with JSON replies
    chat_session = MODEL.start_chat(history=past.chat_history(time()))
    prompt = now.prompt()

    debug("Sending message")
    reply = chat_session.send_message(prompt)
    debug(f"Reply:\n{reply}")

    # Log costs
    past_cost = past.cost()
    now_cost = now.cost() + COST_PER_OUTPUT_CHAR * len(reply.text)
    COSTS.ingest(past_cost + now_cost)
    COSTS.log_current_costs(info)

    output = parse_reply(reply)
    return output