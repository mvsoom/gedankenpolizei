"""Upload a post .feather file to Pinecone"""

import os
from sys import exit

import dotenv
import numpy as np
import pandas as pd
from pinecone.grpc import PineconeGRPC as Pinecone

from src.config import CONFIG, ConfigArgumentParser

dotenv.load_dotenv()


INDEX = CONFIG("pinecone.index")
NAMESPACE = CONFIG("pinecone.namespace")
METADATA_SIZE_THRESHOLD = CONFIG("pinecone.metadata_size_threshold")


def is_embedding_valid(embedding):
    return not np.any(np.isnan(embedding))


def validate(df):
    assert np.all(df["score"] > 0)
    assert np.all(df["post"].str.len() > 0)
    assert len(df) == df.index.nunique()


def get_ids_present(index):
    for ids in index.list(namespace=NAMESPACE):
        for id in ids:
            yield id


def utf8_length(s):
    if pd.isna(s):
        return 0
    return len(s.encode("utf-8"))


def main(args):
    print(f"Connecting to Pinecone index {INDEX}")
    api_key = os.getenv("PINECONE_API_KEY")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(INDEX)

    print(f"Loading {args.postfile}")
    pdf = pd.read_feather(args.postfile)

    print("Finding eligible posts to upload")
    processed = pdf[pdf.embedding.notna()]
    valid = processed["embedding"].apply(is_embedding_valid)
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
