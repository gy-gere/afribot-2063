"""
tests/test_llm.py — Test AI routing and responses.

Run:  python -m tests.test_llm
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_language_detection():
    from language.detect import detect_language
    print("\n=== TEST: Language Detection ===\n")

    cases = [
        ("What is Faraday's Law?",                  "en"),
        ("ፋራዳይ ህግ ምንድን ነው?",                        "am"),
        ("የኤሌክትሪክ ማሽን ምንድን ነው",                      "am"),
        ("Explain how a transformer works",           "en"),
        ("ማግኔቲክ ፍሰት ማለት ምን ማለት ነው?",               "am"),
    ]

    for text, expected in cases:
        detected = detect_language(text)
        status   = "✅" if detected == expected else "❌"
        print(f"  {status} '{text[:40]}' → {detected} (expected {expected})")

    print()


def test_offline_routing():
    from models.local_llm import is_ollama_running

    print("=== TEST: Offline Routing ===\n")

    if not is_ollama_running():
        print("  ⚠ Ollama not running — skipping offline test")
        print("  Start Ollama with: ollama serve")
        return

    from models.router import answer
    q = "What is Ampere's Law?"
    print(f"  Q: {q}")
    resp, source = answer(q, language="en", force_offline=True)
    print(f"  Source: {source}")
    print(f"  A: {resp[:200]}…\n")
    assert len(resp) > 10, "Response too short"
    print("  ✅ Offline routing OK\n")


def test_online_routing():
    from utils.internet import is_online
    from config import GEMINI_API_KEY

    print("=== TEST: Online Routing (Gemini) ===\n")

    if not is_online():
        print("  ⚠ No internet — skipping online test")
        return

    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("  ⚠ Gemini API key not set — skipping")
        return

    from models.router import answer
    q = "ፋራዳይ ህግ ምንድን ነው?"
    print(f"  Q: {q}")
    resp, source = answer(q, language="am")
    print(f"  Source: {source}")
    print(f"  A: {resp[:200]}…\n")
    assert len(resp) > 10, "Response too short"
    print("  ✅ Online routing OK\n")


if __name__ == "__main__":
    test_language_detection()
    test_offline_routing()
    test_online_routing()
    print("All tests complete.")
