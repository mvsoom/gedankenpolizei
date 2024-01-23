import argparse
import pandas as pd
import textwrap
from textacy import preprocessing
from textacy.preprocessing import normalize, replace, remove
from functools import partial
from markdown import markdown as markdown_to_html
import re
import string


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

def firststage(df):
    df = df[df["selftext"] != "[removed]"]
    df = df[df[["selftext", "title"]].notnull().all(1)]
    df.fillna(0, inplace=True)
    return df


def secondstage(df):
    df["selftext"] = df["text"].progress_apply(impurity, min_len=10)

    # remove collapsed
    return


def main(args):
    verbose = print if args.verbose else void

    verbose(f"Reading {args.inputcsv}")
    df = pd.read_csv(args.inputcsv)

    verbose("Removing empty posts and normalizing up/down counts")
    df = firststage(df)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("inputcsv", help="Clean this CSV")
    parser.add_argument(
        "outputcsv",
        nargs="?",
        default=None,
        help="Append cleaned submissions to this CSV file, or create it if it does not exist (default: {inputcsv}.cleaned)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()
    if args.outputcsv is None:
        args.outputcsv = args.inputcsv + ".cleaned"

    exit(main(args))
