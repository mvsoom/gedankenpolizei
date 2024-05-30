from seer import env

# Import all NARRATE_* dotenv variables into this namespace
globals().update(
    {k.removeprefix("NARRATE_"): v for k, v in env.glob("NARRATE_*").items()}
)

# Then, declare some more hard constants
IMAGE_MAX_SIZE = (1024, 1024)  #  Claude API will downsize if larger than this
MAX_TOKENS = 300  # Max tokens to generate before stopping
RESPONSE_TIMEOUT = 10  # seconds