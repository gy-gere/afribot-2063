"""
rag/query.py — Retrieve relevant document chunks for a given question.
"""

import chromadb
from chromadb.config import Settings

from utils.logger import get_logger

log = get_logger("query")

_collection = None   # module-level singleton


def get_collection():
    global _collection
    if _collection is None:
        from config import CHROMA_DB_PATH, COLLECTION_NAME
        import os
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def retrieve_context(query: str, top_k: int = None) -> str:
    """
    Query ChromaDB for the most relevant text chunks.
    Returns a concatenated context string ready to inject into a prompt.
    """
    from config import TOP_K_RESULTS
    from rag.ingest import get_embed_model

    top_k = top_k or TOP_K_RESULTS
    collection = get_collection()

    # Check we have any documents
    count = collection.count()
    if count == 0:
        log.warning("ChromaDB collection is empty. Run 'python -m rag.ingest' first.")
        return ""

    embed_model = get_embed_model()
    query_vec   = embed_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        log.debug("No matching chunks found.")
        return ""

    # Build context block
    parts = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
        source = meta.get("source", "unknown")
        score  = round(1 - dist, 3)   # cosine similarity
        parts.append(f"[Source: {source} | Relevance: {score}]\n{doc}")

    context = "\n\n---\n\n".join(parts)
    log.debug(f"Retrieved {len(docs)} chunks (top score: {round(1-distances[0],3)})")
    return context


def retrieve_chunks(query: str, top_k: int = None) -> list[dict]:
    """
    Same as retrieve_context but returns structured list of dicts.
    Useful for testing or custom formatting.
    """
    from config import TOP_K_RESULTS
    from rag.ingest import get_embed_model

    top_k = top_k or TOP_K_RESULTS
    collection = get_collection()

    if collection.count() == 0:
        return []

    embed_model = get_embed_model()
    query_vec   = embed_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {
            "text":       doc,
            "source":     meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", -1),
            "similarity": round(1 - dist, 3),
        }
        for doc, meta, dist in zip(docs, metadatas, distances)
    ]
