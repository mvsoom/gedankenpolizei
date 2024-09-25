import numpy as np

from src.config import CONFIG
from src.log import debug
from src.pinecone import NAMESPACE, resolve_index
from src.slow.embed import (  # Takes a while
    bias_step,
    compute_bias_matrix,
    embed,
    is_valid_vector,
    random_vector,
)

INDEX = resolve_index()

BIAS_MATRIX = compute_bias_matrix(
    CONFIG("slow.bias.overall_multiplier"),
    CONFIG("slow.bias.directions"),
)
BIAS_PROJECTOR = np.linalg.pinv(BIAS_MATRIX)
INTENSITY = CONFIG("slow.bias.intensity")
MAX_STEPS = CONFIG("slow.walk.max_steps")


def ids(history):
    return [h["id"] for h in history]


def sample_random_thought(history=None, maxtries=100):
    for _ in range(maxtries):
        vector = random_vector()
        candidate = nearest_neighbor(vector)
        if history is None or candidate["id"] not in ids(history):
            return candidate

    return candidate


def nearest_neighbor(vector):
    if not is_valid_vector(vector):
        raise ValueError(f"Invalid vector {vector}")

    reply = INDEX.query(
        namespace=NAMESPACE,
        vector=vector,
        top_k=1,
        include_values=True,
        include_metadata=True,
    )

    nn = reply["matches"][0].to_dict()
    return nn


def sample_nearby_thought(walk, start, end):
    current = walk[-1]["values"]

    step = embed(end) - embed(start)

    if np.isclose(np.linalg.norm(step), 0.0):
        # Take a shortcut
        return sample_random_thought(walk)

    biased_step = bias_step(
        step,
        BIAS_MATRIX,
        BIAS_PROJECTOR,
        INTENSITY,
    )

    for i in range(MAX_STEPS):
        debug(
            f"Taking step {i+1}/{MAX_STEPS}: |biased_step| = {np.linalg.norm(biased_step)}"
        )

        current = current + biased_step

        candidate = nearest_neighbor(current)
        if candidate["id"] not in ids(walk):
            return candidate

        biased_step *= 2.0

    return sample_random_thought(walk)
