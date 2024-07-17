import os

import dotenv
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)

dotenv.load_dotenv()

project_id = os.getenv("PROJECT_ID")
if not project_id:
    raise ValueError("PROJECT_ID token is not set in the .env file")

# TODO: make location and model configurable

vertexai.init(project=project_id, location="europe-west1")

GEMINI_FLASH = GenerativeModel(model_name="gemini-1.5-flash-001")

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}
