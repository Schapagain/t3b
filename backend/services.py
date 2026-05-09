import os
import chromadb
from openai import AsyncOpenAI
from functools import lru_cache
from constants import OPENAI_EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    """
    Create and return an OpenAI client using API key from environment.

    Returns:
        Configured OpenAI client instance.

    Raises:
        EnvironmentError: If OPENAI_API_KEY is not set.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not found in environment variables")
    return AsyncOpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """
    Create a persistent ChromaDB client at the location defined.
    in the environment variable: CHROMA_DB_PATH

    Returns:
        ChromaDB PersistentClient instance.
    """
    db_path = os.getenv("CHROMA_DB_PATH")
    if not db_path:
        raise EnvironmentError("CHROMA_DB_PATH not found in environment variables")
    return chromadb.PersistentClient(path=db_path)


@lru_cache(maxsize=None)
def get_collection(collection_name: str) -> chromadb.Collection:
    """
    Get an existing collection or a new one.

    Args:
        collection_name: Name of the collection.

    Returns:
        ChromaDB Collection instance.
    """
    chroma_client = get_chroma_client()
    return chroma_client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}  # Use cosine similarity
    )
