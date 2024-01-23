"""Scrape submissions (posts without the comments) from a subreddit"""
import argparse
import time
import requests
from datetime import datetime
from retrying import retry
from urllib.parse import urlencode
import csv
import os
from collections import OrderedDict
from sys import exit


API = "https://api.pullpush.io/reddit/search/submission/"
MAXSUBS = 100
COLUMNS = (
    "created_utc",
    "id",
    "subreddit",
    "author",
    "title",
    "selftext",
    "ups",
    "downs",
)


@retry(wait_exponential_multiplier=1000, stop_max_delay=3600000)
def make_request(url):
    response = requests.get(url, timeout=10)

    # If not succesful, raise and @retry
    response.raise_for_status()

    response_dict = response.json()
    return response_dict


def make_url(subreddit, after, before):
    params = {
        "subreddit": str(subreddit),
        "size": int(MAXSUBS),
        "after": int(after),
        "before": int(before),
    }

    return f"{API}?{urlencode(params)}"


def interestingpart(s):
    return OrderedDict((c, s.get(c, None)) for c in COLUMNS)


def deleted(s):
    return s["selftext"] == "[deleted]" or s["selftext"] == "[removed]"


def write(filename, s):
    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        if not file_exists:
            writer.writerow(s.keys())

        # Append the data to the CSV file
        row = [v if v is not None else "" for v in s.values()]
        writer.writerow(row)


def void(*_, **__):
    pass


def filesize_in_gb(filename):
    if os.path.exists(filename):
        file_size_bytes = os.path.getsize(filename)
        return file_size_bytes / (1024**3)
    else:
        return 0.0


utc = datetime.utcfromtimestamp


def main(args):
    verbose = print if args.verbose else void
    verbose(f"Writing to {args.outputcsv}")

    b = args.before
    stride = args.stride
    done = False

    while not done:
        # Scrape submissions timestamped within [a,b]
        a = b - stride
        if a <= args.after:
            a = args.after
            done = True

        verbose(f"Scraping r/{args.subreddit} between UTC {utc(a)} -- {utc(b)}")

        url = make_url(args.subreddit, a, b)
        response = make_request(url)

        # Write out scraped submissions
        subs = response["data"]
        for raws in subs:
            s = interestingpart(raws)
            if not deleted(s):
                write(args.outputcsv, s)
                verbose((" " * 3 + s["title"])[:50])

        # Check approximate file size constraint
        if filesize_in_gb(args.outputcsv) > args.maxfsize:
            verbose(
                f"Stopping, as filesize of {args.outputcsv} exceeds {args.maxfsize} GB"
            )
            done = True

        # Setup for next iteration
        n = len(subs)
        if n < MAXSUBS:
            b = a
            if n == 0:
                verbose("No submissions found: doubling stride")
                stride *= 2
        else:
            verbose("Reached MAXSUBS: continuing from last submission")
            b = min([int(s["created_utc"]) for s in subs]) - 1
        continue

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "subreddit", help="Which subreddit to scrape (without the r/ prefix)"
    )
    parser.add_argument(
        "outputcsv",
        nargs="?",
        default=None,
        help="Append new submissions to this CSV file, or create it if it does not exist (default: {subreddit}.csv)",
    )

    now = int(time.time())

    parser.add_argument(
        "--before",
        type=int,
        default=now,
        help="Scrape submissions before this UTC epoch date (default: now)",
    )
    parser.add_argument(
        "--after",
        type=int,
        default=1137452400,  # First post on Reddit
        help="Scrape submissions after this UTC epoch date",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=86400,
        help="Scrape submissions in batches of STRIDE seconds (default: 86400 seconds, i.e., 1 day)",
    )
    parser.add_argument(
        "--maxfsize",
        type=float,
        default=float("inf"),
        help="Stop if the outputcsv filesize approximately exceeds MAXFSIZE in GB",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

    # Parse the command line arguments
    args = parser.parse_args()
    if args.outputcsv is None:
        args.outputcsv = args.subreddit + ".csv"

    exit(main(args))
