"""Vet posts automatically with few shot Gemini"""

import argparse
import sys
import time

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

{{EXAMPLES}}
Here is the post:
```
{{POST}}
```

Output only GOOD or BAD{{EXPLAIN}}. Priors: p(GOOD) = 0.2, p(BAD) = 0.8.\
"""  # ~220 tokens

# TODO: Independent of their length, GOOD posts are raw, ...
# TODO: BAD posts include specifically human-identifying properties, situations or activities (age, home, sex, family, friends, job, etc.): ...


def ask_gemini(post, explain=False, examples=None):
    """Post is a the title + body of a Reddit post where sentences are separated by newlines."""
    query = PROMPT.replace("{{POST}}", post)

    if explain:
        generation_config = None
        query = query.replace(
            "{{EXPLAIN}}", " followed by a one-sentence justification"
        )
    else:
        generation_config = GenerationConfig(max_output_tokens=1)  # Only GOOD or BAD
        query = query.replace("{{EXPLAIN}}", "")

    if examples:
        text = "Here are some examples of GOOD and BAD posts:\n"

        for label, sample in examples:
            text += f"```\n{sample['post']}\n``` => {label}\n"

        query = query.replace("{{EXAMPLES}}", text)
    else:
        query = query.replace("{{EXAMPLES}}", "")

    t = time.time()
    response = model.generate_content(
        query,
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    dt = time.time() - t

    reply = response.text

    if explain:
        reply += " (took {:.2f}s)".format(dt)

    return reply


def main(args):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "postfile", help="Post .feather file containing posts to automatically vet"
    )
    parser.add_argument("vetfile", help="Output vet .feather file to append to")
    parser.add_argument(
        "--vetted",
        default=None,
        help="Optional vet .feather file containing references to vetted posts for few shot learning",
    )
    parser.add_argument(
        "-n", type=int, default=sys.maxsize, help="Number of posts to vet"
    )

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))