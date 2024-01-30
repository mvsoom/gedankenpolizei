import argparse
from datetime import datetime
import pandas as pd
import numpy as np
from sys import exit
from lib import tui
import re
from tqdm import tqdm

INSTRUCTIONS = "Vetting: press '+' to score +1, '-' for -1, ENTER for 0, 'q' to quit"
PLUS, MINUS, ENTER = ord("+"), ord("-"), ord("\n")
EXIT = ord("q")

SCORE = {
    PLUS: 1,
    ENTER: 0,
    MINUS: -1,
}

# What defines a unique post
UID_COLUMNS = ["created_utc", "id", "subreddit", "author"]

# Regex word matches (must be words, case insensitive)
AUTOVET_WORDS = [
    "spencer",
    "post(s)?",
    "repost(s)?",
    "front page",
    "comment(s)?",
    "title",
    "moderator(s)?",
    "mods",
    "discord",
    "4chan",
    "school",
    "college",
    "undergrad",
    "hello everyone",
    "you guys",
    "tl;dr",
    "marriage",
    "mom(s)?",
    "dad(s)?",
    "mommy",
    "daddy",
    "my mother",
    "my father",
    "boyfriend",
    "girlfriend",
    "bff",
    "gf",
    "lm(f)?ao",
    "soundcloud",
]

# Regex pattern matches (case insensitive)
AUTOVET_PATTERNS = [
    r"\b(\d\d\s*[fFmM])\b",  # 28m/28f/28 f (but also 28m $)
    r"\b\d\dyo\b",  # 28yo
    r"\bI\'m \d\d\b",  # I'm 28 (but also I'm 28% sure)
    r"\bI\'m a \d\d\b",  # I'm a 28
    r"\bedit:\B",  # Needs special care due to colon
]


def stratified_sample(df, among):
    subclasses = df[among].unique()
    c = np.random.choice(subclasses)
    return df[df[among] == c].sample(n=1)


def unique_stratified_sample(df, among, vetdf, maxtries=100, matchcols=UID_COLUMNS):
    # https://stackoverflow.com/questions/68490691/faster-way-to-look-for-a-value-in-pandas-dataframe
    if vetdf.empty:
        return stratified_sample(df, among)

    tries = 0
    while tries < maxtries:
        with open("tmpoutput", "a") as f:
            print(tries, file=f, flush=True)
        sample = stratified_sample(df, among)

        match = (sample[matchcols].values == vetdf[matchcols].values).all(axis=1).any()

        if not match:
            return sample
        else:
            tries += 1

    raise ValueError(f"Can't find unique stratified sample after {maxtries} tries")


def _unique_stratified_sample(df, among, vetdf, maxtries=100, matchcols=UID_COLUMNS):
    if vetdf.empty:
        return stratified_sample(df, among)

    tries = 0
    while tries < maxtries:
        with open("tmpoutput", "a") as f:
            print(tries, file=f, flush=True)
        sample = stratified_sample(df, among)

        match = (sample[matchcols].values == vetdf[matchcols].values).all(axis=1).any()

        if not match:
            return sample
        else:
            tries += 1

    raise ValueError(f"Can't find unique stratified sample after {maxtries} tries")


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
    # df.sort_values(by=UID_COLUMNS, inplace=True)

    try:
        vetdf = pd.read_hdf(args.outputh5)
    except FileNotFoundError:
        vetdf = pd.DataFrame()

    # df.set_index(UID_COLUMNS, drop=False, inplace=True)
    # vetdf.set_index(UID_COLUMNS, drop=False, inplace=True)

    if args.autovet:
        return autovet(args, df, vetdf)
    else:
        return vet(args, df, vetdf)


def match_blacklist(df):
    blacklist = "|".join([rf"\b{m}\b" for m in AUTOVET_WORDS] + AUTOVET_PATTERNS)

    regex = re.compile(blacklist, flags=re.IGNORECASE)

    tqdm.pandas(desc="Matching blacklist...")
    matches = df[df["normalized"].progress_apply(lambda x: bool(regex.search(x)))]
    return matches


def autovet(args, df, vetdf):
    matches = match_blacklist(df).copy()
    matches["score"] = SCORE[MINUS]

    # Add matches to the vetting df
    vetdf = pd.concat([vetdf, matches], join="inner", ignore_index=True)

    # Group duplicates together, with score increasing
    vetdf.sort_values(by=UID_COLUMNS + ["score"], inplace=True)

    # Drop duplicates, keeping the one with highest score
    vetdf.drop_duplicates(keep="last", inplace=True)

    # Write out
    vetdf.to_hdf(args.outputh5, key="df", mode="w")

    return 0


def vet(args, df, vetdf):
    def get_sample():
        sample = unique_stratified_sample(df, "subreddit", vetdf)
        # subreddit = sample["subreddit"].values[0]
        # timestamp = sample["created_utc"].values[0]
        sample_text = sample["normalized"].values[0]
        return sample, sample_text

    def keypressed(screen, c):
        if c in [PLUS, ENTER, MINUS]:
            # Add the sample to the vetting df and write out immediately
            nonlocal sample, vetdf, args
            vetted_sample = sample.copy()
            vetted_sample["score"] = SCORE[c]
            vetdf = pd.concat([vetdf, vetted_sample])
            vetdf.to_hdf(args.outputh5, key="df", mode="w")

            # Set stage for the next sample to be vetted
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
    parser.add_argument(
        "--autovet",
        action="store_true",
        help="Do automatic vetting instead of running UI",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))
