"""
ui/app.py — AfriBot-2063 Streamlit Web Dashboard
Run:  streamlit run ui/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AfriBot-2063",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-header {
    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
    padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;
    text-align: center; color: white;
  }
  .main-header h1 { font-size: 2.2rem; margin: 0; letter-spacing: 2px; }
  .main-header p  { color: #aaa; margin: 0.3rem 0 0; }

  .chat-user {
    background: #e8f4fd; border-radius: 12px 12px 2px 12px;
    padding: 0.75rem 1rem; margin: 0.5rem 0; max-width: 80%;
    margin-left: auto; color: #1a1a2e;
  }
  .chat-bot {
    background: #f0f9f0; border-radius: 2px 12px 12px 12px;
    padding: 0.75rem 1rem; margin: 0.5rem 0; max-width: 85%;
    border-left: 3px solid #2ecc71; color: #1a1a2e;
  }
  .chat-bot-am {
    background: #fff8e7; border-radius: 2px 12px 12px 12px;
    padding: 0.75rem 1rem; margin: 0.5rem 0; max-width: 85%;
    border-left: 3px solid #f39c12; color: #1a1a2e;
  }
  .source-badge {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 0.7rem; font-weight: 600; margin-top: 6px;
  }
  .badge-gemini  { background: #4285f4; color: white; }
  .badge-local   { background: #6c757d; color: white; }
  .badge-fallback{ background: #e67e22; color: white; }
  .status-online  { color: #2ecc71; font-weight: 600; }
  .status-offline { color: #e74c3c; font-weight: 600; }

  .metric-card {
    background: #f8f9fa; border-radius: 8px; padding: 1rem;
    text-align: center; border: 1px solid #e9ecef;
  }
  .metric-card h3 { font-size: 1.8rem; margin: 0; color: #2c3e50; }
  .metric-card p  { font-size: 0.8rem; color: #6c757d; margin: 0; }

  .chunk-card {
    background: #f8f9fa; border-left: 3px solid #3498db;
    padding: 0.6rem 0.8rem; border-radius: 4px;
    font-size: 0.82rem; margin-bottom: 0.4rem; color: #333;
  }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0
if "gemini_count" not in st.session_state:
    st.session_state.gemini_count = 0
if "local_count" not in st.session_state:
    st.session_state.local_count = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading AfriBot knowledge base…")
def load_system():
    """Load RAG + embeddings once and cache."""
    from rag.query  import get_collection
    from rag.ingest import get_embed_model, ingest_all
    col = get_collection()
    if col.count() == 0:
        ingest_all()
    get_embed_model()   # warm up
    return True


def check_online():
    from utils.internet import is_online
    return is_online()


def get_db_stats():
    try:
        from rag.query import get_collection
        col = get_collection()
        count = col.count()
        sources = set()
        if count > 0:
            sample = col.get(limit=min(count, 200), include=["metadatas"])
            for m in sample["metadatas"]:
                sources.add(m.get("source", "unknown"))
        return count, list(sources)
    except Exception:
        return 0, []


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ AfriBot Controls")
    st.divider()

    # System status
    online = check_online()
    status_text = "🟢 Online (Gemini)" if online else "🔴 Offline (Ollama)"
    st.markdown(f"**Status:** {status_text}")

    force_offline = st.toggle("Force offline mode", value=False)

    st.divider()
    st.markdown("### 🧠 Knowledge Base")
    chunk_count, sources = get_db_stats()
    st.metric("Chunks in DB", chunk_count)
    if sources:
        for s in sources:
            st.markdown(f"- 📄 `{s}`")

    st.divider()
    st.markdown("### 📥 Add New PDF")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded and st.button("Ingest PDF"):
        save_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "pdfs", uploaded.name
        )
        with open(save_path, "wb") as f:
            f.write(uploaded.read())
        with st.spinner(f"Ingesting {uploaded.name}…"):
            from rag.ingest import ingest_pdf
            n = ingest_pdf(save_path)
        st.success(f"✅ Added {n} chunks from {uploaded.name}")
        st.cache_resource.clear()

    st.divider()
    st.markdown("### 📊 Session Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Queries",  st.session_state.total_queries)
    col2.metric("Gemini",   st.session_state.gemini_count)
    col3.metric("Local",    st.session_state.local_count)

    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### 🔍 RAG Debug")
    show_context = st.toggle("Show retrieved context", value=False)
    top_k = st.slider("Context chunks (top-K)", 1, 8, 4)


# ── Main area ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
  <h1>🤖 AfriBot-2063</h1>
  <p>Hybrid AI Teacher — Electrical Machines · Electronics · Robotics · TVET</p>
  <p style="font-size:0.85rem; margin-top:4px;">English · አማርኛ | Offline + Online</p>
</div>
""", unsafe_allow_html=True)

# Load system
with st.spinner("Initialising AfriBot…"):
    load_system()

# Tabs
tab_chat, tab_search, tab_topics = st.tabs(["💬 Chat", "🔍 Document Search", "📚 Topics"])

