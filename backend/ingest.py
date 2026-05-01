from trello import get_all_cards
from services import get_collection, get_openai_client, OPENAI_EMBEDDING_MODEL
from trello import Card
from datetime import datetime
from constants import COLLECTION_NAME, VECTOR_SIMILARITY_THRESHOLD

last_synced_at: datetime | None = None
_sync_status = {"last_synced_at": None}


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
        assignee = (card.assignee or "").lower()

        metadatas.append(
            {
                "id": card.id,
                "name": card.name,
                "desc": card.desc or "",
                "due": card.due or 0.0,
                "url": card.url,
                "status": card.status,
                "assignee": assignee,
                "assignee_first_name": (assignee.split()[0]) if assignee else "",
                "assignee_last_name": (assignee.split()[-1]) if assignee else "",
            }
        )
    embeddings = get_embeddings(card_texts)
    print("Embeddings received.")
    collection = get_collection(COLLECTION_NAME)
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
    last_synced_at = datetime.now()
    _sync_status["last_synced_at"] = last_synced_at
    return {"cards_ingested": len(cards), "synced_at": last_synced_at}


def get_last_synced_at() -> datetime:
    """
    Get the timestamp for the last Trello sync (if any)
    """
    return _sync_status["last_synced_at"]


# VECTOR SEARCH
def vector_search(
    query: str, top_k: int, cards: list[Card] = []
) -> list[tuple[str, float, str, dict]]:
    """
    Search ChromaDB collection using vector similarity.

    Args:
        query: search query.
        top_k: number of results to return.
        cards: subset of cards to search (if any)

    Returns:
        List of tuples: (id, similarity_score, document_text, metadata)
    """

    collection = get_collection(COLLECTION_NAME)
    query_embedding = get_embeddings([query])[0]
    card_ids = [card["id"] for card in cards] if cards else None

    # ChromaDB query needs to include "documents", "distances", and "metadatas"
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "distances",
            "metadatas",
        ],
        ids=card_ids,
    )

    # Extract results from nested structure
    ids = results["ids"][0] if results["ids"] else []
    documents = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results["distances"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    # For cosine distance: similarity = 1 - distance
    results = []
    for i in range(len(ids)):
        similarity = 1.0 - distances[i]
        results.append(
            (
                ids[i],
                similarity,
                documents[i],
                metadatas[i] if i < len(metadatas) else {},
            )
        )

    print(f"\nTop {top_k} Vector Results (threshold: {VECTOR_SIMILARITY_THRESHOLD}):")
    for i, (doc_id, similarity, text, metadata) in enumerate(results, 1):
        print(f"\n[{i}] Similarity: {similarity:.4f} | ID: {doc_id}")
        print(f"    {text[:200]}...")

    results = [
        (id, sim, doc, meta)
        for id, sim, doc, meta in results
        if sim >= VECTOR_SIMILARITY_THRESHOLD
    ]

    return results
