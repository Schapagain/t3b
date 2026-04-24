from datetime import timedelta

OPENAI_CHAT_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

COLLECTION_NAME = "cards"
MAX_AGENT_ITERATIONS = 4
TRELLO_SYNC_TTL = timedelta(minutes=30)
VECTOR_SIMILARITY_THRESHOLD = 0.35
