"""
speech/tts.py — Text-to-Speech for AfriBot-2063.

Primary:   pyttsx3 (offline, cross-platform)
Amharic:   gTTS (online cloud TTS — better Amharic support)
Fallback:  print to console
"""

import os
import tempfile
from utils.logger import get_logger

log = get_logger("tts")


# ─────────────────────────────────────────────────────────────────────────────
# pyttsx3 offline TTS
# ─────────────────────────────────────────────────────────────────────────────

_pyttsx3_engine = None

def _get_pyttsx3():
    global _pyttsx3_engine
    if _pyttsx3_engine is None:
        import pyttsx3
        from config import TTS_RATE, TTS_VOLUME
        engine = pyttsx3.init()
        engine.setProperty("rate",   TTS_RATE)
        engine.setProperty("volume", TTS_VOLUME)
        _pyttsx3_engine = engine
    return _pyttsx3_engine


def speak_offline(text: str) -> bool:
    """Use pyttsx3 to speak text. Returns True on success."""
    try:
        engine = _get_pyttsx3()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        log.warning(f"pyttsx3 failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# gTTS online TTS (better Amharic)
# ─────────────────────────────────────────────────────────────────────────────

def speak_gtts(text: str, lang: str = "am") -> bool:
    """
    Use Google Text-to-Speech (requires internet + gTTS package).
    Returns True on success.
    """
    try:
        from gtts import gTTS
        import pygame

        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        tts.save(tmp_path)

        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        os.unlink(tmp_path)
        return True
    except ImportError:
        log.warning("gTTS or pygame not installed — falling back to pyttsx3")
        return False
    except Exception as e:
        log.warning(f"gTTS failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def speak(text: str, language: str = "en") -> None:
    """
    Speak the given text in the detected language.

    Strategy:
      - Amharic + online → try gTTS (best Amharic voice)
      - Otherwise        → pyttsx3 offline
      - Final fallback   → print to console
    """
    if not text or not text.strip():
        return

    log.info(f"Speaking ({language}): {text[:60]}…")

    from utils.internet import is_online

    if language == "am" and is_online():
        if speak_gtts(text, lang="am"):
            return

    if speak_offline(text):
        return

    # Last resort
    print(f"\n🔊 [AfriBot]: {text}\n")
