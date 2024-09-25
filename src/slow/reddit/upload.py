"""Upload a post .feather file to Pinecone"""

from sys import exit

import dotenv
import numpy as np
import pandas as pd

from src.config import ConfigArgumentParser
from src.pinecone import (
    INDEX,
    METADATA_SIZE_THRESHOLD,
    NAMESPACE,
    get_ids_present,
    resolve_index,
)
from src.slow.embed import is_valid_vector

dotenv.load_dotenv()


def validate(df):
    assert np.all(df["score"] > 0)
    assert np.all(df["post"].str.len() > 0)
    assert len(df) == df.index.nunique()


def utf8_length(s):
    if pd.isna(s):
        return 0
    return len(s.encode("utf-8"))


def main(args):
    print(f"Connecting to Pinecone index {INDEX}")
    index = resolve_index()

    print(f"Loading {args.postfile}")
    pdf = pd.read_feather(args.postfile)

    print("Finding eligible posts to upload")
    processed = pdf[pdf.embedding.notna()]
    valid = processed["embedding"].apply(is_valid_vector)
    eligible = processed[valid]

    print("Validating")
    validate(eligible)

    print("Finding ids of posts to upload")
    ids_present = list(get_ids_present(index))
    todo = ~eligible.index.isin(ids_present)
    df_to_upload = eligible[todo]

    print("Screening texts for size...", end=" ")
    size = df_to_upload["post"].apply(utf8_length)
    threshold = int(0.9 * METADATA_SIZE_THRESHOLD)
    reject = size > threshold
    df_to_upload = df_to_upload[~reject]
    print(f"rejected {reject.sum()} posts")

    print(f"Converting {len(df_to_upload)} posts to Pinecone format")
    pinecone_df = pd.DataFrame(
        {
            "id": df_to_upload.index,
            "values": df_to_upload["embedding"],
            "metadata": df_to_upload["post"].apply(lambda x: {"text": x}),
        }
    )

    print(f"Upserting to index {INDEX}(namespace={NAMESPACE})")
    index.upsert_from_dataframe(pinecone_df, namespace=NAMESPACE)

    return 0


if __name__ == "__main__":
    parser = ConfigArgumentParser(description=__doc__)

    parser.add_argument("postfile", help="Post .feather file containing posts")

    args = parser.parse_args()

    exit(main(args))
