"""
ui/server.py — Flask API backend for AfriBot-2063 Web UI

Exposes:
  POST /api/ask          — Ask a text question
  POST /api/voice        — Upload audio, transcribe, ask
  GET  /api/status       — System health check
  POST /api/ingest       — Trigger PDF ingest
  GET  /api/chunks       — Search raw RAG chunks
  GET  /                 — Serve the main HTML UI

Run:
  python ui/server.py
  # or with auto-reload:
  flask --app ui/server run --port 5000 --reload
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import threading
import time
import psutil

from flask import Flask, request, jsonify, send_from_directory, render_template_string

from utils.logger   import get_logger
from utils.internet import is_online

log = get_logger("ui_server")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload

# ── Lazy boot: ingest if DB empty ─────────────────────────────────────────────
_booted = False

def boot():
    global _booted
    if _booted:
        return
    _booted = True
    try:
        from rag.query  import get_collection
        from rag.ingest import ingest_all
        if get_collection().count() == 0:
            log.info("Auto-ingesting PDFs on first start…")
            threading.Thread(target=ingest_all, daemon=True).start()
    except Exception as e:
        log.warning(f"Boot ingest skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    boot()
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "static"),
        "index.html"
    )


@app.route("/api/status", methods=["GET"])
def status():
    boot()
    online = is_online()

    # Ollama check
    try:
        from models.local_llm import is_ollama_running
        ollama_ok = is_ollama_running()
    except Exception:
        ollama_ok = False

    # DB stats
    try:
        from rag.query import get_collection
        col        = get_collection()
        db_chunks  = col.count()
        sources    = set()
        if db_chunks > 0:
            sample = col.get(limit=min(db_chunks, 200), include=["metadatas"])
            for m in sample["metadatas"]:
                sources.add(m.get("source", "unknown"))
    except Exception:
        db_chunks, sources = 0, set()

    # System resources
    mem   = psutil.virtual_memory()
    cpu   = psutil.cpu_percent(interval=0.2)

    return jsonify({
        "online":        online,
        "ollama":        ollama_ok,
        "gemini_ready":  online,
        "db_chunks":     db_chunks,
        "db_sources":    list(sources),
        "ram_used_pct":  mem.percent,
        "ram_used_gb":   round(mem.used / 1e9, 2),
        "ram_total_gb":  round(mem.total / 1e9, 2),
        "cpu_pct":       cpu,
        "mode":          "online" if online else "offline",
    })


@app.route("/api/ask", methods=["POST"])
def ask():
    boot()
    data     = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    force_offline = bool(data.get("force_offline", False))
    top_k    = int(data.get("top_k", 4))

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        from language.detect import detect_language
        from models.router   import answer
        from rag.query       import retrieve_chunks

        lang   = detect_language(question)
        chunks = retrieve_chunks(question, top_k=top_k)

        t0             = time.time()
        answer_text, source = answer(question, language=lang, force_offline=force_offline)
        elapsed        = round(time.time() - t0, 2)

        return jsonify({
            "question":  question,
            "answer":    answer_text,
            "language":  lang,
            "source":    source,
            "elapsed_s": elapsed,
            "chunks": [
                {
                    "text":       c["text"][:400],
                    "source":     c["source"],
                    "similarity": c["similarity"],
                }
                for c in chunks
            ],
        })

    except Exception as e:
        log.error(f"/api/ask error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/voice", methods=["POST"])
def voice():
    boot()
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files["audio"]
    suffix     = os.path.splitext(audio_file.filename)[1] or ".webm"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
    audio_file.save(tmp_path)

    try:
        # Convert to wav for Whisper
        wav_path = tmp_path.replace(suffix, ".wav")
        ret = os.system(
            f"ffmpeg -y -i '{tmp_path}' -ar 16000 -ac 1 '{wav_path}' -loglevel quiet"
        )
        input_path = wav_path if ret == 0 and os.path.exists(wav_path) else tmp_path

        from speech.stt import transcribe_file
        transcript = transcribe_file(input_path)

        os.unlink(tmp_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)

        if not transcript:
            return jsonify({"error": "Could not transcribe audio"}), 422

        # Now answer the transcribed question
        from language.detect import detect_language
        from models.router   import answer
        from rag.query       import retrieve_chunks

        lang            = detect_language(transcript)
        chunks          = retrieve_chunks(transcript, top_k=4)
        answer_text, source = answer(transcript, language=lang)

        return jsonify({
            "transcript": transcript,
            "question":   transcript,
            "answer":     answer_text,
            "language":   lang,
            "source":     source,
            "chunks": [
                {"text": c["text"][:400], "source": c["source"], "similarity": c["similarity"]}
                for c in chunks
            ],
        })

    except Exception as e:
        log.error(f"/api/voice error: {e}", exc_info=True)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 500


@app.route("/api/ingest", methods=["POST"])
def ingest():
    def _run():
        from rag.ingest import ingest_all
        ingest_all(force=False)
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"message": "Ingest started in background."})


@app.route("/api/chunks", methods=["GET"])
def search_chunks():
    boot()
    query = request.args.get("q", "").strip()
    top_k = int(request.args.get("k", 5))

    if not query:
        return jsonify({"error": "No query"}), 400

    try:
        from rag.query import retrieve_chunks
        chunks = retrieve_chunks(query, top_k=top_k)
        return jsonify({"query": query, "chunks": chunks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",  default="0.0.0.0")
    parser.add_argument("--port",  default=5000, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║          AfriBot-2063 Web UI Server                      ║
║  Open in browser: http://localhost:{args.port}               ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
