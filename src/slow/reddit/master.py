"""Join and process normalized subreddits into master database"""

import argparse
import pandas as pd
from sys import exit
import patterns
import re


def read_dfs(inputs):
    dfs = [pd.read_hdf(input) for input in inputs]

    for df in dfs:
        if df.index.name != "id" or df.index.dtype != "object":
            raise ValueError(
                "All input DataFrames must have an index named 'id' and of type 'str'"
            )

    df = pd.concat(dfs)

    if df.index.has_duplicates:
        df = df.reset_index().drop_duplicates(subset="id", keep="first").set_index("id")

    return df


def apply(f, column, show_progress):
    if show_progress:
        try:
            from tqdm import tqdm

            tqdm.pandas()
            result = column.progress_apply(f)
        except ImportError:
            result = column.apply(f)
    else:
        result = column.apply(f)
    return result


COMPILED_LABEL_PATTERNS = {
    category: re.compile("|".join(patterns), flags=re.IGNORECASE)
    for category, patterns in patterns.LABEL_PATTERNS.items()
}


def label(text):
    return set(
        category
        for category, pattern in COMPILED_LABEL_PATTERNS.items()
        if pattern.search(text)
    )


def embed(text):
    return text


def verbose(*_, **__):
    pass


def main(args):
    verbose = print if args.verbose else void

    df = read_dfs(args.inputh5)
    if args.downsample:
        df = df.sample(n=args.downsample)
    verbose(f"Read {len(df)} rows from {len(args.inputh5)} files")

    df = df[["created_utc", "subreddit", "author", "post"]]

    if args.label:
        verbose("Labeling posts")
        df["labels"] = apply(label, df["post"], show_progress=args.verbose)

    if args.embed:
        verbose("Embedding posts")
        df["embedding"] = apply(embed, df["post"], show_progress=args.verbose)

    verbose(f"Writing result to {args.outputh5}")
    df.to_hdf(args.outputh5, key="df", mode="w")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("inputh5", nargs="+", help="HDF5 files")
    parser.add_argument(
        "--outputh5",
        default="master.h5",
        help="Output HDF5 file to (over)write result to (default: master.h5)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument(
        "--downsample",
        type=int,
        default=0,
        help="Downsample to {downsample} rows for testing purposes",
    )
    parser.add_argument(
        "--label",
        action="store_true",
        help="Label the posts into a column 'labels'",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed the posts into a column 'embedding'",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))