# ── TAB 1: Chat ───────────────────────────────────────────────────────────────
with tab_chat:
    # Render message history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center; color:#aaa; padding:3rem 0;">
              <div style="font-size:3rem">🤖</div>
              <p>Ask me anything about electrical machines, electronics, or robotics!</p>
              <p style="font-size:0.85rem">ስለ ኤሌክትሪካል ማሽን ወይም ሮቦቲክስ ጠይቁኝ!</p>
            </div>
            """, unsafe_allow_html=True)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">👤 {msg["content"]}</div>',
                            unsafe_allow_html=True)
            else:
                lang     = msg.get("lang", "en")
                source   = msg.get("source", "local")
                box_cls  = "chat-bot-am" if lang == "am" else "chat-bot"
                badge_cls = f"badge-{source}"
                badge_lbl = {"gemini": "Gemini ☁️", "local": "Ollama 🖥️",
                             "fallback": "Fallback ⚠️"}.get(source, source)
                ts = msg.get("time", "")
                st.markdown(
                    f'<div class="{box_cls}">🤖 {msg["content"]}'
                    f'<br><span class="source-badge {badge_cls}">{badge_lbl}</span>'
                    f'<span style="font-size:0.7rem;color:#aaa;margin-left:8px">{ts}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if show_context and msg.get("context_chunks"):
                    with st.expander("📄 Retrieved context"):
                        for chunk in msg["context_chunks"]:
                            st.markdown(
                                f'<div class="chunk-card">'
                                f'<strong>{chunk["source"]}</strong> '
                                f'(score: {chunk["similarity"]})<br>{chunk["text"][:300]}…'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

    # Input area
    st.markdown("---")
    input_col, btn_col = st.columns([5, 1])
    with input_col:
        question = st.text_input(
            "Ask AfriBot:",
            placeholder="e.g. What is Faraday's Law? / ፋራዳይ ህግ ምንድን ነው?",
            label_visibility="collapsed",
            key="question_input",
        )
    with btn_col:
        send = st.button("Send ➤", use_container_width=True)

    # Quick starters
    st.markdown("**Quick questions:**")
    qcols = st.columns(4)
    starters = [
        "What is Faraday's Law?",
        "Explain magnetic permeability",
        "How does a transformer work?",
        "ፋራዳይ ህግ ምንድን ነው?",
    ]
    for i, (col, q) in enumerate(zip(qcols, starters)):
        if col.button(q, key=f"starter_{i}"):
            question = q
            send = True

    # Process question
    if send and question.strip():
        from language.detect import detect_language
        from models.router   import answer
        from rag.query       import retrieve_chunks

        lang = detect_language(question)

        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})

        with st.spinner("🤔 AfriBot is thinking…"):
            # Retrieve context for display
            chunks = retrieve_chunks(question, top_k=top_k)

            resp_text, source = answer(
                question,
                language=lang,
                force_offline=force_offline,
            )

        # Update stats
        st.session_state.total_queries += 1
        if source == "gemini":
            st.session_state.gemini_count += 1
        else:
            st.session_state.local_count += 1

        st.session_state.messages.append({
            "role": "assistant",
            "content": resp_text,
            "lang": lang,
            "source": source,
            "time": datetime.now().strftime("%H:%M"),
            "context_chunks": chunks,
        })
        st.rerun()


# ── TAB 2: Document Search ────────────────────────────────────────────────────
with tab_search:
    st.markdown("### 🔍 Search the Knowledge Base Directly")
    st.markdown("Retrieve raw chunks from the textbook without AI processing.")

    search_q = st.text_input("Search query:", placeholder="e.g. reluctance permeance magnetic circuit")
    n_results = st.slider("Number of results", 1, 10, 5)

    if st.button("Search 🔍") and search_q.strip():
        from rag.query import retrieve_chunks
        with st.spinner("Searching…"):
            chunks = retrieve_chunks(search_q, top_k=n_results)

        if chunks:
            st.success(f"Found {len(chunks)} relevant passages")
            for i, ch in enumerate(chunks, 1):
                with st.expander(f"#{i} — {ch['source']} (relevance: {ch['similarity']})"):
                    st.markdown(ch["text"])
        else:
            st.warning("No results found. Make sure the PDF has been ingested.")


# ── TAB 3: Topics ─────────────────────────────────────────────────────────────
with tab_topics:
    st.markdown("### 📚 Curriculum Topics")
    st.markdown("Click any topic to ask AfriBot about it.")

    topics = {
        "⚡ Electromagnetic Laws": [
            "Explain Ampere's Law with examples",
            "What is Faraday's Law of electromagnetic induction?",
            "Describe the Lorentz Force Law",
        ],
        "🧲 Magnetic Circuits": [
            "What is magnetomotive force (MMF)?",
            "Explain magnetic permeability and reluctance",
            "What are the properties of magnetic flux?",
        ],
        "🔄 Transformers": [
            "How does a transformer work?",
            "What is the turns ratio of a transformer?",
            "Explain transformer losses and efficiency",
        ],
        "⚙️ DC Machines": [
            "How does a DC motor work?",
            "Explain back EMF in DC motors",
            "What are the types of DC generators?",
        ],
        "🤖 Robotics & TVET": [
            "What sensors are used in robots?",
            "Explain PWM motor control",
            "How is electromagnetic induction used in industry?",
        ],
        "🇪🇹 Amharic Questions": [
            "ፋራዳይ ህግ ምንድን ነው?",
            "ትራንስፎርመር እንዴት ይሠራል?",
            "ማግኔቲክ ፍሰት ምንድን ነው?",
        ],
    }

    for section, questions in topics.items():
        st.markdown(f"#### {section}")
        cols = st.columns(len(questions))
        for col, q in zip(cols, questions):
            if col.button(q, key=f"topic_{q[:20]}"):
                st.session_state.messages.append({"role": "user", "content": q})
                from language.detect import detect_language
                from models.router   import answer
                lang = detect_language(q)
                with st.spinner("Thinking…"):
                    resp, src = answer(q, language=lang, force_offline=force_offline)
                st.session_state.messages.append({
                    "role": "assistant", "content": resp,
                    "lang": lang, "source": src,
                    "time": datetime.now().strftime("%H:%M"),
                    "context_chunks": [],
                })
                st.session_state.total_queries += 1
                st.switch_page("ui/app.py") if hasattr(st, "switch_page") else st.rerun()
        st.markdown("---")
