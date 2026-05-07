"""
models/gemini_llm.py — Google Gemini API integration (online AI).

Provides high-quality responses in both English and Amharic.
"""

from utils.logger import get_logger

log = get_logger("gemini")


def _build_prompt(question: str, context: str, language: str) -> str:
    """Build a structured prompt for Gemini with RAG context."""

    lang_instruction = {
        "am": (
            "You are AfriBot-2063, an AI teacher for Ethiopian students. "
            "The student asked in Amharic. Respond FULLY in Amharic (Ethiopic script). "
            "Explain clearly and simply so a student can understand."
        ),
        "en": (
            "You are AfriBot-2063, an AI teacher specialising in electrical machines, "
            "electronics, robotics, and TVET education for Ethiopian students. "
            "Respond in clear, simple English suitable for university students."
        ),
    }.get(language, "You are AfriBot-2063, an AI teacher. Respond helpfully.")

    context_block = (
        f"\n\nRelevant textbook content:\n{context}\n"
        if context.strip()
        else "\n\n(No textbook context available — answer from general knowledge.)\n"
    )

    return (
        f"{lang_instruction}"
        f"{context_block}"
        f"\nStudent question: {question}\n\n"
        "Provide a thorough, educational answer. "
        "If the context contains relevant formulas or definitions, include them."
    )


def ask_gemini(question: str, context: str = "", language: str = "en") -> str:
    """
    Send a question + RAG context to Gemini and return the answer.
    Raises on failure so the router can catch and fall back.
    """
    import google.generativeai as genai
    from config import GEMINI_API_KEY, GEMINI_MODEL

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("GEMINI_API_KEY is not set in config.py or environment.")

    genai.configure(api_key=GEMINI_API_KEY)
    model  = genai.GenerativeModel(GEMINI_MODEL)
    prompt = _build_prompt(question, context, language)

    log.debug(f"Sending to Gemini ({GEMINI_MODEL})…")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=1024,
        ),
    )

    answer = response.text.strip()
    log.debug(f"Gemini response: {answer[:80]}…")
    return answer
