"""Embedding algebra"""

import numpy as np
from google.api_core.exceptions import InvalidArgument
from numpy.linalg import norm
from vertexai.language_models import TextEmbeddingInput

from src.vertex import embedder

MODEL = embedder()
DTYPE = np.float32  # Don't set to np.float64, as it will cause memory issues


def zero_vector():
    return np.zeros(MODEL.dimension, dtype=DTYPE)


def allnan_vector():
    return np.full(MODEL.dimension, np.nan, dtype=DTYPE)


def is_valid_vector(embedding):
    return not np.any(np.isnan(embedding))


def random_vector():
    e = np.random.randn(MODEL.dimension).astype(DTYPE)
    return e / norm(e)


def embed(
    text_input,
    dimension=MODEL.dimension,
    task=MODEL.task,
):
    """Embed a single string and output the normalized embedding vector"""
    inputs = [TextEmbeddingInput(text_input, task)]

    try:
        embeddings = MODEL.get_embeddings(
            inputs, auto_truncate=True, output_dimensionality=dimension
        )
    except InvalidArgument as e:
        # TODO: handle too long inputs -- maybe by truncating from beginning or end?
        # Then set auto_truncate=False!
        # Example text: "400 Input texts at positions {0} are longer than the maximum number of tokens for this model (2048). Actual token counts: {42908}"
        # See reembed.ipynb for more details
        raise e

    embedding = np.array(embeddings[0].values)
    embedding /= norm(embedding)
    return embedding.astype(DTYPE)


def compute_bias_matrix(overall_multiplier, directions):
    def construct_bias_direction(d):
        bd = d["multiplier"] * (embed(d["to"]) - embed(d["from"]))
        return overall_multiplier * bd

    if directions:
        bs = [construct_bias_direction(d) for d in directions]
        B = np.stack(bs, axis=-1)  # (embedding_dimension, num_vectors)
    else:
        B = zero_vector()[:, None]

    return B


def bias_coefficients(c, intensity):
    assert 0.0 <= intensity <= 1.0
    return (1 - intensity) * c + intensity * np.maximum(1, c)


def bias_step(step, bias_matrix, bias_projector, intensity):
    """Apply a bias to a step in the embedding space by changing its direction while retaining its norm

    Here step is the direction vector to be biased (nudged) towards the bias_matrix B, which is a matrix holding the bias directions as columns
    The bias_projector B^+ is simply the pseudo-inverse of B
    The intensity parameter controls the strength of the bias, with 0 being no bias and 1 being full bias, amounting to growing the projections of step onto B to be at least of size 1
    """
    # Coordinates of the projected step in the bias hyperplane
    c = bias_projector @ step

    projected = bias_matrix @ c
    orthogonal = step - projected
    # step == projected + orthogonal

    biased_projection = bias_matrix @ bias_coefficients(c, intensity)
    biased_step = biased_projection + orthogonal
    # step != biased_projection + orthogonal unless intensity == 0

    # biased_projection can have arbitrary size, so we renormalize to step length
    biased_step = norm(step) * biased_step / norm(biased_step)

    return biased_step