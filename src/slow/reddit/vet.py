import argparse
from datetime import datetime
import pandas as pd
import numpy as np
import curses
from sys import exit
from lib import tui

INSTRUCTIONS = (
    "Vetting: press '+' for positive, '-' for negative, ENTER to skip, 'q' to quit"
)
PLUS, MINUS, ENTER = ord("+"), ord("-"), ord("\n")
EXIT = ord("q")

SCORE = {
    PLUS: 1,
    ENTER: 0,
    MINUS: -1,
}


def stratified_sample(df, among):
    subclasses = df[among].unique()
    c = np.random.choice(subclasses)
    return df[df[among] == c].sample(n=1)


def unique_stratified_sample(
    df, among, vetdf, maxtries=100, matchcols=["id", "subreddit", "author"]
):
    if vetdf.empty:
        return stratified_sample(df, among)

    tries = 0
    while tries < maxtries:
        sample = stratified_sample(df, among)

        match = (sample[matchcols].values == vetdf[matchcols].values).all(axis=1).any()

        if not match:
            return sample
        else:
            tries += 1

    raise ValueError("Can't find unique stratified sample")


def read(inputcsv):
    dtype = {
        "created_utc": float,
        "id": object,
        "subreddit": object,
        "author": object,
        "title": object,
        "selftext": object,
        "ups": int,
        "downs": int,
        "normalized": object,
    }

    df = pd.read_csv(
        inputcsv,
        keep_default_na=False,
        na_filter=False,
        dtype=dtype,
    )

    return df


def main(args):
    dfs = [pd.read_hdf(inputh5) for inputh5 in args.inputh5]
    df = pd.concat(dfs, ignore_index=True)
    df.sort_values(by=["subreddit", "created_utc"], inplace=True)

    try:
        vetdf = pd.read_hdf(args.outputh5)
    except FileNotFoundError:
        vetdf = pd.DataFrame()

    return vet(args, df, vetdf)


utc = datetime.utcfromtimestamp


def vet(args, df, vetdf):
    def get_sample():
        sample = unique_stratified_sample(df, "subreddit", vetdf)
        # subreddit = sample["subreddit"].values[0]
        # timestamp = sample["created_utc"].values[0]
        sample_text = sample["normalized"].values[0]
        return sample, sample_text

    def keypressed(screen, c):
        if c in [PLUS, ENTER, MINUS]:
            nonlocal sample, vetdf, args
            vetted_sample = sample.copy()
            vetted_sample["score"] = SCORE[c]
            vetdf = pd.concat([vetdf, vetted_sample])
            vetdf.to_hdf(args.outputh5, key="df", mode="w")

            sample, text = get_sample()
            screen.text = text
            screen.display()
        elif c == EXIT:
            return (continue_loop := False)
        return (continue_loop := True)

    sample, text = get_sample()
    screen = tui.Screen(text, keypressed)
    return screen.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=INSTRUCTIONS)

    parser.add_argument("inputh5", nargs="+", help="HDF5 files to use for vetting")
    parser.add_argument(
        "--outputh5",
        default="vet.h5",
        help="Output HDF5 file to append to (default: vet.h5)",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))
