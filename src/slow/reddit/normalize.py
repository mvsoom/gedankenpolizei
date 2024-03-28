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


def remove_unicode_sequences(text, pattern=re.compile(r"&#[xX][0-9a-fA-F]+;")):
    """Matches hexadecimal Unicode escape sequences like &#x200B;"""
    return pattern.sub("", text)


def remove_triple_ticks(text, pattern=re.compile(r"```")):
    return pattern.sub("", text)


def remove_unicode_whitespace_chars(
    text, pattern=re.compile(r"[\u200b-\u200d\u2028\u2029\u3000]+")
):
    return pattern.sub("", text)


def normalize_repeated_whitespace(text, pattern=re.compile(r"\s+")):
    return pattern.sub(" ", text)


def normalize_repeated_ellipses(text, pattern=re.compile(r"\.[\s\.]+\.")):
    return pattern.sub("...", text)


def remove_markdown_urls(text, pattern=re.compile(r"\[(.+?)\]\(.+?\)")):
    """Remove markdown URLs like [text](url) and keep only the text (https://stackoverflow.com/a/53980235/6783015)"""
    return pattern.sub(r"\1", text)


def replace_urls(
    text,
    pattern=re.compile(
        r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
    ),
):
    """https://stackoverflow.com/a/48689681/6783015"""
    return pattern.sub("...", text)


def replace_redacted(text, pattern=patterns.REDACTED):
    """Remove stuff like [redacted], [removed by mod], [deleted], etc. from the text"""
    return pattern.sub("...", text)


def replace_redditlike(
    text,
    pattern=re.compile(r"\b\w*reddit\w*\b|\br/\w+|\bu/\w+", re.IGNORECASE),
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
    normalize.whitespace,
    remove_unicode_whitespace_chars,
    # Normalize repeated characters
    normalize_repeated_ellipses,
    normalize_repeated_whitespace,
    # Collapse posts to "" if they only contain nonsignificant information
    trycollapse,
)


COLLAPSE = preprocessing.make_pipeline(
    replace_urls,
    replace_redacted,
    replace_redditlike,
)


# TODO: use with vetting
MASKSENSITIVE = preprocessing.make_pipeline(
    partial(replace.emails, repl="..."),
    partial(replace.emojis, repl="..."),
    partial(replace.phone_numbers, repl="..."),
    partial(replace.urls, repl="..."),
    partial(replace.user_handles, repl="..."),
    normalize_repeated_ellipses,
    partial(normalize.repeating_chars, chars=".", maxn=3),
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


def embed_title_in_selftext(title, selftext):
    return "[" + title + "] " + selftext


def main(args):
    verbose = print if args.verbose else void

    verbose(f"Reading {args.inputcsv}")
    df = read(args.inputcsv)

    verbose("Normalizing authors")
    author = normalize_column(df, "author", args.verbose)

    verbose("Normalizing titles")
    title = normalize_column(df, "title", args.verbose)

    verbose("Normalizing selftexts")
    selftext = normalize_column(df, "selftext", args.verbose)

    verbose("Setting normalized columns")
    df["author"] = author
    df["normalized"] = embed_title_in_selftext(title, selftext)

    verbose("Removing empty posts (empty authors are allowed)")
    empty = emptystring(title) | emptystring(selftext)
    df = df[~empty]

    verbose("Dropping duplicates, setting index and sorting")
    df.drop_duplicates(
        subset="normalized", inplace=True, keep="last"
    )  # Remove duplicate normalized texts (unlikely)
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
