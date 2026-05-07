"""
main.py — AfriBot-2063 Hybrid AI Teacher System
Entry point. Run with:
    python main.py              # text-only mode
    python main.py --speech     # speech I/O mode
    python main.py --ingest     # (re)ingest PDFs and exit
    python main.py --offline    # force offline mode
"""

import sys
import os
import argparse

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger   import get_logger
from utils.internet import is_online

log = get_logger("main")


# ─────────────────────────────────────────────────────────────────────────────
# Session loop
# ─────────────────────────────────────────────────────────────────────────────

def run_session(use_speech: bool = False, force_offline: bool = False):
    """Main interactive session loop."""
    from language.detect  import detect_language
    from models.router    import answer
    from robot.io_handler import IOHandler
    from robot.controller import robot

    io = IOHandler(use_speech=use_speech, use_mic=use_speech)
    io.show_banner()

    # Show mode
    online = is_online() and not force_offline
    mode_str = "ONLINE (Gemini + RAG)" if online else "OFFLINE (Ollama + RAG)"
    io.show_status(f"Mode: {mode_str}")
    io.show_status("PDF knowledge: machines_1.pdf (Electrical Machines, Debre Berhan University)")
    io.show_status("Languages: English + Amharic | Type 'quit' to exit\n")

    robot.greet()

    # ── Main loop ─────────────────────────────────────────────────────────
    while True:
        try:
            # Get input
            question = io.get_input("You: ")

            if not question.strip():
                continue

            if question.lower() in {"quit", "exit", "q", "ወጣ", "ውጣ"}:
                io.output("Goodbye! / ቸር ሁን!", language="en")
                break

            # Detect language
            lang = detect_language(question)
            log.info(f"Question [{lang}]: {question}")

            # Show thinking indicator
            robot.set_thinking(True)
            io.show_status(f"Thinking… (lang={lang})")

            # Get answer
            resp_text, source = answer(
                question,
                language=lang,
                force_offline=force_offline,
            )

            robot.set_thinking(False)
            io.show_status(f"Source: {source}")

            # Respond
            robot.set_speaking(True)
            io.output(resp_text, language=lang)
            robot.set_speaking(False)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            io.output(f"An error occurred: {e}")

    robot.cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AfriBot-2063 — Hybrid AI Teacher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # text mode (default)
  python main.py --speech           # enable speech I/O
  python main.py --offline          # force offline (Ollama)
  python main.py --ingest           # ingest PDFs into vector DB
  python main.py --ingest --force   # re-ingest (overwrite existing)
  python main.py --test             # run diagnostic tests
        """,
    )
    parser.add_argument("--speech",  action="store_true", help="Enable speech I/O (mic + speaker)")
    parser.add_argument("--offline", action="store_true", help="Force offline mode (skip Gemini)")
    parser.add_argument("--ingest",  action="store_true", help="Ingest PDFs into vector DB and exit")
    parser.add_argument("--force",   action="store_true", help="Force re-ingest even if already done")
    parser.add_argument("--test",    action="store_true", help="Run diagnostic tests")
    args = parser.parse_args()

    # ── Ingest mode ──────────────────────────────────────────────────────
    if args.ingest:
        from rag.ingest import ingest_all
        print("AfriBot-2063 — PDF Ingestor")
        print("=" * 40)
        n = ingest_all(force=args.force)
        print(f"\nDone. {n} new chunks added to vector database.")
        return

    # ── Test mode ────────────────────────────────────────────────────────
    if args.test:
        print("Running diagnostics…")
        from tests.test_rag import test_ingest_and_query
        from tests.test_llm import test_language_detection, test_offline_routing, test_online_routing
        test_ingest_and_query()
        test_language_detection()
        test_offline_routing()
        test_online_routing()
        return

    # ── Auto-ingest if DB is empty ────────────────────────────────────────
    try:
        from rag.query import get_collection
        col = get_collection()
        if col.count() == 0:
            log.info("Vector DB is empty — auto-ingesting PDFs…")
            from rag.ingest import ingest_all
            ingest_all()
    except Exception as e:
        log.warning(f"Could not check/ingest PDFs: {e}")

    # ── Main session ─────────────────────────────────────────────────────
    run_session(use_speech=args.speech, force_offline=args.offline)


if __name__ == "__main__":
    main()
