#!/bin/bash
# Output dummy webcam MJPEG stream
ffmpeg -loglevel panic -f lavfi -i testsrc=size=640x480:rate=30 -vcodec mjpeg -f mjpeg -
