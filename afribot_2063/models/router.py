"""
models/router.py — Route questions to the best available AI.

Decision logic:
  1. Check internet availability
  2. If online  → try Gemini; on failure fall back to local
  3. If offline → use local Ollama
  ALWAYS include RAG context from ChromaDB
"""

from utils.logger  import get_logger
from utils.internet import is_online

log = get_logger("router")


def answer(question: str, language: str = "en",
           force_offline: bool = False) -> tuple[str, str]:
    """
    Get an answer for the question.

    Returns:
        (answer_text, source)   where source ∈ {"gemini", "local", "fallback"}
    """
    from rag.query import retrieve_context

    # ── 1. Retrieve RAG context ───────────────────────────────────────────
    log.info("Retrieving RAG context…")
    context = retrieve_context(question)
    if context:
        log.debug(f"Context retrieved ({len(context)} chars)")
    else:
        log.warning("No context found in vector DB — answering from model only")

    # ── 2. Route to AI ───────────────────────────────────────────────────
    online = (not force_offline) and is_online()

    if online:
        log.info("Mode: ONLINE → trying Gemini…")
        try:
            from models.gemini_llm import ask_gemini
            answer_text = ask_gemini(question, context=context, language=language)
            return answer_text, "gemini"
        except Exception as e:
            log.warning(f"Gemini failed ({e}), falling back to local model…")

    log.info("Mode: OFFLINE → using local Ollama…")
    try:
        from models.local_llm import ask_local
        answer_text = ask_local(question, context=context, language=language)
        return answer_text, "local"
    except Exception as e:
        log.error(f"Local model also failed: {e}")
        # Last-resort fallback: return the raw context if any
        if context:
            fallback = (
                "I could not reach either AI, but here is the relevant information "
                "from the textbook:\n\n" + context[:800]
            )
        else:
            fallback = (
                "I am currently unable to connect to any AI model. "
                "Please ensure Ollama is running or check your internet connection."
            )
        return fallback, "fallback"
