import os

import dotenv

from pinecone.grpc import PineconeGRPC as Pinecone
from src.config import CONFIG

dotenv.load_dotenv()


INDEX = CONFIG("pinecone.index")
NAMESPACE = CONFIG("pinecone.namespace")
METADATA_SIZE_THRESHOLD = CONFIG("pinecone.metadata_size_threshold")


def resolve_index(name=INDEX):
    api_key = os.getenv("PINECONE_API_KEY")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(name)
    return index


def get_ids_present(index=INDEX, namespace=NAMESPACE):
    for ids in index.list(namespace=namespace):
        for id in ids:
            yield id
