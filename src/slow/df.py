import os

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

from src.config import CONFIG
from src.log import verbose

load_dotenv()

HF_REPO_ID = CONFIG("slow.reddit.hf_repo_id")
HF_SLOW_THOUGHTS_FILE = CONFIG("slow.reddit.hf_slow_thoughts_file")


def _load_slow_thoughts():
    HF_TOKEN_READ = os.getenv("HF_TOKEN_READ")
    if not HF_TOKEN_READ:
        raise ValueError("`HF_TOKEN_READ` token is not set in the .env file")

    # Retrieve the file from HF or cache
    downloaded_file_path = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=HF_SLOW_THOUGHTS_FILE,
        repo_type="dataset",
        use_auth_token=HF_TOKEN_READ,
    )

    slowdf = pd.read_feather(downloaded_file_path)
    verbose(f"Loaded {len(slowdf)} slow thoughts from {downloaded_file_path}")
    return slowdf


SLOWDF = _load_slow_thoughts()  # Takes a while
