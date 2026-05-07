"""
models/local_llm.py — Offline AI using Ollama (tinyllama / phi / mistral).

Works with no internet. Requires Ollama running on localhost:11434.
"""

from utils.logger import get_logger

log = get_logger("local_llm")


def _build_prompt(question: str, context: str, language: str) -> str:
    """Build a prompt compatible with small local models."""

    if language == "am":
        lang_note = (
            "The student asked in Amharic. Try to respond in Amharic if possible, "
            "otherwise respond in English and note that Amharic response requires internet."
        )
    else:
        lang_note = "Respond in clear, simple English."

    ctx = f"\nContext from textbook:\n{context}\n" if context.strip() else ""

    return (
        f"You are AfriBot, an AI teacher for Ethiopian students studying electrical "
        f"machines, electronics, and robotics. {lang_note}"
        f"{ctx}"
        f"\nQuestion: {question}\n"
        f"Answer:"
    )


def ask_local(question: str, context: str = "", language: str = "en") -> str:
    """
    Query the local Ollama model.
    Returns response string or raises on connection failure.
    """
    import ollama
    from config import OLLAMA_MODEL, OLLAMA_BASE_URL

    prompt = _build_prompt(question, context, language)
    log.debug(f"Querying local model: {OLLAMA_MODEL}")

    try:
        client   = ollama.Client(host=OLLAMA_BASE_URL)
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            options={
                "temperature":   0.4,
                "num_predict":   512,   # limit tokens for low-RAM devices
                "num_ctx":       2048,
            },
        )
        answer = response["response"].strip()
        log.debug(f"Local model response: {answer[:80]}…")
        return answer

    except Exception as e:
        log.error(f"Ollama error: {e}")
        raise


def list_local_models() -> list[str]:
    """Return list of models available in local Ollama instance."""
    try:
        import ollama
        from config import OLLAMA_BASE_URL
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = client.list()
        return [m["name"] for m in models.get("models", [])]
    except Exception as e:
        log.warning(f"Could not list Ollama models: {e}")
        return []


def is_ollama_running() -> bool:
    """Quick check whether Ollama server is reachable."""
    try:
        import requests
        from config import OLLAMA_BASE_URL
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
