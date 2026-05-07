"""
language/translate.py — Amharic ↔ English translation helpers.

Primary:  Google Gemini API (online, high quality)
Fallback: argostranslate (offline, must be installed separately)
Last resort: return original text unchanged.
"""

from utils.logger import get_logger

log = get_logger("translate")


def translate(text: str, source_lang: str, target_lang: str,
              gemini_available: bool = False) -> str:
    """
    Translate text between languages.
    Returns translated string, or original on failure.
    """
    if source_lang == target_lang:
        return text

    # ── Online: Gemini translation ────────────────────────────────────────
    if gemini_available:
        try:
            import google.generativeai as genai
            from config import GEMINI_API_KEY, GEMINI_MODEL
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            prompt = (
                f"Translate the following text from {source_lang} to {target_lang}. "
                f"Return ONLY the translated text, nothing else.\n\n{text}"
            )
            resp = model.generate_content(prompt)
            result = resp.text.strip()
            log.debug(f"Translated ({source_lang}→{target_lang}) via Gemini")
            return result
        except Exception as e:
            log.warning(f"Gemini translation failed: {e}")

    # ── Offline: argostranslate ───────────────────────────────────────────
    try:
        import argostranslate.package
        import argostranslate.translate

        # Map codes to Argos format
        lang_map = {"am": "am", "en": "en"}
        src = lang_map.get(source_lang, source_lang)
        tgt = lang_map.get(target_lang, target_lang)

        translated = argostranslate.translate.translate(text, src, tgt)
        log.debug(f"Translated ({source_lang}→{target_lang}) via argostranslate")
        return translated
    except ImportError:
        log.warning("argostranslate not installed — returning original text")
    except Exception as e:
        log.warning(f"argostranslate error: {e} — returning original text")

    return text   # last resort


def amharic_to_english(text: str, gemini_available: bool = False) -> str:
    return translate(text, "am", "en", gemini_available)


def english_to_amharic(text: str, gemini_available: bool = False) -> str:
    return translate(text, "en", "am", gemini_available)
