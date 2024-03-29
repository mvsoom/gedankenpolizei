#!/bin/bash

NUM_THREADS=4
STRIDE=259200 # 3 days
MAXFSIZE=2 # GB

cat subreddit/subreddits.list | xargs -I {} -P $NUM_THREADS -n 1 \
    python scrape.py {} subreddit/{}.csv --stride $STRIDE --maxfsize $MAXFSIZE --verbose
