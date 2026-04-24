from trello import get_all_cards
from services import get_collection, get_openai_client, OPENAI_EMBEDDING_MODEL
from trello import Card

CHROMA_COLLECTION = "cards"


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI's embedding API.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    client = get_openai_client()
    response = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
    embeddings = [item.embedding for item in response.data]

    return embeddings


def upsert_cards(cards: list[Card]) -> None:
    """

    Upsert provided cards' text contents into ChromaDB with their embeddings.
    Upsert is idempotent: if an ID already exists, it will be updated.

    Args:
        card_texts: List of text contents in cards
    """
    ids = []
    card_texts = []
    metadatas = []
    for card in cards:
        ids.append(card.id)
        card_texts.append(card.name + " " + card.desc)
        metadatas.append(
            {
                "due": card.due or "",
                "url": card.url,
                "status": card.status,
                "assignee": card.assignee or "",
            }
        )
    embeddings = get_embeddings(card_texts)
    print("Embeddings received.")
    collection = get_collection(CHROMA_COLLECTION)
    print("Upserting to collection.")
    collection.upsert(
        documents=card_texts, embeddings=embeddings, metadatas=metadatas, ids=ids
    )


def re_index_db() -> dict[str, int]:
    """

    Get all cards from Trello, embed them, and
    upsert to ChromaDB

    """
    print("Re-indexing database.")
    cards = get_all_cards()
    print(f"Fetched {len(cards)} cards to ingest.")
    upsert_cards(cards)
    print("Re-ingestion done.")
    return {"cards_ingested": len(cards)}
