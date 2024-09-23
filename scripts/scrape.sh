#!/bin/bash
# Scrape new Reddit posts, process them, and update the posts and autovet files

DATA_DIR="data/reddit"
SUBREDDIT_DIR="$DATA_DIR/subreddit"
SUBREDDIT_LIST="$DATA_DIR/subreddit.list"

POSTS_FILE="$DATA_DIR/posts.feather"
POSTS_BATCH=5000

NUM_WORKERS=6

SCRAPE_STRIDE=31449600 # 1 year
SCRAPE_MAXFSIZE=5 # GB

echo "Updating new scrapes..."
cat "$SUBREDDIT_LIST" | grep -v '^#' | xargs -I {} -P $NUM_WORKERS \
    python -m src.slow.reddit.scrape {} "$SUBREDDIT_DIR"/{}.csv --update --stride $SCRAPE_STRIDE --maxfsize $SCRAPE_MAXFSIZE --verbose

echo "Normalizing new scrapes..."
# List all CSV files and process them in parallel
find "$SUBREDDIT_DIR" -name "*.csv" | xargs -P $NUM_WORKERS -I {} python -m src.slow.reddit.normalize {} --update --verbose

echo "Turning new scrapes into posts in batches of $POSTS_BATCH..."
# Run the command as long as it returns a zero exit code, which means new updates have arrived
# Nonzero exitcode means error or no new updates
while python -m src.slow.reddit.make "$SUBREDDIT_DIR"/*.feather "$POSTS_FILE" --update --verbose --maxops $POSTS_BATCH
do
    :
done

echo "Done at $(date)"