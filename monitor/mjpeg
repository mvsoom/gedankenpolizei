#!/bin/bash
# Use this script to insert a monitoring window in a pipeline
tee >(ffmpeg -loglevel panic -f mjpeg -i - -pix_fmt yuv420p -f sdl "$0")