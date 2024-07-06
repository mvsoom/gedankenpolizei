import asyncio
import base64

import cv2
import numpy as np
import websockets
from PIL import Image

from seer.log import debug, error


async def process_image(websocket, path):
    async for message in websocket:
        # Decode the received image
        img_data = base64.b64decode(message)
        nparr = np.frombuffer(img_data, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert CV image into a Pillow Image
        pillow_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

        # Process the image and generate text
        text = str(nparr.sum())

        error("GOT", extra={"image": pillow_img})

        # Send the generated text back to the client
        await websocket.send(text)


def generate_text_from_image(img):
    # Dummy text generation logic
    return "Generated description of the image."


start_server = websockets.serve(process_image, "localhost", 8765)

debug("Started the server at ws://localhost:8765.")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
