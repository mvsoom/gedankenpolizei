"""Normalize a scraped CSV file and size to a more robust HDF5 file"""

import argparse
import pandas as pd
from textacy import preprocessing
from textacy.preprocessing import normalize, replace, remove
from functools import partial
from markdown import markdown as markdown_to_html
import re
import html
import patterns
import spacy


def remove_unicode_sequences(text, pattern=re.compile(r"&#[xX][0-9a-fA-F]+;")):
    """Matches hexadecimal Unicode escape sequences like &#x200B;"""
    return pattern.sub("", text)


def remove_triple_ticks(text, pattern=re.compile(r"```")):
    return pattern.sub("", text)


def remove_unicode_whitespace_chars(
    text, pattern=re.compile(r"[\u200b-\u200d\u2028\u2029\u3000]+")
):
    return pattern.sub("", text)


def remove_markdown_urls(text, pattern=re.compile(r"\[(.+?)\]\(.+?\)")):
    """Remove markdown URLs like [text](url) and keep only the text (https://stackoverflow.com/a/53980235/6783015)"""
    return pattern.sub(r"\1", text)


def replace_urls(text, pattern=re.compile(patterns.URL)):
    return pattern.sub("...", text)


def replace_redacted(text, pattern=re.compile(patterns.REDACTED, re.IGNORECASE)):
    """Remove stuff like [redacted], [removed by mod], [deleted], etc. from the text"""
    return pattern.sub("...", text)


def replace_redditlike(
    text,
    pattern=re.compile(patterns.REDDITLIKE, re.IGNORECASE),
):
    """Replace Reddit-related identifiers: r/subreddit, u/username, reddit, etc."""
    return pattern.sub("...", text)


def trycollapse(
    text,
    pattern=re.compile(r"\w"),  # = at least one alphanumeric
):
    """Try to collapse the text into "" if it only contains links or [deleted] or special symbols"""
    result = COLLAPSE(text)
    return "" if not pattern.search(result) else text


def sentence_tokenizer(text, nlp=spacy.load("en_core_web_sm")):
    """Split text into newline-separated sentence tokens

    Note: en_core_web_sm is well suited for sentence tokenization, little to no gains from larger models
    """
    doc = nlp(text)
    return "\n".join([sentence.strip() for sentence in map(str, doc.sents)])


NORMALIZE = preprocessing.make_pipeline(
    # Normalize markdown
    remove_markdown_urls,
    markdown_to_html,
    remove.html_tags,
    html.unescape,
    remove_triple_ticks,
    # Normalize text
    normalize.bullet_points,
    normalize.hyphenated_words,
    normalize.quotation_marks,
    # Normalize unicode
    partial(normalize.unicode, form="NFKC"),
    remove_unicode_sequences,  # Handle Reddit bug; see https://www.reddit.com/r/Infinity_For_Reddit/comments/kz7keb/bug_x200b_is_being_rendered_as_plain_text_instead
    partial(replace.emojis, repl=""),
    # Normalize whitespace
    normalize.whitespace,  # Collapses repeated whitespace
    remove_unicode_whitespace_chars,
    # Collapse posts to "" if they only contain nonsignificant information
    trycollapse,
    # Separate into newline-separated sentence tokens
    sentence_tokenizer,
)


COLLAPSE = preprocessing.make_pipeline(
    replace_urls,
    replace_redacted,
    replace_redditlike,
)


def read(inputcsv):
    """Read CSV file without treating empty strings as NaN and with custom converters"""

    def convert_to_int_or_zero(value):
        return int(value) if value != "" else 0

    column_converters = {
        "ups": convert_to_int_or_zero,
        "downs": convert_to_int_or_zero,
    }

    df = pd.read_csv(
        inputcsv,
        keep_default_na=False,
        na_filter=False,
        converters=column_converters,
    )

    return df


def write(df, outputh5):
    df.to_hdf(outputh5, key="df", mode="w")


def void(*_, **__):
    pass


def normalize_column(df, column_name, show_progress):
    column = df[column_name]
    if show_progress:
        try:
            from tqdm import tqdm

            tqdm.pandas()
            result = column.progress_apply(NORMALIZE)
        except ImportError:
            result = column.apply(NORMALIZE)
    else:
        result = column.apply(NORMALIZE)
    return result


def emptystring(column):
    return column.str.len() == 0


def make_post(normalized_title, normalized_selftext):
    """A post contains newline separated sentence tokens, so each line is a sentence token

    The first line (aka sentence token) is always the normalized title (which may contain multiple natural language sentences (rare), but no newlines).
    The next lines are the sentence tokens of the normalized selftext.
    """
    post = normalized_title.str.replace("\n", " ") + "\n" + normalized_selftext
    return post


def main(args):
    verbose = print if args.verbose else void

    verbose(f"Reading {args.inputcsv}")
    df = read(args.inputcsv)

    verbose("Normalizing authors")
    df["author"] = normalize_column(df, "author", args.verbose)

    verbose("Normalizing titles")
    df["title"] = normalize_column(df, "title", args.verbose)

    verbose("Normalizing selftexts")
    df["selftext"] = normalize_column(df, "selftext", args.verbose)

    verbose("Removing empty posts (empty authors are allowed)")
    empty = emptystring(df["title"]) | emptystring(df["selftext"])
    df = df[~empty]

    verbose("Joining titles and selftexts into posts")
    df["post"] = make_post(df["title"], df["selftext"])

    verbose("Dropping duplicates, setting index and sorting")
    df.drop_duplicates(
        subset="post", inplace=True, keep="last"
    )  # Remove duplicate posts (unlikely)
    df.drop_duplicates(subset="id", inplace=True, keep="last")
    df.set_index("id", inplace=True, verify_integrity=True)
    df.sort_values(by="created_utc", inplace=True)

    verbose(f"Writing resulting {len(df)} rows to {args.outputh5}")
    write(df, args.outputh5)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("inputcsv", help="Normalize this CSV")
    parser.add_argument(
        "outputh5",
        nargs="?",
        default=None,
        help="Write out result to this HDF5 file and replace it if it already exists (default: base on {inputcsv})",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()
    if args.outputh5 is None:
        args.outputh5 = (
            args.inputcsv[:-4]
            if args.inputcsv.lower().endswith(".csv")
            else args.inputcsv
        ) + ".normalized"

    exit(main(args))
