import os
from time import time

import dotenv
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)

from src.config import CONFIG

dotenv.load_dotenv()

project_id = os.getenv("PROJECT_ID")
if not project_id:
    raise ValueError("PROJECT_ID token is not set in the .env file")


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


def gemini(**kwargs):
    config = dict(
        model_name=MODEL_FLASH_NAME,
        safety_settings=SAFETY_SETTINGS,
    )
    config.update(kwargs)
    model = GenerativeModel(**config)
    # TODO: attach COST_PER_* costs to the model object rather than to this module
    model.name = MODEL_FLASH_NAME
    return model


def read_prompt_file(filename):
    """Note that for Gemini whitespace are not billed"""
    with open(filename, "r") as file:
        lines = file.readlines()
    text = ""
    for line in lines:  # Remove comments
        if not line.strip().startswith("#"):
            text += line
    return text


def replace_variables_in_prompt(prompt, variables_dict):
    """Replace {{VARIABLE_NAME}} placeholders in the prompt with actual values from the variables dictionary."""
    for var_name, var_value in variables_dict.items():
        prompt = prompt.replace("{{" + var_name + "}}", str(var_value))

    return prompt


class Costs:
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