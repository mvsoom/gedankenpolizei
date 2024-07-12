import argparse
from sys import exit

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util

from lib import tui
from makeposts import formatpost

INSTRUCTIONS = "Vetting: press '+' to score +1, '-' for -1, ENTER for 0, 'q' to quit"
PLUS, MINUS, ENTER = ord("+"), ord("-"), ord("\n")
EXIT = ord("q")

SCORE = {
    PLUS: 1,
    ENTER: 0,
    MINUS: -1,
}

# BIAS = "I am feeling good, happy, fine, neutral."
BIAS = "I see people."


def weigh_subreddits(pdf, vdf):
    vetted = pdf.loc[pdf.index.isin(vdf.index)]

    counts = pdf["subreddit"].value_counts() * 0.0
    counts = counts + vetted["subreddit"].value_counts()

    counts[counts.isna()] = 1 / len(pdf)

    # Favor subreddits that have not been vetted yet
    weights = (1 / counts) / (1 / counts).sum()
    return weights


def main(args):
    pdf = pd.read_feather(args.postfile)
    try:
        vdf = pd.read_feather(args.vetfile)
    except FileNotFoundError:
        vdf = pd.DataFrame()

    probs = weigh_subreddits(pdf, vdf)
    embeddings = np.stack(pdf["embedding"], dtype="float32")

    if args.bias:
        from makeposts import EMBEDDING_MODEL

        model = SentenceTransformer(EMBEDDING_MODEL)

        bias_embedding = model.encode(BIAS, convert_to_tensor=True)

    def sample_post(previous_post=None, numcandidates=200, maxtries=20, tried=0):
        if previous_post:
            # Get semantically similar posts, regardless of subreddit
            query = pdf.loc[previous_post].embedding
            results = util.semantic_search(query, embeddings, top_k=numcandidates)[0]

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
            if args.bias:
                candidate_embeddings = np.stack(
                    candidates["embedding"], dtype="float32"
                )
                scores = util.cos_sim(bias_embedding, candidate_embeddings)
                best = scores.argmax().item()
                return candidates.iloc[best]
            else:
                return candidates.iloc[0]

        else:
            if tried >= maxtries:
                raise ValueError(
                    f"Can't find unique stratified sample after {maxtries} tries"
                )
            return sample_post(None, numcandidates, maxtries, tried=tried + 1)

    return vet(args, vdf, sample_post)


def vet(args, vdf, sample_post):
    def display(sample):
        subreddit = sample["subreddit"]
        post = formatpost(sample["post"])
        return f"r/{subreddit}\n{post}"

    def keypressed(screen, c):
        if c in [PLUS, ENTER, MINUS]:
            # Add the sample to the vetting df
            nonlocal sample
            vdf.loc[sample.name, "score"] = int(SCORE[c])

            # Set stage for the next sample to be vetted
            sample = sample_post(sample.name if c == PLUS else None)
            screen.text = display(sample)
            screen.display()
        elif c == EXIT:
            return (continue_loop := False)
        return (continue_loop := True)

    try:
        sample = sample_post()
        text = display(sample)
        screen = tui.Screen(text, keypressed)
        screen.run()
    finally:
        if "score" in vdf:
            vdf["score"] = vdf["score"].astype("int")
        vdf.to_feather(args.vetfile, compression="zstd")
        print(f"Written to {args.vetfile}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=INSTRUCTIONS)

    parser.add_argument("postfile", help="Post .feather file containing posts to vet")
    parser.add_argument("vetfile", help="Output vet .feather file to append to")
    parser.add_argument(
        "--bias",
        default=None,
        nargs="?",
        const=BIAS,
        help="Bias post selection? If given without argument, defaults to: '%(default)s'",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    exit(main(args))
