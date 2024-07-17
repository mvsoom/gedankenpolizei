from copy import deepcopy


def read_prompt_file(filename):
    with open(filename, "r") as file:
        lines = file.readlines()
    text = ""
    for line in lines:
        if not line.strip().startswith("#"):
            text += line
    return text


def replace_variables_in_prompt(prompt, variables_dict):
    """Replace {{VARIABLE_NAME}} placeholders in the prompt with actual values from the variables dictionary."""
    for var_name, var_value in variables_dict.items():
        prompt = prompt.replace("{{" + var_name + "}}", str(var_value))

    return prompt


def mask_base64_messages(message):
    """Mask base64 data in the Claude API messages"""
    masked_message = deepcopy(message)
    for message in masked_message:
        if message["role"] == "user":
            for content in message["content"]:
                if content["type"] == "image":
                    content["source"]["data"] = "<base64>"
    return masked_message