"""Vet posts automatically with few shot Gemini"""


import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
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

PROMPT = """\
Evaluate the Reddit post as GOOD or BAD. GOOD posts are interesting starting points for an artificial stream of consciousnes of an AI camera sculpture hanging in an art installation. GOOD posts contain everyday bland or strikingly original thoughts, creative copypasta, or moving utterances an AI could have. Independent of their length, GOOD posts are raw, human-like, with cynicism, elation, humor, internet poetry, or absurdity, referencing "seeing" humans or reflecting about people, with timeless, "small" worldly thoughts.

BAD posts include specifically human-identifying properties, situations or activities (age, home, sex, family, friends, job, etc.): an AI aspiring to BE HUMAN but knowing that IT IS NOT and that cannot talk, hear or move about, wouldn't have these thoughts. BAD posts are simply too recognizable as (toxic?) Reddit posts rather than inner monologue.
{{OPTIONAL_EXAMPLES}}
Here is the post:
```
{{POST}}
```

Given the priors `p(GOOD) = 0.25`, `p(BAD) = 1 - p(GOOD) = 0.75`, output a single float representing `p(GOOD|post)` followed by a one-sentence justification.\
"""  # ~220 tokens
# Note: "followed by a one-sentence justification" is crucial for the model to generate output starting with a float


def ask_gemini(post, explain=False, examples=None):
    """Post is a the title + body of a Reddit post where sentences are separated by newlines."""
    query = PROMPT.replace("{{POST}}", post)

    if explain:
        # Let the LLM finish with the one-sentence justification
        generation_config = None
    else:
        # Cut the LLM short after the float
        generation_config = GenerationConfig(max_output_tokens=4)

    if examples:
        text = "\nHere are some examples of GOOD and BAD posts:\n"

        for label, sample in examples:
            text += f"```\n{sample['post']}\n``` => {label}\n"

        query = query.replace("{{OPTIONAL_EXAMPLES}}", text)
    else:
        query = query.replace("{{OPTIONAL_EXAMPLES}}", "")

    response = model.generate_content(
        query,
        generation_config=generation_config,
        safety_settings=safety_settings,
    )

    reply = response.text

    return reply
