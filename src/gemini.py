import os

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

vertexai.init(project=project_id, location=LOCATION)

GEMINI_FLASH = GenerativeModel(model_name=MODEL_FLASH_NAME)

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}
