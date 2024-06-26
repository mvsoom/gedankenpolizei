import time

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Image,
)

project_id = "gen-lang-client-0149736153"

vertexai.init(project=project_id, location="europe-west1")

model = GenerativeModel(model_name="gemini-1.5-flash-001")

safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Measure response time
image = Image.load_from_file("logs/images/1718113430.04286790.jpg")

t = time.time()
response = model.generate_content(
    [
        image,
        "What is shown in this image?",
    ],
    safety_settings=safety_settings,
)
print(f"Response time: {time.time() - t:.2f}s")
print(response.text)

