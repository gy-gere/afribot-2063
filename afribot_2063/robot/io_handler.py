"""
robot/io_handler.py — Sensor and peripheral abstraction for AfriBot-2063.

Wraps microphone, speaker, camera, and button inputs in a unified API.
On desktop: falls back to keyboard input and console output.
"""

from utils.logger import get_logger

log = get_logger("io_handler")


class IOHandler:
    """Unified I/O interface for AfriBot or desktop."""

    def __init__(self, use_speech: bool = True, use_mic: bool = True):
        self.use_speech = use_speech
        self.use_mic    = use_mic

    # ── Input ─────────────────────────────────────────────────────────────

    def get_input(self, prompt_text: str = "You: ") -> str:
        """
        Get input from speech (mic) or keyboard.
        Returns raw text string.
        """
        if self.use_mic:
            from speech.stt import transcribe_microphone
            print(f"\n{prompt_text}(press Enter to record, or type your question)")
            choice = input().strip()
            if choice == "":
                text = transcribe_microphone(duration_seconds=6)
                if text:
                    print(f"  → Heard: {text}")
                    return text
                print("  (No speech detected, please type instead)")
            return choice
        else:
            return input(prompt_text).strip()

    # ── Output ────────────────────────────────────────────────────────────

    def output(self, text: str, language: str = "en"):
        """Print and optionally speak a response."""
        print(f"\n🤖 AfriBot: {text}\n")
        if self.use_speech:
            from speech.tts import speak
            speak(text, language=language)

    # ── Status ────────────────────────────────────────────────────────────

    def show_status(self, message: str):
        """Display a status message (progress, mode, etc.)."""
        print(f"   [{message}]")

    def show_banner(self):
        """Print startup banner."""
        banner = """
╔══════════════════════════════════════════════════════════╗
║           AfriBot-2063 Hybrid AI Teacher System          ║
║      Offline + Online | Amharic + English | TVET/EE      ║
╚══════════════════════════════════════════════════════════╝
        """
        print(banner)
