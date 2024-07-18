"""Make the seed posts for the SLOW stream from raw posts and vetting information and upload to Hugging Face"""

import os
from io import BytesIO
from sys import exit

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import HfApi

from src.config import ConfigArgumentParser, config

load_dotenv()

HF_API = HfApi()


def main(args):
    pdf = pd.read_feather(args.postfile)
    vdf = pd.concat([pd.read_feather(vetfile) for vetfile in args.vetfiles])

    repo_id = config()["slow"]["reddit"]["hf_repo_id"]
    thoughts_file = config()["slow"]["reddit"]["hf_thoughts_file"]

    duplicates = vdf.index.duplicated(keep="first")
    print(
        f"Found {duplicates.sum()} posts that have been vetted more than once (keeping first)"
    )
    vdf = vdf[~duplicates]

    print(
        "Score distribution: (+1 => GOOD; -1 => BAD; 0 => undecided or error during autovetting)"
    )
    print(vdf.value_counts())

    good = vdf[vdf["score"] == 1]
    sdf = pdf.loc[good.index]
    print(f"Kept {len(sdf)} GOOD posts")

    print("Anonymizing data")
    sdf.reset_index(drop=True, inplace=True)
    sdf = sdf[["post", "embedding"]]
    sdf.rename(columns={"post": "thought"}, inplace=True)

    print(
        f"Uploading {thoughts_file} to Hugging Face using `HF_TOKEN_WRITE` from .env file"
    )
    buffer = BytesIO()
    sdf.to_feather(buffer, compression="zstd")

    HF_TOKEN_WRITE = os.getenv("HF_TOKEN_WRITE")
    if not HF_TOKEN_WRITE:
        raise ValueError("HF_TOKEN_WRITE not found in .env file")

    HF_API.upload_file(
        path_or_fileobj=buffer,
        path_in_repo=thoughts_file,
        repo_id=repo_id,
        repo_type="dataset",
        token=HF_TOKEN_WRITE,
    )

    return 0


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

    parser.add_argument("postfile", help="Post .feather file containing posts")
    parser.add_argument("vetfiles", nargs="+", help="One or more vet .feather files")

    args = parser.parse_args()

    exit(main(args))