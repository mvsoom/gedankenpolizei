"""Make labeled and embedded posts from normalized submissions"""

import os
import re
import textwrap
from sys import exit

import pandas as pd
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from src.config import ConfigArgumentParser
from src.slow.embed import embed
from src.slow.reddit import patterns


def formatpost(post, symbol="🟦", width=60):
    # Color the first line (title) in blue
    lines = post.splitlines()
    # lines[0] = f"\033[94m{lines[0]}\033[0m"
    # Separate newlines by symbol
    formattedpost = symbol.join(lines)
    # Wrap the text to 60 characters
    formattedpost = textwrap.fill(formattedpost, width=width)
    return formattedpost


def printpost(post, *args, **kwargs):
    print(formatpost(post, *args, **kwargs))


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


def get_distilbert_ner():
    tokenizer = AutoTokenizer.from_pretrained("dslim/distilbert-NER")
    model = AutoModelForTokenClassification.from_pretrained("dslim/distilbert-NER")

    # Replace the labels in the output with the actual categories from the HF model card
    model.config.id2label = {
        0: "O",
        1: "B-MISC",
        2: "I-MISC",
        3: "B-PER",
        4: "I-PER",
        5: "B-ORG",
        6: "I-ORG",
        7: "B-LOC",
        8: "I-LOC",
    }

    return pipeline(
        "ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple"
    )


def contains_entities(
    text,
    distilbert_ner=get_distilbert_ner(),
    score_treshold=0.8,  # Works well empirically
):
    output = distilbert_ner(text)
    return any(
        entity["entity_group"] != "O" and entity["score"] > score_treshold
        for entity in output
    )


def label(text):
    labels = [
        category
        for category, pattern in COMPILED_LABEL_PATTERNS.items()
        if pattern.search(text)
    ]

    if contains_entities(text):
        labels += ["ENTITIES"]

    return labels


def apply(df, f, show_progress=False):
    if show_progress:
        try:
            from tqdm import tqdm

            tqdm.pandas()
            result = df.progress_apply(f)
        except ImportError:
            result = df.apply(f)
    else:
        result = df.apply(f)
    return result


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
    df["labels"] = apply(df["post"], label, show_progress=args.verbose)

    verbose("Embedding posts")
    df["embedding"] = apply(df["post"], embed, show_progress=args.verbose)

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


verbose = print

if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

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
