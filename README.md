# AfriBot-2063 Hybrid AI Teacher System 🤖🇪🇹

> A production-ready offline + online AI education system for Ethiopian students.
> Teaches electrical machines, electronics, robotics and TVET content.
> Supports **Amharic** and **English** — works offline in rural environments.

---

## Architecture Overview

```
User Input (voice/text)
       │
       ▼
Language Detection (Amharic / English)
       │
       ▼
RAG Retrieval ← ChromaDB ← machines_1.pdf (282 pages, Debre Berhan Univ.)
       │
       ▼
AI Router
  ├── Internet available? → Google Gemini API (best Amharic + quality)
  │       └── on failure → Ollama local fallback
  └── No internet?        → Ollama (tinyllama / phi)
       │
       ▼
Response (same language as input)
       │
       ▼
TTS Output (pyttsx3 offline / gTTS online for Amharic)
```

---

## Project Structure

```
afribot_2063/
├── main.py                  # Entry point
├── config.py                # API keys, settings
├── requirements.txt         # Python dependencies
├── data/pdfs/               # PDF knowledge base
│   └── machines_1.pdf       # Electrical Machines textbook (Debre Berhan Univ.)
├── db/chroma/               # Vector DB (auto-generated on first run)
├── models/
│   ├── gemini_llm.py        # Google Gemini API (online)
│   ├── local_llm.py         # Ollama offline AI
│   └── router.py            # AI routing logic
├── rag/
│   ├── ingest.py            # PDF → chunks → embeddings → ChromaDB
│   └── query.py             # Retrieve relevant context
├── speech/
│   ├── stt.py               # Whisper speech-to-text
│   └── tts.py               # pyttsx3 / gTTS text-to-speech
├── language/
│   ├── detect.py            # Amharic / English detection
│   └── translate.py         # Translation helpers
├── utils/
│   ├── internet.py          # Connectivity check
│   └── logger.py            # Logging
├── robot/
│   ├── controller.py        # AfriBot hardware abstraction
│   └── io_handler.py        # Mic / speaker / display
└── tests/
    ├── test_rag.py
    └── test_llm.py
```

---

## Quick Start

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Use pyenv if needed |
| Ollama        | Download from [ollama.ai](https://ollama.ai) |
| 4 GB RAM minimum | tinyllama uses ~800 MB |
| Google Gemini API key | Optional — for online mode |

### 2. Install Python dependencies

```bash
cd afribot_2063
pip install -r requirements.txt
```

> On low-RAM devices, install one-by-one to avoid OOM during pip:
> ```bash
> pip install chromadb sentence-transformers google-generativeai
> pip install ollama pypdf pdfplumber faster-whisper pyttsx3
> pip install langdetect requests colorama tqdm
> ```

### 3. Install and start Ollama

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull tinyllama (~637 MB, works in 4GB RAM)
ollama pull tinyllama

# Or phi (~1.6 GB, better quality)
ollama pull phi

# Start the server (keep running in background)
ollama serve
```

### 4. Set your Gemini API key (optional but recommended)

```bash
# Option A: environment variable (recommended)
export GEMINI_API_KEY="your_key_here"

# Option B: edit config.py
#   GEMINI_API_KEY = "your_key_here"
```

Get a free key at: https://aistudio.google.com/app/apikey

### 5. Ingest the PDF knowledge base

```bash
python main.py --ingest
```

This processes `machines_1.pdf` (282 pages), creates chunks, generates embeddings,
and stores everything in `db/chroma/`. Takes ~2–5 minutes on first run.

### 6. Run AfriBot-2063

```bash
# Text mode (default)
python main.py

# Speech I/O mode (requires microphone)
python main.py --speech

# Force offline mode (no Gemini)
python main.py --offline

# Run diagnostic tests
python main.py --test
```

---

## Usage Examples

### English session

```
You: What is Faraday's Law?

🤖 AfriBot: Faraday's Law states that an electromotive force (EMF) is induced in a
conductor whenever the magnetic flux linking that conductor changes with time.
The induced EMF is given by: E = -dΦB/dt
...
```

### Amharic session

```
You: ፋራዳይ ህግ ምንድን ነው?

🤖 AfriBot: ፋራዳይ ህግ እንደሚከተለው ይገልጻል: አንድ ሞካሪ (conductor) ውስጥ
ኤሌክትሮሞቲቭ ፎርስ (EMF) የሚፈጠረው የማግኔቲክ ፍሰቱ በጊዜ ሲቀየር ነው...
```

---

## PDF Knowledge Base

The system is pre-loaded with:

| File | Content | Pages |
|---|---|---|
| `machines_1.pdf` | Electrical Machines — Debre Berhan University (ECEg-3162) by Dr. Bisrat Gezahegn | 282 |

**Topics covered:**
- Magnetic circuits & properties (MMF, reluctance, permeability)
- Ampere's Law, Faraday's Law, Lorentz Force
- DC machines (motors & generators)
- Transformers
- AC machines

**To add more PDFs:** Copy any `.pdf` to `data/pdfs/` then run:
```bash
python main.py --ingest
```

---

## Configuration Reference (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | env var | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Fast + multilingual |
| `OLLAMA_MODEL` | `tinyllama` | Local offline model |
| `CHUNK_SIZE` | 800 | Characters per RAG chunk |
| `TOP_K_RESULTS` | 4 | RAG chunks retrieved per query |
| `WHISPER_MODEL` | `tiny` | STT model size |

---

## Deploying to AfriBot Robot

The system is hardware-ready. On Raspberry Pi:

```bash
# Install additional hardware deps
pip install RPi.GPIO

# Run with speech enabled
python main.py --speech
```

`robot/controller.py` auto-detects Raspberry Pi and activates GPIO.
Edit `LED_THINKING` and `LED_SPEAKING` pin numbers to match your wiring.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `DB is empty` | Run `python main.py --ingest` |
| `Ollama connection refused` | Run `ollama serve` in a separate terminal |
| `No speech detected` | Install `sounddevice scipy`: `pip install sounddevice scipy` |
| Amharic text not displaying | Use a terminal with UTF-8 support (e.g. VS Code terminal) |
| Out of memory | Use `tinyllama` model and `CHUNK_SIZE=600` in config |

---

## License

Educational use - Debre Berhan University, Ethiopia.
AfriBot-2063 system by: based on the AfriBot-2063 specification.
