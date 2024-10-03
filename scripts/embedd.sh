#!/bin/bash
DIMENSION=3

DATA_DIR="data/reddit"
SUBREDDIT_DIR="$DATA_DIR/subreddit"
POSTS_FILE="$DATA_DIR/posts.feather"
POSTS_DIM_FILE="$DATA_DIR/posts_dim$DIMENSION.feather"

if [ -e "$POSTS_DIM_FILE" ]
  then 
   echo "File $POSTS_DIM_FILE already exists"
   exit 1
fi

cp "$POSTS_FILE" "$POSTS_DIM_FILE"

python -m src.slow.reddit.make "$SUBREDDIT_DIR"/*.feather "$POSTS_DIM_FILE" \
    --update \
    --verbose \
    --invalidate embedding \
    --config slow.embed.model.dimension:$DIMENSION
