"""Embedding arithmetic"""

import sys

import numpy as np
import torch
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer

from src.config import CONFIG

NAME = CONFIG("slow.embed.model.name")
MODEL = SentenceTransformer(NAME)


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
        * It's so much slower on my CPU for some reason
    """
    is_batch = isinstance(text, list)

    tokens = tokenize_last(text, truncation_length)

    with torch.no_grad():  # https://github.com/UKPLab/sentence-transformers/issues/742#issuecomment-772757207
        model_output = MODEL(tokens)

    embedding = model_output["sentence_embedding"]
    embedding = embedding if is_batch else embedding.squeeze(0)
    return embedding.numpy()


def compute_projection_matrix(list_of_vectors):
    """Compute the projection matrix from a list of vectors"""
    if not list_of_vectors:
        d = MODEL.get_sentence_embedding_dimension()
        zero = np.zeros((d, d))
        return zero

    B = np.stack(list_of_vectors, axis=-1)  # (embedding_dimension, num_vectors)
    return B @ np.linalg.pinv(B)


def bias_step(step, beta, bias_projection, beta_limit=30.0):
    if beta < beta_limit:
        direction = step + (np.exp(beta) - 1.0) * (bias_projection @ step)
    else:
        # Manually implement the mathematical limit beta -> +infty
        direction = bias_projection @ step

    return norm(step) * (direction / norm(direction))
