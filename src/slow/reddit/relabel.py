"""Relabel a post.h5 file"""

import argparse
import pandas as pd
from sys import exit


def main(args):
    df = pd.read_hdf(args.inputh5)

    verbose("Rabeling posts")
    from makeposts import label

    df["labels"] = label(df["post"], show_progress=args.verbose)

    verbose(f"Writing {len(df)} rows to {args.inputh5}")
    df.to_hdf(args.inputh5, key="df", mode="w")

    return 0


def void(*_, **__):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("inputh5", help="HDF5 file containing posts to relabel")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()

    verbose = print if args.verbose else void

    exit(main(args))
