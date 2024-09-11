# /usr/bin/env python
import numpy as np
import pandas as pd
from tqdm import tqdm

from src.slow.df import SLOWDF
from src.slow.embed import embed
from src.slow.reddit.makeposts import apply

BATCH_SIZE = 200
OUTPUT_FILE = "data/reddit/slow_thoughts_reembedded_google.feather"

DIM = 384

try:
    df = pd.read_feather(OUTPUT_FILE)
    print("Loaded existing embeddings")
except FileNotFoundError:
    print("Starting from scratch")
    df = SLOWDF
    df["embedding"] = [np.zeros(DIM, dtype="float32") for _ in range(len(df))]


embeddings = np.stack(df["embedding"], dtype="float32")
norms = np.linalg.norm(embeddings, axis=1)

# Find indices where the elements are close to zero; they are marked for reembedding
SMALL = 1e-3
indices = np.where(np.abs(norms) < SMALL)[0]

print("Working on", len(indices), "embeddings in batches of", BATCH_SIZE)

# Iterate over batches in indices
for i in tqdm(range(0, len(indices), BATCH_SIZE), desc="Batches"):
    batch = indices[i : i + BATCH_SIZE]

    df.loc[batch, "embedding"] = apply(df.loc[batch, "text"], embed, show_progress=True)

    df.to_feather(OUTPUT_FILE, compression="zstd")
    print("Written to", OUTPUT_FILE)
