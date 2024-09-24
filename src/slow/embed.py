"""Embedding algebra"""

import numpy as np
from numpy.linalg import norm
from vertexai.language_models import TextEmbeddingInput

from src.vertex import embedder

MODEL = embedder()
DTYPE = np.float32


def zero():
    return np.zeros(MODEL.dimension, dtype=DTYPE)


def allnan():
    return np.full(MODEL.dimension, np.nan, dtype=DTYPE)


def random():
    e = np.random.randn(MODEL.dimension).astype(DTYPE)
    return e / norm(e)


def embed(
    text_input,
    dimension=MODEL.dimension,
    max_batch_size=MODEL.max_batch_size,
    task=MODEL.task,
):
    """Embed a single text or list (batch) of texts

    If text_input is a list, the output is a 2D array with one embedding per row; otherwise just the embedding vector
    """
    is_batch = isinstance(text_input, list)
    texts = text_input if is_batch else [text_input]

    if len(texts) > max_batch_size:
        batches = [
            texts[i : i + max_batch_size] for i in range(0, len(texts), max_batch_size)
        ]
        return np.vstack(
            [embed(batch, dimension, max_batch_size, task) for batch in batches]
        )

    inputs = [TextEmbeddingInput(text, task) for text in texts]

    embeddings = MODEL.get_embeddings(
        inputs, auto_truncate=True, output_dimensionality=dimension
    )

    embeddings = np.vstack([embedding.values for embedding in embeddings], dtype=DTYPE)

    # Impose normalization!
    embeddings = embeddings / norm(embeddings, axis=1)[:, None]

    return embeddings.squeeze()


def compute_bias_matrix(overall_multiplier, directions):
    def construct_bias_direction(d):
        bd = d["multiplier"] * (embed(d["to"]) - embed(d["from"]))
        return overall_multiplier * bd

    if directions:
        bs = [construct_bias_direction(d) for d in directions]
        B = np.stack(bs, axis=-1)  # (embedding_dimension, num_vectors)
    else:
        B = zero()[:, None]

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