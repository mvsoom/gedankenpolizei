from seer import env
from seer.util import read_prompt_file

IMAGE_MAX_SIZE = (1024, 1024)  #  Claude API will downsize if larger than this

MAX_TOKENS = 300  # Max tokens to generate before stopping

# MODEL_NAME = "claude-3-opus-20240229"
# MODEL_NAME = "claude-3-sonnet-20240229"
MODEL_NAME = env.NARRATE_MODEL_NAME
MODEL_TEMPERATURE = env.NARRATE_MODEL_TEMPERATURE
SYSTEM_PROMPT = read_prompt_file(env.NARRATE_SYSTEM_PROMPTFILE)