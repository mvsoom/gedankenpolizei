#!/bin/bash
# Run the pipeline to process new information (new posts, new label rules)

SUBREDDIT_DIR="subreddit"

POSTS_FILE="posts/posts.h5"
POSTS_BATCH=1000

SCRAPE_NUM_THREADS=4
SCRAPE_STRIDE=259200 # 3 days
SCRAPE_MAXFSIZE=5 # GB

echo "Relabeling existing posts..."
python relabel.py "$POSTS_FILE" --verbose

echo "Updating new scrapes..."
cat "$SUBREDDIT_DIR"/subreddits.list | xargs -I {} -P $SCRAPE_NUM_THREADS -n 1 \
    python scrape.py {} "$SUBREDDIT_DIR"/{}.csv --stride $SCRAPE_STRIDE --maxfsize $SCRAPE_MAXFSIZE --verbose --update

echo "Normalizing new scrapes..."
for csv_file in "$SUBREDDIT_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        # Run the command for each CSV file
        python normalize.py "$csv_file" --verbose
    fi
done

echo "Turning new scrapes into posts in batches of $POSTS_BATCH..."
# Run the command as long as it returns a zero exit code, which means new updates have arrived
# Nonzero exitcode means error or no new updates
while python makeposts.py "$SUBREDDIT_DIR"/*.normalized --outputh5 "$POSTS_FILE" --verbose --downsample $POSTS_BATCH --update
do
    :
done

echo "Done at $(date)"