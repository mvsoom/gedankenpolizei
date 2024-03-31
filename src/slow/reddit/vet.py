import argparse
import pandas as pd
import numpy as np
from sys import exit
from lib import tui
import warnings
import sentence_transformers
from makeposts import formatpost

INSTRUCTIONS = "Vetting: press '+' to score +1, '-' for -1, ENTER for 0, 'q' to quit"
PLUS, MINUS, ENTER = ord("+"), ord("-"), ord("\n")
EXIT = ord("q")

SCORE = {
    PLUS: 1,
    ENTER: 0,
    MINUS: -1,
}


def weigh_subreddits(pdf, vdf):
    vetted = pdf.loc[pdf.index.isin(vdf.index)]

    counts = pdf["subreddit"].value_counts() * 0
    counts = counts + vetted["subreddit"].value_counts()

    counts[counts.isna()] = 1 / len(pdf)

    # Assign minimal weight for subreddits that have not been vetted yet
    weights = (1 / counts) / (1 / counts).sum()
    return weights


def stratified_sample(df, among):
    subclasses = df[among].unique()
    c = np.random.choice(subclasses)
    return df[df[among] == c].sample(n=1)


def unique_stratified_sample(df, among, vetdf, maxtries=100):
    # https://stackoverflow.com/questions/68490691/faster-way-to-look-for-a-value-in-pandas-dataframe
    if vetdf.empty:
        return stratified_sample(df, among)

    tries = 0
    while tries < maxtries:
        with open("tmpoutput", "a") as f:
            print(tries, file=f, flush=True)
        sample = stratified_sample(df, among)

        # match = (sample[matchcols].values == vetdf[matchcols].values).all(axis=1).any()
        match = None

        if not match:
            return sample
        else:
            tries += 1

    raise ValueError(f"Can't find unique stratified sample after {maxtries} tries")


def main(args):
    pdf = pd.read_hdf(args.posth5)
    try:
        vdf = pd.read_hdf(args.veth5)
    except FileNotFoundError:
        vdf = pd.DataFrame()

    probs = weigh_subreddits(pdf, vdf)
    embeddings = np.stack(pdf["embedding"], dtype="float32")

    def sample_post(previous_post=None, numcandidates=100, maxtries=20, tried=0):
        if previous_post:
            # Get semantically similar posts, regardless of subreddit
            query = pdf.loc[previous_post].embedding
            results = sentence_transformers.util.semantic_search(
                query, embeddings, top_k=numcandidates
            )[0]

            candidates = pdf.iloc[[result["corpus_id"] for result in results]]
        else:
            # Choose an undersampled subreddit
            subreddit = probs.sample(weights=probs).index[0]

            # Choose candidate posts from that subreddit
            candidates = pdf[pdf["subreddit"] == subreddit].sample(numcandidates)

        # Choose a post that has not been labeled or vetted yet
        candidates = candidates[candidates["labels"].apply(len) == 0]
        candidates = candidates[~candidates.index.isin(vdf.index)]

        # If no valid candidate, retry
        if len(candidates) > 0:
            return candidates.iloc[0]
        else:
            if tried >= maxtries:
                raise ValueError(
                    f"Can't find unique stratified sample after {maxtries} tries"
                )
            return sample_post(None, numcandidates, maxtries, tried=tried + 1)

    return vet(args, vdf, sample_post)


def vet(args, vdf, sample_post):
    def keypressed(screen, c):
        if c in [PLUS, ENTER, MINUS]:
            # Add the sample to the vetting df and write out immediately
            nonlocal sample
            vdf.loc[sample.name, "score"] = SCORE[c]

            # Set stage for the next sample to be vetted
            sample = sample_post(sample.name if c == PLUS else None)
            screen.text = formatpost(sample["post"])
            screen.display()
        elif c == EXIT:
            return (continue_loop := False)
        return (continue_loop := True)

    try:
        sample = sample_post()
        text = formatpost(sample["post"])
        screen = tui.Screen(text, keypressed)
        screen.run()
    finally:
        vdf["score"] = vdf["score"].astype("int")
        vdf.to_hdf(args.veth5, key="df", mode="w")
        print(f"Written to {args.veth5}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=INSTRUCTIONS)

    parser.add_argument("posth5", help="HDF5 file containing posts to vet")
    parser.add_argument("veth5", help="Output HDF5 vet file to append to")

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))
