"""Embedding algebra"""

import sys

import numpy as np
import torch
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer

from src.config import CONFIG

NAME = CONFIG("slow.embed.model.name")
MODEL = SentenceTransformer(NAME)
DIMENSION = MODEL.get_sentence_embedding_dimension()


def zero():
    return np.zeros(DIMENSION)


def tokenize_last(text, truncation_length):
    """Tokenize and truncate to the LAST part of the text"""
    # We use the `truncation=True` and `max_length=sys.maxsize` trick to avoid an harmless log warning
    tokens = MODEL.tokenizer(
        text, padding=True, truncation=True, max_length=sys.maxsize, return_tensors="pt"
    )

    truncated = {k: v[..., -truncation_length:] for k, v in tokens.items()}

    return truncated


def embed(text, truncation_length=MODEL.max_seq_length):
    """Embed a single text or list (batch) of texts

    Note: we don't use the SentenceTransformer.encode() interface for two reasons:
        * It doesn't support truncation to the last part of the text
        * It's so much slower on my CPU for some reason. Batching also makes much less sense for CPU
    """
    is_batch = isinstance(text, list)

    tokens = tokenize_last(text, truncation_length)

    with torch.no_grad():  # https://github.com/UKPLab/sentence-transformers/issues/742#issuecomment-772757207
        model_output = MODEL(tokens)

    embedding = model_output["sentence_embedding"]
    embedding = embedding if is_batch else embedding.squeeze(0)
    return embedding.numpy()


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