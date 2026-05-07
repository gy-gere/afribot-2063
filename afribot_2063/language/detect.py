"""
language/detect.py — Detect Amharic vs English (and other languages).

Strategy:
1. Check for Amharic Unicode range U+1200–U+137F (Ethiopic script).
   This is 100 % reliable and requires no library.
2. Fall back to langdetect for other language disambiguation.
"""

import re
from utils.logger import get_logger

log = get_logger("detect")

# Ethiopic Unicode block: covers Amharic, Tigrinya, Ge'ez
_ETHIOPIC_RE = re.compile(r"[\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF\uAB00-\uAB2F]")


def detect_language(text: str) -> str:
    """
    Returns ISO 639-1 code:
      'am'  — Amharic / Ethiopic script detected
      'en'  — English or Latin-script default
      other — langdetect result
    """
    if not text or not text.strip():
        return "en"

    # Fast path: count Ethiopic characters
    ethiopic_chars = len(_ETHIOPIC_RE.findall(text))
    total_alpha    = len(re.findall(r"[^\s\d\W]", text))

    if total_alpha > 0 and (ethiopic_chars / total_alpha) > 0.3:
        log.debug(f"Language → am (Ethiopic ratio {ethiopic_chars}/{total_alpha})")
        return "am"

    # Fall back to langdetect
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42          # deterministic
        lang = detect(text)
        log.debug(f"Language → {lang} (langdetect)")
        return lang
    except Exception as e:
        log.warning(f"langdetect failed: {e} — defaulting to 'en'")
        return "en"


def is_amharic(text: str) -> bool:
    return detect_language(text) == "am"


def is_english(text: str) -> bool:
    return detect_language(text) == "en"
