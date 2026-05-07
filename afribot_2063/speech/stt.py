"""
speech/stt.py — Speech-to-Text using faster-whisper.

Uses the "tiny" model (~75 MB) for low-resource devices.
Supports Amharic and English transcription.
"""

import os
import tempfile
from utils.logger import get_logger

log = get_logger("stt")

_whisper_model = None   # lazy-loaded singleton


def load_model():
    """Load faster-whisper model (lazy, once per session)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        from config import WHISPER_MODEL, WHISPER_DEVICE
        log.info(f"Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}…")
        _whisper_model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type="int8",   # saves memory
        )
        log.info("Whisper model loaded.")
    return _whisper_model


def transcribe_file(audio_path: str, language: str = None) -> str:
    """
    Transcribe an audio file.

    Args:
        audio_path: path to .wav / .mp3 / .m4a file
        language:   ISO 639-1 code ("am", "en") or None for auto-detect

    Returns:
        Transcribed text string.
    """
    model = load_model()

    # Whisper uses "am" for Amharic internally
    whisper_lang = None
    if language == "am":
        whisper_lang = "am"
    elif language == "en":
        whisper_lang = "en"
    # None = auto-detect

    segments, info = model.transcribe(
        audio_path,
        language=whisper_lang,
        beam_size=5,
        vad_filter=True,         # skip silence
    )

    detected_lang = info.language
    text = " ".join(seg.text.strip() for seg in segments).strip()

    log.info(f"Transcribed ({detected_lang}): {text[:80]}…")
    return text


def transcribe_microphone(duration_seconds: int = 5) -> str:
    """
    Record from the default microphone and transcribe.
    Requires: sounddevice, scipy

    Returns:
        Transcribed text string.
    """
    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io.wavfile import write as wav_write

        SAMPLE_RATE = 16000   # Whisper expects 16 kHz
        log.info(f"Recording for {duration_seconds}s… (speak now)")
        print(f"\n🎤 Recording for {duration_seconds}s — speak now…")

        audio_data = sd.rec(
            int(duration_seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        print("✅ Recording done.")

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        wav_write(tmp_path, SAMPLE_RATE, audio_data)

        text = transcribe_file(tmp_path)

        os.unlink(tmp_path)
        return text

    except ImportError as e:
        log.warning(f"Microphone recording unavailable: {e}")
        log.info("Install sounddevice and scipy for microphone support.")
        return ""
    except Exception as e:
        log.error(f"Microphone transcription failed: {e}")
        return ""
