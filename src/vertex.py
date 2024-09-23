"""Gemini API wrapper for Vertex AI"""

import os
from time import time

import dotenv
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)
from vertexai.language_models import TextEmbeddingModel

from src.config import CONFIG

dotenv.load_dotenv()

project_id = os.getenv("VERTEXAI_PROJECT_ID")
if not project_id:
    raise ValueError("VERTEXAI_PROJECT_ID token is not set in the .env file")


LOCATION = CONFIG("gemini.location")
MODEL_FLASH_NAME = CONFIG("gemini.model.flash.name")

COST_PER_IMAGE = CONFIG("gemini.model.flash.cost_per_image")
COST_PER_INPUT_CHAR = CONFIG("gemini.model.flash.cost_per_input_char")
COST_PER_OUTPUT_CHAR = CONFIG("gemini.model.flash.cost_per_output_char")


SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

vertexai.init(project=project_id, location=LOCATION)


def gemini(model_shorthand, **kwargs):
    model_name = CONFIG["gemini"]["model"][model_shorthand]["name"]
    config = dict(
        model_name=model_name,
        safety_settings=SAFETY_SETTINGS,
    )
    config.update(kwargs)
    model = GenerativeModel(**config)
    # TODO: attach COST_PER_* costs to the model object rather than to this module
    model.name = model_name
    return model


def embedder():
    model_name = CONFIG("slow.embed.model.name")
    model = TextEmbeddingModel.from_pretrained(model_name)

    model.dimension = CONFIG("slow.embed.model.dimension")
    model.task = CONFIG("slow.embed.model.task")
    model.max_batch_size = CONFIG("slow.embed.model.max_batch_size")

    return model


def read_prompt_file(filename):
    """Note that for Gemini on Vertex AI whitespace is not billed"""
    with open(filename, "r") as file:
        lines = file.readlines()
    text = ""
    for line in lines:  # Remove comments
        if not line.strip().startswith("#"):
            text += line
    return text


def replace_variables(prompt, **variables):
    """Replace {{VARIABLE_NAME}} placeholders in the prompt with actual values from the variables dictionary"""
    deferred = []
    for name, value in variables.items():
        placeholder = "{{" + name + "}}"
        if isinstance(value, str):
            prompt = prompt.replace(placeholder, value)
        elif value is None:
            prompt = prompt.replace(placeholder, "")
        else:
            deferred.append((name, value))

    if not deferred:
        return prompt

    prompts = [prompt]

    for name, value in deferred:
        placeholder = "{{" + name + "}}"

        def replace_variable_by_object(prompt):
            parts = prompt.split(placeholder)

            def gather():
                for p in parts:
                    yield p
                    yield value

            return list(gather())[:-1]

        prompts = [replace_variable_by_object(p) for p in prompts if isinstance(p, str)]
        prompts = [  # Flatten
            item for sublist in prompts if isinstance(sublist, list) for item in sublist
        ]

    return prompts


class Costs:  # TODO
    def __init__(self):
        self.start = time()
        self.total = 0.0

    def ingest(self, cost):
        self.total += cost

    def current_rate(self):  # Per hour
        dt = time() - self.start
        return self.total / dt * 3600.0

    def log_current_costs(self, log):
        rate = self.current_rate()
        log(f"Gemini cost: ${rate:.2f}/hour (total: ${self.total:.4f})")