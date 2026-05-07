"""
tests/test_rag.py — Test RAG retrieval pipeline.

Run:  python -m tests.test_rag
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ingest_and_query():
    from rag.ingest import ingest_all, get_chroma_collection
    from rag.query  import retrieve_context, retrieve_chunks

    print("\n=== TEST: RAG Ingest & Query ===\n")

    # 1. Ingest PDFs
    print("Step 1: Ingesting PDFs…")
    count = ingest_all()
    print(f"  → {count} chunks ingested (0 = already in DB)\n")

    # 2. Check DB has data
    col = get_chroma_collection()
    total = col.count()
    print(f"Step 2: Total chunks in DB: {total}")
    assert total > 0, "DB is empty — check PDF directory"
    print("  ✅ DB has data\n")

    # 3. Run test queries
    test_queries = [
        "What is Faraday's Law?",
        "Explain magnetic flux and permeability",
        "What is an electrical machine?",
        "How does a transformer work?",
    ]

    print("Step 3: Query tests:")
    for q in test_queries:
        chunks = retrieve_chunks(q, top_k=2)
        print(f"\n  Q: {q}")
        if chunks:
            print(f"  → Top result (score={chunks[0]['similarity']}): {chunks[0]['text'][:120]}…")
        else:
            print("  ⚠ No results found")

    print("\n✅ RAG test complete\n")


if __name__ == "__main__":
    test_ingest_and_query()
