"""Make labeled, embedded and vetted posts from normalized submissions"""

import os
import re
from functools import partial
from sys import exit

import numpy as np
import pandas as pd
from google.api_core.exceptions import ResourceExhausted
from tqdm import tqdm
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from src.config import ConfigArgumentParser
from src.slow.embed import allnan_vector, embed
from src.slow.reddit import patterns
from src.slow.reddit.vet import ask_gemini, formatpost, parse_prediction

COLUMNS = ["created_utc", "subreddit", "author", "post", "labels", "score", "embedding"]


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


def label_row(post):
    labels = [
        category
        for category, pattern in COMPILED_LABEL_PATTERNS.items()
        if pattern.search(post)
    ]

    if contains_entities(post):
        labels += ["ENTITIES"]

    return labels


def write(df, args):
    df.reset_index(inplace=True)
    df.drop_duplicates(subset="id", inplace=True, keep="last")
    df.set_index("id", inplace=True, verify_integrity=True)

    # If file exists and we're not updating, abort
    if (not args.update) and os.path.exists(args.outputfile):
        raise ValueError(f"Output file {args.outputfile} already exists")

    df.to_feather(args.outputfile, compression="zstd")


def invalidate(df, columns):
    for column in columns:
        assert column in COLUMNS, f"Invalid column {column}"
        df[column] = np.nan
        df[column] = df[column].astype(object)
    return df


def maybe_update(df, outputfile):
    try:
        old = pd.read_feather(outputfile)
    except FileNotFoundError:
        return df

    new = df.index.difference(old.index)
    df = pd.concat([old, df.loc[new]])

    return df


def apply(df, f, result, args, maxops=-1, show_progress=False):
    if result not in df.columns:
        df = invalidate(df, [result])  # Mark all as to-do

    todo = df[result].isna()
    valid = df[args].notna().all(axis=1)
    todo = todo & valid

    if maxops > 0:
        todo = todo & (np.cumsum(todo) <= maxops)

    def enhanced_apply(df, f):
        try:
            if show_progress:
                return df.progress_apply(f, axis=1)
            else:
                return df.apply(f, axis=1)
        except KeyboardInterrupt:
            verbose(f"Operation on column `{result}` aborted")
            return df

    df.loc[todo, result] = enhanced_apply(
        df.loc[todo, args], lambda row: f(**row.to_dict())
    )

    return df


def score_row(post, labels):
    if len(labels) == 0:  # Only autovet unlabeled posts
        try:
            prediction = ask_gemini(post)
            score = parse_prediction(prediction)
        except Exception as e:
            verbose(f"Error processing `{formatpost(post)}`: {e}")
            score = 0
    else:
        score = -1
    return score


def embed_row(post, score):
    if score > 0:
        try:
            embedding = embed(post)
        except ResourceExhausted:
            verbose("Embedding failed due to resource exhaustion")
            embedding = np.nan  # Mark as "to retry later"
    else:
        embedding = allnan_vector()
    return embedding


def main(args):
    df = read_dfs(args.inputfile)

    if args.update:
        df = maybe_update(df, args.outputfile)

    if args.invalidate:
        df = invalidate(df, args.invalidate)

    global apply
    apply = partial(
        apply,
        maxops=args.maxops,
        show_progress=args.verbose,
    )

    verbose("Labeling posts")
    df = apply(df, label_row, "labels", ["post"])

    verbose("Scoring posts")
    df = apply(df, score_row, "score", ["post", "labels"])

    verbose("Embedding posts")
    df = apply(df, embed_row, "embedding", ["post", "score"])

    df = df[COLUMNS]

    verbose(f"Writing {len(df)} rows to {args.outputfile}")
    write(df, args)

    future_todos = df.isna().sum().sum()  # Pandas sucks
    return 0 if future_todos > 0 else 1


verbose = print


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

    parser.add_argument(
        "inputfile",
        nargs="+",
        help="Input .feather files containing normalized submissions",
    )
    parser.add_argument("outputfile", help="Output .feather file to write results to")
    parser.add_argument(
        "--invalidate",
        nargs="+",
        help="Invalidate one or more columns, which will be recalculated",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update output file rather than overwriting",
    )
    parser.add_argument(
        "--maxops",
        type=int,
        default=-1,
        help="Limit maximum number of operations per task (default: no limit)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    args = parser.parse_args()

    if not args.verbose:
        verbose = lambda *_, **__: None
    else:
        tqdm.pandas()

    exit(main(args))
