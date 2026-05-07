"""
AfriBot-2063 — Central Configuration
Edit this file to set your API keys and preferences.
"""

import os

# ─────────────────────────────────────────────
# GOOGLE GEMINI API
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL   = "gemini-1.5-flash"          # fast + multilingual

# ─────────────────────────────────────────────
# LOCAL OLLAMA MODEL
# ─────────────────────────────────────────────
OLLAMA_MODEL    = "tinyllama"                 # or "phi", "mistral"
OLLAMA_BASE_URL = "http://localhost:11434"

# ─────────────────────────────────────────────
# RAG / CHROMADB
# ─────────────────────────────────────────────
CHROMA_DB_PATH   = os.path.join(os.path.dirname(__file__), "db", "chroma")
PDF_DIR          = os.path.join(os.path.dirname(__file__), "data", "pdfs")
COLLECTION_NAME  = "afribot_knowledge"
CHUNK_SIZE       = 800    # characters per chunk
CHUNK_OVERLAP    = 150    # overlap between chunks
TOP_K_RESULTS    = 4      # how many chunks to retrieve

# ─────────────────────────────────────────────
# WHISPER SPEECH-TO-TEXT
# ─────────────────────────────────────────────
WHISPER_MODEL    = "tiny"           # tiny|base|small — tiny fits 4GB RAM
WHISPER_DEVICE   = "cpu"            # cpu or cuda

# ─────────────────────────────────────────────
# TEXT-TO-SPEECH
# ─────────────────────────────────────────────
TTS_RATE   = 150    # words per minute
TTS_VOLUME = 0.9    # 0.0 – 1.0

# ─────────────────────────────────────────────
# LANGUAGE
# ─────────────────────────────────────────────
DEFAULT_LANGUAGE = "en"   # "en" or "am"

# ─────────────────────────────────────────────
# SYSTEM BEHAVIOUR
# ─────────────────────────────────────────────
INTERNET_CHECK_URL     = "https://www.google.com"
INTERNET_CHECK_TIMEOUT = 3    # seconds
LOG_LEVEL              = "INFO"
LOG_FILE               = os.path.join(os.path.dirname(__file__), "afribot.log")
