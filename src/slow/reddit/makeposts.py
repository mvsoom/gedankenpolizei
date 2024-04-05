"""Make labeled and embedded posts from normalized submissions"""

import argparse
import os
import pandas as pd
from sys import exit
import patterns
import re
import textwrap
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def formatpost(post, symbol="🟦", width=60):
    # Color the first line (title) in blue
    lines = post.splitlines()
    # lines[0] = f"\033[94m{lines[0]}\033[0m"
    # Separate newlines by symbol
    formattedpost = symbol.join(lines)
    # Wrap the text to 60 characters
    formattedpost = textwrap.fill(formattedpost, width=width)
    return formattedpost


def printpost(post):
    print(formatpost(post))


def read_dfs(inputs):
    dfs = [pd.read_feather(input) for input in inputs]

    for df in dfs:
        if df.index.name != "id" or df.index.dtype != "object":
            raise ValueError("Bad indices")

    df = pd.concat(dfs)

    if df.index.has_duplicates:
        n = len(df)
        df = df.reset_index().drop_duplicates(subset="id", keep="first").set_index("id")
        verbose(f"Dropped {n - len(df)} duplicate rows based on index")

    return df


def downsample(df, args):
    if args.update:
        try:
            # Sample only from rows in df that are not in old
            old = pd.read_feather(args.outputfile)
            new = df[~df.index.isin(old.index)]
            numsamples = min(args.downsample, len(new))
            return new.sample(n=numsamples)
            return new.sample(n=numsamples)
        except FileNotFoundError:
            verbose("Update file not found: sampling from all rows")
    return df.sample(n=args.downsample)


def make_post(normalized_title, normalized_selftext):
    """A post contains newline separated sentence tokens, so each line is a sentence token

    The first line (aka sentence token) is always the normalized title (which may contain multiple natural language sentences (rare), but no newlines).
    The next lines are the sentence tokens of the normalized selftext.
    """
    post = normalized_title.str.replace("\n", " ") + "\n" + normalized_selftext
    return post


COMPILED_LABEL_PATTERNS = {
    category: re.compile("|".join(patterns), flags=re.IGNORECASE)
    for category, patterns in patterns.LABEL_PATTERNS.items()
}


def label(posts, show_progress=False):
    def label_text(text):
        return set(
            category
            for category, pattern in COMPILED_LABEL_PATTERNS.items()
            if pattern.search(text)
        )

    if show_progress:
        try:
            from tqdm import tqdm

            tqdm.pandas()
            result = posts.progress_apply(label_text)
        except ImportError:
            result = posts.apply(label_text)
    else:
        result = posts.apply(label_text)
    return result


def embed(posts, show_progress=False, **encode_kwargs):
    """Embed posts using sentence-transformers

    Note: models have maximum sequence lengths of 256 to 512 tokens (512 tokens ~ 2000 chars ~ 400 words).
    Longer maximum sequence length take considerably longer to embed.
    Texts longer than the maximum sequence length are truncated.
    The embedder is not sensitive to whitespace or newlines.
    """
    model = SentenceTransformer(EMBEDDING_MODEL)
    verbose("Model:", EMBEDDING_MODEL, f"(max_seq_length={model.max_seq_length})")

    sentences = posts.values
    embedding = model.encode(
        sentences,
        show_progress_bar=show_progress,
        batch_size=50,
        **encode_kwargs,
    )  # (len(posts), <embedding dimension>)

    return [np.array(row) for row in embedding]


def write(df, args):
    df.reset_index(inplace=True)
    df.drop_duplicates(subset="id", inplace=True, keep="last")
    df.set_index("id", inplace=True, verify_integrity=True)

    # If file exists and we're not updating, abort
    if (not args.update) and os.path.exists(args.outputfile):
        raise ValueError(f"Output file {args.outputfile} already exists")

    df.to_feather(args.outputfile, compression="zstd")


def main(args):
    df = read_dfs(args.inputfile)

    if not args.downsample:
        args.downsample = len(df)

    df = downsample(df, args)
    verbose(f"Read {len(df)} rows from {len(args.inputfile)} files")

    verbose("Joining titles and selftexts into posts")
    df["post"] = make_post(df["title"], df["selftext"])

    df = df[["created_utc", "subreddit", "author", "post"]]

    verbose("Labeling posts")
    df["labels"] = label(df["post"], show_progress=args.verbose)

    verbose("Embedding posts")
    df["embedding"] = embed(df["post"], show_progress=args.verbose)

    newrows = len(df)
    newrows = len(df)
    if args.update:
        try:
            old = pd.read_feather(args.outputfile)
            df = pd.concat([old, df])
            df = df[~df.index.duplicated(keep="last")]
            newrows = len(df) - len(old)
            newrows = len(df) - len(old)
            verbose("Updating")
        except FileNotFoundError:
            verbose("Update file not found: writing to new file")

    verbose(f"Writing {newrows} new rows to {args.outputfile}")
    write(df, args)

    return 0 if newrows > 0 else 1
    return 0 if newrows > 0 else 1


verbose = print

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "inputfile",
        nargs="+",
        help="Input .feather files containing normalized submissions",
    )
    parser.add_argument(
        "--outputfile",
        default="posts.feather",
        help="Output .feather file to result to (default: posts.feather)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update output file rather than overwriting",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument(
        "--downsample",
        type=int,
        default=0,
        help="Downsample input to {downsample} rows. If --update, sample new rows only",
    )

    # Parse the command line arguments
    args = parser.parse_args()
    if not args.verbose:
        verbose = lambda *_, **__: None

    exit(main(args))
