import os

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

from src.config import CONFIG

# Load the token from .env file
load_dotenv()
HF_TOKEN_READ = os.getenv("HF_TOKEN_READ")

if not HF_TOKEN_READ:
    raise ValueError("`HF_TOKEN_READ` token is not set in the .env file")


HF_REPO_ID = CONFIG("slow.reddit.hf_repo_id")
HF_SLOW_THOUGHTS_FILE = CONFIG("slow.reddit.hf_slow_thoughts_file")

# Download the file with caching
downloaded_file_path = hf_hub_download(
    repo_id=HF_REPO_ID,
    filename=HF_SLOW_THOUGHTS_FILE,
    repo_type="dataset",
    use_auth_token=HF_TOKEN_READ,
)

print(f"File downloaded to {downloaded_file_path}")

import pandas as pd

thoughts = pd.read_feather(downloaded_file_path)

from src.slow.reddit.makeposts import printpost

while True:
    printpost(thoughts.sample()["thought"].values[0])
    input("Press Enter for another thought, or Ctrl+C to exit")
    print()
    print()
    print()