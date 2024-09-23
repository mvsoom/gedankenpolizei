
"""Narrate frames"""

import base64
import json
from io import BytesIO
from time import time

from PIL import Image
from vertexai.generative_models import Image as GeminiImage

from src.config import CONFIG
from src.log import debug
from src.vertex import (
    gemini,
    read_prompt_file,
)

SYSTEM_PROMPT = read_prompt_file(CONFIG("fast.model.system_prompt_file"))

MODEL = gemini(
    CONFIG("fast.model.name"),
    generation_config={
        "temperature": CONFIG("fast.model.temperature"),
        "response_mime_type": "application/json",
    },
    system_instruction=SYSTEM_PROMPT,
)


class Frame:  # Cannot subclass PIL.Image.Image directly, so wrap it awkwardly
    def __init__(self, rawjpeg, max_size=None):
        self.timestamp = time()
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

    def encode64(self):
        return base64.b64encode(self.jpeg()).decode("utf-8")

    def gemini_image(self):
        return GeminiImage.from_bytes(self.jpeg())

    def precaption(self, t=None):
        dt = (t or time()) - self.timestamp
        caption = f"{dt:.1f} sec ago:"
        return caption

    def prompt(self, t=None):
        return [self.precaption(t), self.gemini_image()]


def join(prompts, sep=None):
    def iter():
        for prompt in prompts:
            for part in prompt:
                yield part
            if sep:
                yield sep

    return list(iter())[:-1]


class Memory:
    def __init__(self, config):
        self.max_size = config("fast.memory.max_size")
        self.scaling = config("fast.memory.scaling")
        self.frames = []
        self.outputs = []

    def remember(self, frame, output):
        if self.scaling != 1.0:
            self.downsize_frames()

        self.frames.append(frame)
        self.outputs.append(output)

        if len(self.frames) > self.max_size:
            self.frames.pop(0)
            self.outputs.pop(0)

    def last_narration(self):
        if self.outputs:
            return self.outputs[-1]["narration"]
        return None

    def downsize_frames(self):
        for frame in self.frames:
            frame.downsize(self.scaling)

    def prompts(self, t=None):
        return [frame.prompt(t) for frame in self.frames]

    def log(self, level=debug):
        level("Memory contents", extra={"images": self.frames})


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

    return output


def narrate(past, now):
    """Narrate the `now` frame conditioned on the `past` outputs of this function"""
    prompt = join(past.prompts() + [now.prompt()], sep="\n")
    debug(f"Sending message:\n{prompt}")
    reply = MODEL.generate_content(prompt)
    debug(f"Reply:\n{reply}")

    output = parse_reply(reply)
    return output