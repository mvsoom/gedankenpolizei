from seer import env

# Import all THOUGHTS_* dotenv variables into this namespace
globals().update(
    {k.removeprefix("THOUGHTS_"): v for k, v in env.glob("THOUGHTS_*").items()}
)