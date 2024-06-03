#!/bin/bash
# This script enables using the `seer.narrate.stream` script with a video file by streaming the video file to a virtual video device using ffmpeg.
# This strategy sidesteps difficult synchronization issues when directly opening the video file with OpenCV, keeping synchronization errors to about +/- 0.05 sec rather than a steady drift.
# Example usage:
# $ ./scripts/narrate_video.sh assets/test_stream_timestamped.webm --monitor

VIDEO_FILE=$1
NARRATE_STREAM_ARGS=${@:2}

VIDEO_NR=99
VIDEO_STREAM=/dev/video$VIDEO_NR

sudo modprobe v4l2loopback video_nr=$VIDEO_NR

# Check if the video device was created
if [ ! -e "$VIDEO_STREAM" ]; then
    echo "Failed to create video device $VIDEO_STREAM"
    exit 1
fi

# Start the ffmpeg command in the background
ffmpeg -re -i "$VIDEO_FILE" -f v4l2 "$VIDEO_STREAM" -loglevel panic &
FFMPEG_PID=$!

# Start the unbuffered python command in the foreground
python -u -m seer.narrate.stream "$VIDEO_STREAM" $NARRATE_STREAM_ARGS

# When the python command exits, kill the ffmpeg command
kill $FFMPEG_PID

# Remove the video device
sudo rmmod v4l2loopback
