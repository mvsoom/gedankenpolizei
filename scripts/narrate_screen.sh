#!/bin/bash
# This script enables the `seer.narrate.stream` script to narrate the screen by streaming the screen to a virtual video device using ffmpeg. It does not take any extra args.
# Example usage:
# $ ./scripts/narrate_screen.sh --monitor
NARRATE_STREAM_ARGS="$@"

VIDEO_NR=98
VIDEO_STREAM=/dev/video$VIDEO_NR

sudo modprobe v4l2loopback video_nr=$VIDEO_NR

# Check if the video device was created
if [ ! -e "$VIDEO_STREAM" ]; then
    echo "Failed to create video device $VIDEO_STREAM"
    exit 1
fi

# Start recording the screen in the background
ffmpeg -loglevel panic -f x11grab -framerate 15 -video_size 1920x1080 -i :0.0 -pix_fmt yuv420p -f v4l2 "$VIDEO_STREAM" &
FFMPEG_PID=$!

# Start the unbuffered python command in the foreground
python -u -m seer.narrate.stream "$VIDEO_STREAM" $NARRATE_STREAM_ARGS

# When the python command exits, kill the ffmpeg command
kill $FFMPEG_PID

# Remove the video device
sudo rmmod v4l2loopback
