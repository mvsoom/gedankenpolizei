import asyncio
import base64
import functools
from threading import Lock, Thread
from time import sleep, time

import cv2
import numpy as np
import websockets

from seer.image.frame import format_time, raw_to_image, sample_frames, timestamp
from seer.image.tile import concatenate_images_grid
from seer.log import debug, error
from seer.narrate import TILE_NUM_FRAMES, TILE_SIZE
from seer.narrate.frame import narrate

# Ensure print always flushes to stdout
print = functools.partial(print, flush=True)

# Define global variables
RAWFRAMES = []
DESCRIPTIONS = []
LOCK = Lock()


async def process_image(websocket, path):
    global RAWFRAMES, DESCRIPTIONS
    try:
        while True:
            async for message in websocket:
                # Decode the received image
                img_data = base64.b64decode(message)
                nparr = np.frombuffer(img_data, np.uint8)
                cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Add the frame to RAWFRAMES
                with LOCK:
                    RAWFRAMES.append((time(), cv_img))

                # Check for any available descriptions to send back
                with LOCK:
                    if DESCRIPTIONS:
                        description = DESCRIPTIONS.pop(0)
                    else:
                        description = ""

                # Send the description back to the client
                await websocket.send(description)
    except websockets.ConnectionClosed as e:
        error(f"WebSocket connection closed: {e}")


def generate_text_from_image(img):
    # Dummy text generation logic
    return "Generated description of the image."

def process_frames():
    global RAWFRAMES, DESCRIPTIONS
    while True:
        if len(RAWFRAMES) < TILE_NUM_FRAMES:
            sleep(0.01)
            continue

        with LOCK:
            ts, rawframes = zip(*RAWFRAMES)
            RAWFRAMES.clear()

        # Sample frames
        ts, rawframes = sample_frames(ts, rawframes, TILE_NUM_FRAMES)
        frames = [raw_to_image(rawframe) for rawframe in rawframes]

        for t, frame in zip(ts, frames):
            timestamp(t, frame)

        tile = concatenate_images_grid(frames, 0, TILE_SIZE)

        start = format_time(ts[0])
        end = format_time(ts[-1])

        # Generate narration
        try:
            narration = narrate(tile, start, end)

            # Replace all newlines with spaces and trim
            narration = narration.replace("\n", " ").strip()
            if len(narration) > 0:
                with LOCK:
                    DESCRIPTIONS.append(narration)
        except Exception as e:
            error(f"Error narrating: {e}")


def main():
    # Start the WebSocket server
    start_server = websockets.serve(process_image, "localhost", 8765)
    debug("Started the server at ws://localhost:8765.")

    # Start the frame processing thread
    processing_thread = Thread(target=process_frames)
    processing_thread.daemon = True
    processing_thread.start()

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
