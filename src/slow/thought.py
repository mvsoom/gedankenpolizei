import numpy as np

from src.config import CONFIG
from src.log import info
from src.slow.df import SLOWDF  # Takes a while
from src.slow.embed import (  # Takes a while
    bias_step,
    compute_bias_matrix,
    embed,
)

EMBEDDINGS = np.stack(SLOWDF["embedding"], dtype="float32")

BIAS_MATRIX = compute_bias_matrix(
    CONFIG("slow.bias.overall_multiplier"),
    CONFIG("slow.bias.directions"),
)
BIAS_PROJECTOR = np.linalg.pinv(BIAS_MATRIX)
INTENSITY = CONFIG("slow.bias.intensity")
MAX_STEPS = CONFIG("slow.walk.max_steps")


def sample_random_thought(history=None):
    if history is None:
        return SLOWDF.sample()
    else:
        # Return unique sample not in `history`
        return SLOWDF.loc[~SLOWDF.index.isin(history.index)].sample()


def nearest_neighbor(query, embeddings=EMBEDDINGS):
    """Find the nearest neighbor in `SLOWDF` to `query`

    Note: assuming all embeddings are normalized, we can minimize distance by maximizing dot product"""
    dp = np.dot(embeddings, query)
    return SLOWDF.iloc[np.argmax(dp)]


def sample_nearby_thought(walk, start, end):
    current = walk.iloc[-1].embedding

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
        info(
            f"Taking step {i+1}/{MAX_STEPS}: |biased_step| = {np.linalg.norm(biased_step)}"
        )

        current = current + biased_step

        candidate = nearest_neighbor(current)
        if not candidate.index.isin(walk.index):
            return candidate

        biased_step *= 2.0

    return sample_random_thought(walk)
