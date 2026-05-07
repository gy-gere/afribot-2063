#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# AfriBot-2063 Launcher
# Usage:
#   ./launch.sh web        → Flask web UI (http://localhost:5000)
#   ./launch.sh streamlit  → Streamlit UI (http://localhost:8501)
#   ./launch.sh telegram   → Telegram bot
#   ./launch.sh cli        → Terminal CLI
#   ./launch.sh ingest     → Ingest PDFs
#   ./launch.sh all        → Web UI + Telegram bot (tmux)
# ══════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

MODE="${1:-web}"

check_ollama() {
  if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠  Ollama not running. Starting..."
    ollama serve &
    sleep 2
  else
    echo "✅ Ollama running"
  fi
}

case "$MODE" in
  web)
    echo "🖥  Starting AfriBot-2063 Web UI..."
    check_ollama
    echo "📡 Open http://localhost:5000 in your browser"
    python ui/server.py --host 0.0.0.0 --port 5000
    ;;

  streamlit)
    echo "📊 Starting AfriBot-2063 Streamlit Dashboard..."
    check_ollama
    streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
    ;;

  telegram)
    echo "🤖 Starting AfriBot-2063 Telegram Bot..."
    check_ollama
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
      echo "❌ Set TELEGRAM_BOT_TOKEN first:"
      echo "   export TELEGRAM_BOT_TOKEN='your_token'"
      exit 1
    fi
    python bot/telegram_bot.py
    ;;

  cli)
    echo "💬 Starting AfriBot-2063 CLI..."
    check_ollama
    python main.py
    ;;

  ingest)
    echo "📥 Ingesting PDF knowledge base..."
    python main.py --ingest
    ;;

  all)
    # Run web UI + Telegram in parallel using tmux (if available)
    if command -v tmux &> /dev/null; then
      tmux new-session -d -s afribot -x 220 -y 50
      tmux send-keys -t afribot "python ui/server.py" Enter
      tmux split-window -h -t afribot
      tmux send-keys -t afribot "python bot/telegram_bot.py" Enter
      tmux attach-session -t afribot
    else
      echo "tmux not found — running web UI only"
      python ui/server.py --host 0.0.0.0 --port 5000 &
      python bot/telegram_bot.py
    fi
    ;;

  *)
    echo "Usage: ./launch.sh [web|streamlit|telegram|cli|ingest|all]"
    exit 1
    ;;
esac
