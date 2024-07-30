import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

from src.config import CONFIG
from src.log import verbose
from src.slow.embed import bias_step, embed, zero

load_dotenv()

HF_REPO_ID = CONFIG("slow.reddit.hf_repo_id")
HF_SLOW_THOUGHTS_FILE = CONFIG("slow.reddit.hf_slow_thoughts_file")


def _load_slow_thoughts():
    HF_TOKEN_READ = os.getenv("HF_TOKEN_READ")
    if not HF_TOKEN_READ:
        raise ValueError("`HF_TOKEN_READ` token is not set in the .env file")

    # Retrieve the file from HF or cache
    downloaded_file_path = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=HF_SLOW_THOUGHTS_FILE,
        repo_type="dataset",
        use_auth_token=HF_TOKEN_READ,
    )

    slowdf = pd.read_feather(downloaded_file_path)
    verbose(f"Loaded {len(slowdf)} slow thoughts from {downloaded_file_path}")
    return slowdf


SLOWDF = _load_slow_thoughts()


def _compute_bias_matrix():
    overall_multiplier = CONFIG("slow.bias.overall_multiplier")

    def construct_bias_direction(d):
        bd = d["multiplier"] * (embed(d["to"]) - embed(d["from"]))
        return overall_multiplier * bd

    directions = CONFIG("slow.bias.directions")
    if directions:
        bs = [construct_bias_direction(d) for d in directions]
        B = np.stack(bs, axis=-1)  # (embedding_dimension, num_vectors)
    else:
        B = zero()[:, None]

    return B


BIAS_MATRIX = _compute_bias_matrix()
BIAS_PROJECTOR = np.linalg.pinv(BIAS_MATRIX)
INTENSITY = CONFIG("slow.bias.intensity")

MAX_STEPS = CONFIG("slow.walk.max_steps")


def nearest_slow_thought(embedding): ...


def walk(last, current):
    step = embed(current) - embed(last)

    biased_step = bias_step(step, BIAS_MATRIX, BIAS_PROJECTOR, INTENSITY)

    for _ in range(MAX_STEPS):
        current = current + biased_step

        candidate = nearest_slow_thought(current)
        if not_seen_yet(candidate):
            return candidate

        biased_step *= 2

    # Walking failed; teleport to a new random SLOW thought
    return new_slow_thought()


def sample_thought():
    return SLOWDF.sample().iloc[0].thought
