from time import time

from src.gemini import gemini

generation_config = {
    "temperature": 2.0,
}

MODEL = gemini("flash", generation_config=generation_config)

text = """Turn the following narration of a video into a stream of consciousness between <soc>...</soc> tags.\\n\\n<video_narration>\\n(27.2s ago) A pink sweater hangs in the frame.\\n(25.5s ago) A person has appeared in the frame.\\n(23.6s ago) The person is looking around the room.\\n(20.1s ago) The person is waving their hand.\\n(13.2s ago) The person is using a mobile device.\\n(4.3s ago) The person is holding a blue object, possibly a tablet or phone.\\n(1.4s ago) The person is raising their hand in front of the camera.\\n(0.0s ago) The person is moving around in the room.\\n</video_narration>"""

for _ in range(10):
    t = time()
    t0 = time()

    responses = MODEL.generate_content(
        text,
        stream=True,
    )

    i = 0

    for response in responses:
        dt = time() - t
        print(f"{dt:.3f}", response.text)
        t = time()

        i += 1
        print(i)

        if i == 3:
            responses.close()  # Not entirely sure if this is invoked automatically when breaking
            break

    chars_per_sec = len(text) / (time() - t0)
    print("DONE", f"{chars_per_sec:.2f} chars/sec")

    print(responses)

    break
