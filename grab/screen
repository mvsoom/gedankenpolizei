#!/bin/bash
# Output screengrab MJPEG stream
ffmpeg -loglevel panic -f x11grab -i $DISPLAY -vf "format=yuv420p" -vcodec mjpeg -f mjpeg -