"""Vet posts manually or automatically"""

import argparse
from sys import exit

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

from autovet import ask_gemini
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


def writeout(vdf, path):
    if "score" in vdf:
        vdf["score"] = vdf["score"].astype("int")
    vdf.to_feather(path, compression="zstd")
    print(f"Written to {path}")


def main(args):
    pdf = pd.read_feather(args.postfile)
    vdf = pd.read_feather(args.vetfile)

    if args.reference:
        rdf = pd.read_feather(args.reference)
        reference_embeddings = np.stack(rdf["embedding"], dtype="float32")

    if args.bias:
        from makeposts import EMBEDDING_MODEL

        model = SentenceTransformer(EMBEDDING_MODEL)
        bias_embedding = model.encode(BIAS, convert_to_tensor=True)

    args.n = len(pdf) if args.n is None else args.n
    probs = weigh_subreddits(pdf, vdf)
    embeddings = np.stack(pdf["embedding"], dtype="float32")

    def sample_post(previous_post=None, numcandidates=200, maxtries=20, tried=0):
        if previous_post is not None:
            # Sample semantically similar posts, regardless of subreddit
            query = previous_post.embedding
            results = util.semantic_search(query, embeddings, top_k=numcandidates)[0]

            candidates = pdf.iloc[[result["corpus_id"] for result in results]]
        else:
            if args.autovet:
                # Uniform sampling
                candidates = pdf
            else:
                # Stratified sampling based on subreddit
                subreddit = probs.sample(weights=probs).index[0]

                # Choose candidate posts from that subreddit
                candidates = pdf[pdf["subreddit"] == subreddit].sample(
                    numcandidates, replace=True
                )

        # Choose a post that has not been labeled or vetted yet
        candidates = candidates[candidates["labels"].apply(len) == 0]
        candidates = candidates[~candidates.index.isin(vdf.index)]

        # If no valid candidate, retry
        if len(candidates) > 0:
            if not args.bias:
                return candidates.iloc[0]
            else:
                candidate_embeddings = np.stack(
                    candidates["embedding"], dtype="float32"
                )
                scores = util.cos_sim(bias_embedding, candidate_embeddings)
                best = scores.argmax().item()
                return candidates.iloc[best]
        else:
            if tried >= maxtries:
                raise ValueError(f"Can't find fresh sample after {maxtries} tries")
            return sample_post(None, numcandidates, maxtries, tried=tried + 1)

    def predict(
        sample,
        explain=False,
        num_good_examples=1,
        num_bad_examples=1,
        numcandidates=200,
    ):
        if args.reference:
            nonlocal rdf, reference_embeddings

            # Find semantically similar examples in the reference set
            query = sample.embedding
            results = util.semantic_search(
                query, reference_embeddings, top_k=numcandidates
            )[0]

            examples = []

            for result in results:
                candidate = rdf.iloc[result["corpus_id"]]

                if num_good_examples > 0 and candidate["score"] == 1:
                    examples.append(("GOOD", candidate))
                    num_good_examples -= 1

                if num_bad_examples > 0 and candidate["score"] == -1:
                    examples.append(("BAD", candidate))
                    num_bad_examples -= 1

                if num_good_examples == 0 and num_bad_examples == 0:
                    break
        else:
            examples = None

        return ask_gemini(sample["post"], explain=explain, examples=examples)

    try:
        if args.autovet:
            autovet(args, vdf, sample_post, predict)
        else:
            vet(args, vdf, sample_post, predict)
    finally:
        writeout(vdf, args.vetfile)

    return 0


def autovet(args, vdf, sample_post, predict):
    for numdone in tqdm(range(args.n)):
        sample = sample_post()

        try:
            reply = ask_gemini(sample["post"], explain=False)

            if reply == "GOOD":
                score = 1
            elif reply == "BAD":
                score = -1
            else:
                raise ValueError(f"Unexpected reply: {reply}")
        except Exception as e:
            fp = formatpost(sample["post"])
            print(f"Error processing ```{fp}```: {e}")
            score = 0

        vdf.loc[sample.name, "score"] = int(score)


"""
TODO

- multiple threads: vdf must be kept up to date between threads
- validate with few shot or zero shot

- incorporate autovet.py file
"""


def vet(args, vdf, sample_post, predict):
    numdone = 0

    def display(sample):
        subreddit = sample["subreddit"]
        post = formatpost(sample["post"])
        text = f"r/{subreddit}\n{post}"

        if args.predict:
            reply = predict(sample, explain=True)
            text += " [" + reply + "]"

        return text

    def keypressed(screen, c):
        if c in [PLUS, ENTER, MINUS]:
            # Add the sample to the vetting df
            nonlocal sample, numdone
            vdf.loc[sample.name, "score"] = int(SCORE[c])
            numdone += 1

            # Set stage for the next sample to be vetted
            sample = sample_post(sample if c == PLUS else None)
            screen.text = display(sample)
            screen.display()
        elif c == EXIT:
            return (continue_loop := False)

        if numdone >= args.n:
            return (continue_loop := False)

        return (continue_loop := True)

    sample = sample_post()
    text = display(sample)
    screen = tui.Screen(text, keypressed)
    screen.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=INSTRUCTIONS)

    parser.add_argument("postfile", help="Post .feather file containing posts to vet")
    parser.add_argument("vetfile", help="Output vet .feather file to append to")
    parser.add_argument(
        "-n", type=int, default=None, help="Stop vetting after {n} posts"
    )
    parser.add_argument(
        "--bias",
        default=None,
        nargs="?",
        const=BIAS,
        help="Bias post selection? If given without argument, defaults to: '%(const)s'",
    )
    parser.add_argument(
        "--predict",
        action="store_true",
        help="Display autovet prediction with explanation during manual vetting",
    )
    parser.add_argument(
        "--autovet",
        action="store_true",
        help="Activate autovet mode",
    )
    parser.add_argument(
        "--reference",
        default=None,
        help="Reference .feather file containing ground-truth posts and labels for use with --predict or --autovet",
    )

    # Parse the command line arguments
    args = parser.parse_args()

    if args.autovet:
        assert not args.predict, "Cannot --predict and --autovet at the same time"
    if args.reference:
        assert (
            args.predict or args.autovet
        ), "Cannot --reference without --predict or --autovet"

    exit(main(args))
