"""Relabel a post file"""

import argparse
import pandas as pd
from sys import exit


def main(args):
    df = pd.read_feather(args.postfile)

    verbose("Relabeling posts")
    from makeposts import apply, label

    df["labels"] = apply(df["post"], label, show_progress=args.verbose)

    verbose(f"Writing {len(df)} rows to {args.postfile}")
    df.to_feather(args.postfile, compression="zstd")

    return 0


verbose = print

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "postfile", help="Feather post file containing posts to relabel"
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()
    if not args.verbose:
        verbose = lambda *_, **__: None

    exit(main(args))
