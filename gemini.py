import time

import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part

project_id = "gen-lang-client-0149736153"

vertexai.init(project=project_id, location="europe-west1")

model = GenerativeModel(model_name="gemini-1.5-flash-001")

# Measure response time
image = Image.load_from_file("logs/images/1718113430.04286790.jpg")

t = time.time()
response = model.generate_content(
    [
        Part.from_image(image),
        "What is shown in this image?",
    ]
)
print(f"Response time: {time.time() - t:.2f}s")
print(response.text)