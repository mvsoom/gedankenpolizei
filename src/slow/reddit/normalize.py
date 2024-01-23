import argparse
import pandas as pd
from textacy import preprocessing
from textacy.preprocessing import normalize, replace, remove
from functools import partial
from markdown import markdown as markdown_to_html
import re
import string


def remove_enclosing_symbols_and_whitespace(
    text, pattern=re.compile(r"^[\s\W]+|[\s\W]+$")
):
    return pattern.sub("", text)


def remove_unicode_sequences(text, pattern=re.compile(r"&#[xX][0-9a-fA-F]+;")):
    """Matches hexadecimal Unicode escape sequences like &#x200B;"""
    return pattern.sub("", text)


def normalize_repeated_whitespace(text, pattern=re.compile(r"\s+")):
    return pattern.sub(" ", text)


def normalize_ellipses(text, pattern=re.compile(r"\.[\s\.]+\.")):
    return pattern.sub("...", text)


def remove_markdown_urls(text, pattern=re.compile(r"\[([^\[\]]*)\]\([^\(\)]*\)")):
    return pattern.sub("...", text)


def remove_unicode_whitespace_chars(
    text, pattern=re.compile(r"[\u200b-\u200d\u2028\u2029\u3000]+")
):
    return pattern.sub("", text)


def replace_domains(
    text,
    pattern=re.compile(
        r"[\S]+\.(net|com|org|info|edu|gov|uk|de|ca|jp|fr|au|us|ru|ch|it|nel|se|no|es|mil)[\S]*\s?"
    ),
):
    """https://stackoverflow.com/a/54887468/6783015"""
    return pattern.sub("...", text)


def replace_redditlike(
    text,
    pattern=re.compile(r"\b\w*reddit\w*\b|\br/\w+|\bu/\w+", re.IGNORECASE),
):
    """Define a case-insensitive regular expression pattern to match and replace Reddit-related identifiers"""
    return pattern.sub("...", text)


def maybecollapse(
    text,
    pattern=re.compile(r"^[\s" + "\u200d" + re.escape(string.punctuation) + r"]+$"),
):
    return "" if pattern.match(text) else text


normalize = preprocessing.make_pipeline(
    # Remove markdown by converting to HTML and then stripping the tags
    remove_markdown_urls,
    markdown_to_html,
    remove.html_tags,
    # Handle Reddit bug; see https://www.reddit.com/r/Infinity_For_Reddit/comments/kz7keb/bug_x200b_is_being_rendered_as_plain_text_instead
    remove_unicode_sequences,
    # Handle generic stuff
    normalize.bullet_points,
    normalize.hyphenated_words,
    normalize.quotation_marks,
    partial(normalize.unicode, form="NFKC"),
    normalize.whitespace,
    remove_unicode_whitespace_chars,
    # Mask (sensitive) information
    partial(replace.emails, repl="..."),
    partial(replace.emojis, repl="..."),
    partial(replace.phone_numbers, repl="..."),
    partial(replace.urls, repl="..."),
    partial(replace.user_handles, repl="..."),
    partial(normalize.repeating_chars, chars=".", maxn=3),
    replace_domains,
    replace_redditlike,
    normalize_ellipses,
    # Normalize whitespace
    normalize_repeated_whitespace,
    # Collapse if at this point text is reduced to dots and spaces
    maybecollapse,
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


def firststage(df):
    """Cleanup deleted submission titles and/or selftexts. Do not accept empty selftexts (empty titles are OK)"""
    from scrape import deleted

    def collapse_if_deleted(text):
        return "" if deleted(text) else text

    df["title"] = df["title"].apply(collapse_if_deleted)
    df["selftext"] = df["selftext"].apply(collapse_if_deleted)

    nonempty = df["selftext"].str.len() > 0
    df = df[nonempty]

    return df


def secondstage(df, show_progress):
    def embed_title_in_selftext(row):
        title = remove_enclosing_symbols_and_whitespace(row["title"])
        selftext = row["selftext"]
        return f"[{title}] {selftext}" if title else selftext

    raw = df.apply(embed_title_in_selftext, axis=1)

    if show_progress:
        try:
            from tqdm import tqdm

            tqdm.pandas()
            df["normalized"] = raw.progress_apply(normalize)
        except ImportError:
            df["normalized"] = raw.apply(normalize)
    else:
        df["normalized"] = raw.apply(normalize)

    return df


def write(df, outputcsv):
    df.to_csv(outputcsv, index=False, mode="w")


def void(*_, **__):
    pass


def main(args):
    verbose = print if args.verbose else void

    verbose(f"Reading {args.inputcsv}")
    df = read(args.inputcsv)

    verbose("Removing empty posts")
    df = firststage(df)

    verbose("Normalizing")
    df = secondstage(df, show_progress=args.verbose)

    verbose(f"Writing result to {args.outputcsv}")
    write(df, args.outputcsv)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("inputcsv", help="Normalize this CSV")
    parser.add_argument(
        "outputcsv",
        nargs="?",
        default=None,
        help="Write out result to this CSV file and replace it if it already exists (default: {inputcsv}.normalized)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()
    if args.outputcsv is None:
        args.outputcsv = args.inputcsv + ".normalized"

    exit(main(args))
