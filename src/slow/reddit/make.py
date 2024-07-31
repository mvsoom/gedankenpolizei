"""Make the seed posts for the SLOW stream from raw posts and vetting information and upload to Hugging Face"""

from sys import exit

import pandas as pd

from src.config import ConfigArgumentParser
from src.slow.df import upload_slow_thoughts


def main(args):
    pdf = pd.read_feather(args.postfile)
    vdf = pd.concat([pd.read_feather(vetfile) for vetfile in args.vetfiles])

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
    sdf.rename(columns={"post": "text"}, inplace=True)

    upload_slow_thoughts(sdf, verbose=True)

    return 0


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

    parser.add_argument("postfile", help="Post .feather file containing posts")
    parser.add_argument("vetfiles", nargs="+", help="One or more vet .feather files")

    args = parser.parse_args()

    exit(main(args))
