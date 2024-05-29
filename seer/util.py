from copy import deepcopy


def mask_base64_messages(message):
    """Mask base64 data in the Claude API messages"""
    masked_message = deepcopy(message)
    for message in masked_message:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "image":
                    content["source"]["data"] = "<base64>"
    return masked_message