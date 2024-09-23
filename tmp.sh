#!/bin/bash
# Scrape new Reddit posts, process them, and update the posts and autovet files

DATA_DIR="data/reddit"
SUBREDDIT_DIR="$DATA_DIR/subreddit"
SUBREDDIT_LIST="$DATA_DIR/subreddit.list"

POSTS_FILE="$DATA_DIR/posts.feather"
POSTS_BATCH=5000

echo "Turning new scrapes into posts in batches of $POSTS_BATCH..."
# Run the command as long as it returns a zero exit code, which means new updates have arrived
# Nonzero exitcode means error or no new updates
while python -m src.slow.reddit.make "$SUBREDDIT_DIR"/*.feather "$POSTS_FILE" --update --verbose --maxops $POSTS_BATCH
do
    :
done

echo "Done at $(date)"