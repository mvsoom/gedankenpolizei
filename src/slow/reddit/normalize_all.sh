#!/bin/bash

# Directory containing CSV files
csv_directory="subreddit"

# Check if the directory exists
if [ ! -d "$csv_directory" ]; then
    echo "Directory '$csv_directory' does not exist."
    exit 1
fi

# Iterate over CSV files in the directory
for csv_file in "$csv_directory"/*.csv; do
    if [ -f "$csv_file" ]; then
        # Run the command for each CSV file
        python normalize.py "$csv_file" --verbose
    fi
done