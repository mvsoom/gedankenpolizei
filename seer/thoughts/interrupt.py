import anthropic

from seer import env


def process_stream(text):
    # Process the received text here
    print(text, end="", flush=True)


# Initialize the client
client = anthropic.Anthropic(api_key=env.ANTHROPIC_API_KEY)


with client.messages.stream(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    temperature=1,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Turn the following narration of a video into a stream of consciousness between <soc>...</soc> tags.\n\n<video_narration>\n(27.2s ago) A pink sweater hangs in the frame.\n(25.5s ago) A person has appeared in the frame.\n(23.6s ago) The person is looking around the room.\n(20.1s ago) The person is waving their hand.\n(13.2s ago) The person is using a mobile device.\n(4.3s ago) The person is holding a blue object, possibly a tablet or phone.\n(1.4s ago) The person is raising their hand in front of the camera.\n(0.0s ago) The person is moving around in the room.\n</video_narration>",
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Here is the video narration as a stream of consciousness between <soc>...</soc> tags:\n\n<soc>",
                    # "text": "Here is the video narration as a stream of consciousness between <soc>...</soc> tags:\n\n<soc>\npink sweater hanging there\nwait who's that\na person just appeared\nthey're looking around\nseem a bit lost or searching for something\noh they're waving now\ntrying to get someone's attention?\nthey've got their phone out\nlooks like they're using some app\nor maybe texting someone\nnow they're holding something blue\nis that a tablet or another phone?\nhard to tell",
                }
            ],
        },
    ],
) as stream:
    for text in stream.text_stream:
        # Check if the token contains a period
        if "." in text:
            # Close the SSE connection
            print("GOTTEN! " + text, end="", flush=True)
            # stream.close() # raises exception
            break  # can just break!!
        else:
            process_stream(text)

# stream.close()
print(stream)
# print(stream.get_final_message()) # raises exception

del stream

print(">>> Done!")