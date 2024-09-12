#!/bin/bash
# Scrape new Reddit posts, process them, and update the posts file

DATA_DIR="data/reddit"
SUBREDDIT_DIR="$DATA_DIR/subreddit"
SUBREDDIT_LIST="$DATA_DIR/subreddit.list"

POSTS_FILE="$DATA_DIR/posts.feather"
POSTS_BATCH=2000

SCRAPE_NUM_THREADS=6
SCRAPE_STRIDE=31449600 # 1 year
SCRAPE_MAXFSIZE=5 # GB

echo "Updating new scrapes..."
cat "$SUBREDDIT_LIST" | grep -v '^#' | xargs -I {} -P $SCRAPE_NUM_THREADS -n 1 \
    python -m src.slow.reddit.scrape {} "$SUBREDDIT_DIR"/{}.csv --update --stride $SCRAPE_STRIDE --maxfsize $SCRAPE_MAXFSIZE --verbose

echo "Normalizing new scrapes..."
for csv_file in "$SUBREDDIT_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        # Run the command for each CSV file
        python -m src.slow.reddit.normalize "$csv_file" --update --verbose
    fi
done

echo "Turning new scrapes into posts in batches of $POSTS_BATCH..."
# Run the command as long as it returns a zero exit code, which means new updates have arrived
# Nonzero exitcode means error or no new updates
while python -m src.slow.reddit.makeposts "$SUBREDDIT_DIR"/*.feather --update --outputfile "$POSTS_FILE" --verbose --downsample $POSTS_BATCH
do
    :
done

echo "Done at $(date)"