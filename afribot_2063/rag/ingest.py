"""
rag/ingest.py — Load PDFs → chunk → embed → store in ChromaDB.

Run once (or after adding new PDFs):
    python -m rag.ingest
"""

import os
import re
import hashlib
from pathlib import Path
from tqdm import tqdm

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from utils.logger import get_logger

log = get_logger("ingest")


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF using pypdf with pdfplumber fallback."""
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        log.debug(f"pypdf extracted {len(text)} chars from {Path(pdf_path).name}")
    except Exception as e:
        log.warning(f"pypdf failed ({e}), trying pdfplumber…")
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        except Exception as e2:
            log.error(f"pdfplumber also failed: {e2}")
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks.
    Prefers splitting on paragraph/sentence boundaries.
    """
    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks = []
    start  = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        # Try to break on a sentence boundary near the end
        if end < length:
            for sep in ["\n\n", ".\n", ". ", "\n", " "]:
                boundary = text.rfind(sep, start + chunk_size // 2, end)
                if boundary != -1:
                    end = boundary + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Embedding model (singleton)
# ─────────────────────────────────────────────────────────────────────────────

_embed_model: SentenceTransformer | None = None

def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        log.info("Loading embedding model (all-MiniLM-L6-v2)…")
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_chroma_collection():
    from config import CHROMA_DB_PATH, COLLECTION_NAME
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def doc_id(pdf_name: str, chunk_index: int) -> str:
    return hashlib.md5(f"{pdf_name}_{chunk_index}".encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Main ingest pipeline
# ─────────────────────────────────────────────────────────────────────────────

def ingest_pdf(pdf_path: str, force: bool = False) -> int:
    """
    Ingest one PDF file into ChromaDB.
    Returns number of chunks added.
    """
    from config import CHUNK_SIZE, CHUNK_OVERLAP

    pdf_name = Path(pdf_path).name
    log.info(f"Ingesting: {pdf_name}")

    collection = get_chroma_collection()
    embed_model = get_embed_model()

    # Check if already ingested
    existing = collection.get(where={"source": pdf_name})
    if existing["ids"] and not force:
        log.info(f"  → Already in DB ({len(existing['ids'])} chunks). Use force=True to re-ingest.")
        return 0

    # Extract & chunk
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        log.warning(f"  → No text extracted from {pdf_name}")
        return 0

    chunks = chunk_text(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
    log.info(f"  → {len(chunks)} chunks from {len(raw_text):,} characters")

    # Embed & store in batches
    BATCH = 64
    added = 0
    for i in tqdm(range(0, len(chunks), BATCH), desc=f"  Embedding {pdf_name}"):
        batch_chunks = chunks[i: i + BATCH]
        embeddings   = embed_model.encode(batch_chunks, show_progress_bar=False).tolist()
        ids          = [doc_id(pdf_name, i + j) for j in range(len(batch_chunks))]
        metadatas    = [{"source": pdf_name, "chunk_index": i + j}
                        for j in range(len(batch_chunks))]

        # Upsert so re-runs don't duplicate
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=batch_chunks,
            metadatas=metadatas,
        )
        added += len(batch_chunks)

    log.info(f"  → Stored {added} chunks for {pdf_name}")
    return added


def ingest_text_file(txt_path: str, force: bool = False) -> int:
    """Ingest a plain .txt file into ChromaDB."""
    from config import CHUNK_SIZE, CHUNK_OVERLAP

    txt_name = Path(txt_path).name
    log.info(f"Ingesting text file: {txt_name}")

    collection  = get_chroma_collection()
    embed_model = get_embed_model()

    existing = collection.get(where={"source": txt_name})
    if existing["ids"] and not force:
        log.info(f"  → Already in DB. Use force=True to re-ingest.")
        return 0

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        log.error(f"  → Could not read {txt_name}: {e}")
        return 0

    chunks = chunk_text(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
    log.info(f"  → {len(chunks)} chunks from {len(raw_text):,} characters")

    BATCH = 64
    added = 0
    for i in tqdm(range(0, len(chunks), BATCH), desc=f"  Embedding {txt_name}"):
        batch_chunks = chunks[i: i + BATCH]
        embeddings   = embed_model.encode(batch_chunks, show_progress_bar=False).tolist()
        ids          = [doc_id(txt_name, i + j) for j in range(len(batch_chunks))]
        metadatas    = [{"source": txt_name, "chunk_index": i + j}
                        for j in range(len(batch_chunks))]
        collection.upsert(ids=ids, embeddings=embeddings,
                          documents=batch_chunks, metadatas=metadatas)
        added += len(batch_chunks)

    log.info(f"  → Stored {added} chunks for {txt_name}")
    return added


def ingest_all(force: bool = False) -> int:
    """Ingest every PDF and TXT in the configured PDF directory."""
    from config import PDF_DIR

    pdf_files = list(Path(PDF_DIR).glob("*.pdf"))
    txt_files = list(Path(PDF_DIR).glob("*.txt"))
    all_files = pdf_files + txt_files

    if not all_files:
        log.warning(f"No PDF or TXT files found in {PDF_DIR}")
        return 0

    total = 0
    for f in all_files:
        if f.suffix == ".pdf":
            total += ingest_pdf(str(f), force=force)
        elif f.suffix == ".txt":
            total += ingest_text_file(str(f), force=force)

    log.info(f"Ingest complete. Total chunks added: {total}")
    return total


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    parser = argparse.ArgumentParser(description="AfriBot-2063 PDF ingestor")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if already in DB")
    parser.add_argument("--pdf",   type=str, default=None, help="Ingest a specific PDF file")
    args = parser.parse_args()

    if args.pdf:
        ingest_pdf(args.pdf, force=args.force)
    else:
        ingest_all(force=args.force)
