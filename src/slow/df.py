"""Download or upload slow thoughts dataframe from the HF hub"""

import os
from io import BytesIO
from os.path import basename

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download

from src.config import CONFIG, ConfigArgumentParser
from src.log import info
from src.vertex import replace_variables

load_dotenv()

EMBED_MODEL_NAME = CONFIG("slow.embed.model.name")


def get_hf_slow_thoughts_file():
    embed_model_basename = basename(EMBED_MODEL_NAME)  # E.g. "BAAI/bge-m3" => "bge-m3"

    return replace_variables(
        CONFIG("slow.reddit.hf_slow_thoughts_file"),
        EMBED_MODEL_BASENAME=embed_model_basename,
    )


HF_API = HfApi()
HF_REPO_ID = CONFIG("slow.reddit.hf_repo_id")
HF_SLOW_THOUGHTS_FILE = get_hf_slow_thoughts_file()


def upload_slow_thoughts(sdf, verbose=False):
    if verbose:
        print(
            f"Uploading {HF_SLOW_THOUGHTS_FILE} to Hugging Face using `HF_TOKEN_WRITE` from .env file"
        )

    buffer = BytesIO()
    sdf.to_feather(buffer, compression="zstd")

    HF_TOKEN_WRITE = os.getenv("HF_TOKEN_WRITE")
    if not HF_TOKEN_WRITE:
        raise ValueError("HF_TOKEN_WRITE not found in .env file")

    commitinfo = HF_API.upload_file(
        path_or_fileobj=buffer,
        path_in_repo=HF_SLOW_THOUGHTS_FILE,
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        token=HF_TOKEN_WRITE,
    )

    if verbose:
        print(f"Uploaded {args.upload}. Additional commit information:")
        print(commitinfo)


def download_slow_thoughts():
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
    return slowdf

def _embedding_model_exists():
    """Validate the embedding model specified in config"""
    try:
        from src.slow.embed import MODEL
    except Exception:
        return False

    del MODEL
    return True


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

    parser.add_argument(
        "--upload",
        help="Interactively upload a .feather file containing slow thoughts to the HF hub",
    )

    args = parser.parse_args()

    if args.upload:
        df = pd.read_feather(args.upload)

        if not _embedding_model_exists():
            print(
                f"Config specifies an embedding model {EMBED_MODEL_NAME} that cannot be loaded"
            )
            exit(1)

        a = input(
            f"Assuming {args.upload} used the following embedding model: {EMBED_MODEL_NAME}. Correct? (y/N)"
        )
        if a.lower() != "y":
            exit(1)

        a = input(
            f"Upload {args.upload} to HF as file {HF_REPO_ID}/{HF_SLOW_THOUGHTS_FILE}? (y/N)"
        )
        if a.lower() != "y":
            exit(1)

        upload_slow_thoughts(df, verbose=True)
else:
    # Download and export the dataframe for use in other modules (takes a while)
    SLOWDF = download_slow_thoughts()
    info(f"Loaded {len(SLOWDF)} slow thoughts")
